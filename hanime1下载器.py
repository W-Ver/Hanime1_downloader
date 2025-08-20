#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频批量下载器（交互菜单 · 多线程 · 统一标题= #shareBtn-title · 高颜值 CLI）
================================================================================
要点更新：
  • 所有文件名一律取自 <h3 id="shareBtn-title">…</h3> 的文本（优先 HTTP 直抓）
  • 播放列表/同系列：先抓全量链接，再逐个按“原名(shareBtn-title)”下载
  • 进度条修复（不再因 None total 报错）
  • 文件存在时 10 秒内未答复默认跳过；答 O 覆盖后立即下载下一个

依赖：requests, selenium, rich(推荐), Chrome+chromedriver, ffmpeg(抓 m3u8)
安装：pip install -U requests selenium rich
仅限合规用途。
"""

from __future__ import annotations
import argparse
import concurrent.futures as cf
import contextlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ====================== 可选高颜值 UI：rich =======================
RICH = False
with contextlib.suppress(Exception):
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich.prompt import Prompt, Confirm
    from rich.progress import (
        Progress, BarColumn, TextColumn,
        TimeRemainingColumn, TransferSpeedColumn, SpinnerColumn
    )
    from rich.theme import Theme
    RICH = True

if RICH:
    theme = Theme({
        "info": "bold cyan",
        "good": "bold green",
        "warn": "bold yellow",
        "bad": "bold red",
        "hl": "bright_magenta",
    })
    console = Console(theme=theme)
else:
    class _Dummy:
        def print(self, *a, **k):
            print(*a, **k)
    console = _Dummy()

RESET = "\033[0m"; BOLD = "\033[1m"; GREEN = "\033[32m"; YELLOW = "\033[33m"; RED = "\033[31m"; CYAN = "\033[36m"

def c_info(msg: str) -> None:
    if RICH: console.print(f"[info][i][/info] {msg}")
    else: print(f"{CYAN}[i]{RESET} {msg}")

def c_ok(msg: str) -> None:
    if RICH: console.print(f"[good][✓][/good] {msg}")
    else: print(f"{GREEN}[✓]{RESET} {msg}")

def c_warn(msg: str) -> None:
    if RICH: console.print(f"[warn][!][/warn] {msg}")
    else: print(f"{YELLOW}[!]{RESET} {msg}")

def c_err(msg: str) -> None:
    if RICH: console.print(f"[bad][x][/bad] {msg}")
    else: print(f"{RED}[x]{RESET} {msg}")

# ====================== 依赖 =======================
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

# ====================== 常量 & 设置 =======================
WATCH_RE = re.compile(r'^https?://(?:www\.)?hanime1\.me/watch\?v=\d+$')
DEFAULT_DIR = Path.home() / 'Downloads' / 'Videos'

@dataclass
class Settings:
    retry: int = 3
    threads: int = 3
    delay: int = 2
    stagger: float = 0.8
    priority: str = 'highest'   # highest/balanced/fastest
    directory: Path = DEFAULT_DIR

    # 标题策略：强制 share_h3（本版固定为 share_h3；仅保留 as_shown 作为展示用途）
    title_mode: str = 'share_h3'  # share_h3 / as_shown

    headless: bool = True
    parse_with_images: bool = True

CFG = Settings()

# ====================== 数据结构 =======================
@dataclass
class VideoItem:
    id: str
    url: str
    title: str
    original_title: str
    is_current: bool
    is_same_series: bool
    best_quality: Optional[str] = None
    best_link: Optional[str] = None
    estimated_size: Optional[float] = None  # MB

@dataclass
class AnalyzeResult:
    url: str
    title: str
    series_name: str
    playlist: List[VideoItem]
    timestamp: str

# ====================== 工具函数 =======================

def sanitize_filename(filename: str) -> str:
    if not filename:
        return 'untitled'
    for ch in '<>:"/\\|?*':
        filename = filename.replace(ch, '_')
    filename = ''.join(c for c in filename if ord(c) >= 32)
    return filename.strip()


def format_time(seconds: float) -> str:
    if seconds < 0 or seconds > 24*3600:
        return '--:--'
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

# ====================== 交互输入（带超时） =======================
PROMPT_LOCK = threading.Lock()


def _timed_input(prompt: str, timeout: float, default: str) -> str:
    buf = {"val": None}
    def _reader():
        try:
            buf["val"] = input(prompt)
        except EOFError:
            pass
    t = threading.Thread(target=_reader, daemon=True)
    t.start(); t.join(timeout)
    val = buf["val"]
    return default if val is None or str(val).strip() == '' else str(val).strip()


def ask_overwrite_skip(path: Path, timeout: int = 10) -> bool:
    with PROMPT_LOCK:
        fname = path.name
        if RICH:
            console.print(Panel.fit(
                f"[warn]文件已存在[/warn]：[hl]{fname}[/hl]\n选择 [S]跳过 / [O]覆盖（删除后重下）\n[dim]{timeout}s 内不操作将默认 [S] 跳过[/dim]",
                title="冲突处理", border_style="warn"
            ))
            ans = _timed_input(
                "> 请输入 S 或 O: ", timeout=timeout, default="S"
            )
        else:
            print(f"文件已存在：{fname}\n选择 S=跳过 / O=覆盖（删除后重下）\n{timeout}s 内不操作将默认跳过")
            ans = _timed_input("请输入 S 或 O: ", timeout=timeout, default="S")
    return ans.lower().startswith('o')

# ====================== Selenium 驱动 =======================

def get_chrome_driver(headless: bool = True, images_enabled: bool = True) -> webdriver.Chrome:
    chrome_options = Options()
    if headless:
        chrome_options.add_argument('--headless=new')
    for a in [
        '--no-sandbox', '--disable-dev-shm-usage', '--disable-blink-features=AutomationControlled',
        '--mute-audio', '--autoplay-policy=no-user-gesture-required', '--disable-gpu',
        '--window-size=1920,1080', '--ignore-certificate-errors', '--allow-running-insecure-content',
    ]:
        chrome_options.add_argument(a)
    chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    prefs = {
        'profile.default_content_setting_values.media_stream_mic': 2,
        'profile.default_content_setting_values.media_stream_camera': 2,
        'profile.default_content_setting_values.geolocation': 2,
        'profile.default_content_setting_values.notifications': 2,
        'profile.managed_default_content_settings.images': 1 if images_enabled else 2,
    }
    chrome_options.add_experimental_option('prefs', prefs)
    chrome_options.set_capability('acceptInsecureCerts', True)
    return webdriver.Chrome(options=chrome_options)

# ====================== 标题统一：强制从 #shareBtn-title =======================

# 直接 HTTP 抓页面源码：优先 #shareBtn-title，其次 og:title，再次 <title>
_RE_H3 = re.compile(r'id=["\']shareBtn-title["\'][^>]*>([^<]+)<', re.I)
_RE_OG = re.compile(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']', re.I)
_RE_TIT = re.compile(r'<title>([^<]+)</title>', re.I)
_HTTP_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://hanime1.me/',
    # 偏向日文，避免中文自动翻译
    'Accept-Language': 'ja,ja-JP;q=0.9,en-US;q=0.7,en;q=0.5',
}

def title_from_share_h3_http(url: str, timeout: int = 15) -> Optional[str]:
    try:
        with requests.Session() as s:
            r = s.get(url, headers=_HTTP_HEADERS, timeout=timeout)
            r.raise_for_status()
            html = r.text
        m = _RE_H3.search(html)
        if m:
            return m.group(1).strip()
        m = _RE_OG.search(html)
        if m:
            return m.group(1).strip()
        m = _RE_TIT.search(html)
        if m:
            return m.group(1).split(' - ')[0].strip()
    except Exception:
        return None
    return None

# 兜底：用 Selenium 读 #shareBtn-title

def title_from_share_h3_selenium(url: str, headless: bool = True) -> Optional[str]:
    d = get_chrome_driver(headless=headless, images_enabled=False)
    try:
        d.get(url)
        WebDriverWait(d, 15).until(lambda x: x.title != '')
        with contextlib.suppress(Exception):
            return d.find_element(By.ID, 'shareBtn-title').text.strip() or None
        with contextlib.suppress(Exception):
            return d.title.split(' - ')[0].strip() or None
        return None
    finally:
        with contextlib.suppress(Exception):
            d.quit()

# 统一入口：强制拿到 share_h3；HTTP > Selenium > None

def force_share_title(url: str) -> Optional[str]:
    t = title_from_share_h3_http(url)
    if t:
        return t
    return title_from_share_h3_selenium(url, headless=CFG.headless)

# ====================== 解析 watch 页面 =======================

def extract_series_name(title: str) -> str:
    if not title:
        return ''
    t = re.sub(r'\[.*?\]', '', title)
    t = re.sub(r'\s*\d+\s*$', '', t)
    t = re.sub(r'\s*[一二三四五六七八九十]+\s*$', '', t)
    return t.strip()


def select_best_quality(video_links: List[str], priority: str = 'highest') -> Tuple[Optional[str], Optional[str]]:
    if not video_links:
        return None, None
    order = {
        'highest': ['1080p','720p','480p','360p','240p'],
        'balanced': ['720p','1080p','480p','360p','240p'],
        'fastest': ['480p','360p','720p','240p','1080p'],
    }.get(priority, ['1080p','720p','480p','360p','240p'])
    for q in order:
        for link in video_links:
            if q.lower() in link.lower() or re.search(rf'[=/_-]{q[:-1]}p(?!\d)', link, re.I):
                return link, q
    return video_links[0], 'unknown'


def _locate_playlist_container(driver: webdriver.Chrome):
    for sel in [(By.ID, 'playlist-scroll'), (By.CSS_SELECTOR, 'div.hover-video-playlist')]:
        with contextlib.suppress(Exception):
            return driver.find_element(*sel)
    return None


def preload_playlist(driver, container, step=800, max_rounds=40, sleep=0.25):
    sel = "div > a[href*='watch?v=']"
    last_count = -1; rounds_no_growth = 0
    for _ in range(max_rounds):
        links = container.find_elements(By.CSS_SELECTOR, sel)
        count = len(links)
        if count == last_count: rounds_no_growth += 1
        else: rounds_no_growth = 0
        last_count = count
        end_reached = driver.execute_script(
            "return Math.abs(arguments[0].scrollTop + arguments[0].clientHeight - arguments[0].scrollHeight) < 5;",
            container
        )
        if end_reached and rounds_no_growth >= 2:
            break
        driver.execute_script("arguments[0].scrollBy(0, arguments[1]);", container, step)
        time.sleep(sleep)


def smart_title_from_card(driver, card_or_link):
    js = r"""
    const el = arguments[0];
    function txt(n){ return (n && (n.innerText || n.textContent) || '').trim(); }
    let t = '';
    let cand = el.querySelector('.card-mobile-title, .card-title, [class*="title"], [class*="name"]');
    if (cand) t = txt(cand);
    if (!t) {
      const img = el.querySelector('img[alt]');
      if (img && img.alt) t = img.alt.trim();
    }
    if (!t) {
      t = (el.getAttribute('title') || el.getAttribute('aria-label') || (el.dataset && (el.dataset.title || el.dataset.name)) || '').trim();
    }
    if (!t) t = txt(el);
    if (!t && el.parentElement) {
      const p = el.parentElement;
      cand = p.querySelector('.card-mobile-title, .card-title, [class*="title"], [class*="name"]');
      if (cand) t = txt(cand);
      if (!t) {
        t = (p.getAttribute('title') || p.getAttribute('aria-label') || (p.dataset && (p.dataset.title || p.dataset.name)) || '').trim();
      }
      if (!t) t = txt(p);
    }
    return t;
    """
    try:
        return (driver.execute_script(js, card_or_link) or "").strip()
    except Exception:
        return ""


def analyze_watch(url: str, priority: str = 'highest', headless: bool = True, images_enabled: bool = True, timeout: int = 20) -> AnalyzeResult:
    if not WATCH_RE.match(url):
        raise ValueError('URL 不合法，应为 https://hanime1.me/watch?v=xxxxx')

    driver = get_chrome_driver(headless=headless, images_enabled=images_enabled)
    title = ''
    series_name = ''
    playlist: List[VideoItem] = []

    try:
        c_info(f'访问: {url}')
        driver.get(url)
        WebDriverWait(driver, timeout).until(lambda d: d.title != '')
        time.sleep(1.2)

        # 当前页标题：从 shareBtn-title 抓取，确保与 HTTP 规则一致
        with contextlib.suppress(Exception):
            title = driver.find_element(By.ID, 'shareBtn-title').text.strip()
        if not title:
            with contextlib.suppress(Exception):
                title = driver.title.split(' - ')[0].strip()
        series_name = extract_series_name(title)
        if series_name:
            c_info(f'系列名：{series_name}')

        # 尝试触发播放，提高页面注入直链概率
        with contextlib.suppress(Exception):
            driver.find_element(By.CSS_SELECTOR, 'div.plyr > button').click(); time.sleep(1.2)

        # 当前页直链
        video_urls = []
        with contextlib.suppress(Exception):
            for v in driver.find_elements(By.TAG_NAME, 'video'):
                src = v.get_attribute('src')
                if src: video_urls.append(src)
        with contextlib.suppress(Exception):
            html = driver.page_source
            video_urls += re.findall(r'https?://[^\s"\']+\.m3u8[^\s"\']*', html)
            video_urls += re.findall(r'https?://[^\s"\']+\.mp4[^\s"\']*', html)
        video_urls = list(dict.fromkeys(video_urls))
        best_link, best_quality = select_best_quality(video_urls, priority)

        # 播放列表容器
        playlist_container = _locate_playlist_container(driver)
        link_elems = []
        if playlist_container:
            preload_playlist(driver, playlist_container)
            with contextlib.suppress(Exception):
                link_elems = playlist_container.find_elements(By.CSS_SELECTOR, "div > a[href*='watch?v=']")
        c_info(f'播放列表条目: {len(link_elems)}')

        if link_elems:
            for idx, link in enumerate(link_elems):
                try:
                    href = link.get_attribute('href')
                    if not href or not WATCH_RE.match(href):
                        continue
                    try:
                        card = link.find_element(By.XPATH, '..')
                    except Exception:
                        card = link
                    shown = smart_title_from_card(driver, card) or smart_title_from_card(driver, link) or f"视频 {idx+1}"
                    is_current = (href == url) or ('現正播放' in (card.text or ''))
                    clean = re.sub(r'\[.*?\]', '', shown).strip()
                    same = False
                    if series_name and (series_name in clean or re.sub(r'\s*\d+\s*$', '', clean).strip() == series_name):
                        same = True
                    item = VideoItem(
                        id=hashlib.md5(href.encode()).hexdigest()[:8],
                        url=href,
                        title=shown,
                        original_title=shown,  # 稍后统一用 share_h3 覆盖
                        is_current=is_current,
                        is_same_series=same,
                        estimated_size=round(300 + (idx * 50), 2)
                    )
                    if is_current:
                        item.original_title = title or shown
                        item.best_link = best_link
                        item.best_quality = best_quality
                        item.estimated_size = 800 if best_quality == '1080p' else (500 if best_quality == '720p' else 300)
                    playlist.append(item)
                except Exception as e:
                    c_warn(f'条目失败: {e}')
        else:
            # 没列表也保证有一条
            item = VideoItem(
                id=hashlib.md5(url.encode()).hexdigest()[:8],
                url=url,
                title=title or '当前视频',
                original_title=title or '当前视频',
                is_current=True,
                is_same_series=bool(series_name),
                best_quality=best_quality,
                best_link=best_link,
                estimated_size=800 if best_quality == '1080p' else (500 if best_quality == '720p' else 300)
            )
            playlist.append(item)

        # ★ 统一：对“所有”条目强制用 share_h3 原名覆盖（并发提高速度）
        def _fix(it: VideoItem) -> None:
            nm = force_share_title(it.url)
            if nm:
                it.original_title = nm
        with cf.ThreadPoolExecutor(max_workers=min(8, len(playlist) or 1)) as ex:
            list(ex.map(_fix, playlist))

        # 排序：同系列优先、当前置顶
        playlist.sort(key=lambda x: (not x.is_same_series, not x.is_current))
        return AnalyzeResult(url=url, title=title, series_name=series_name, playlist=playlist, timestamp=datetime.now().isoformat())
    finally:
        with contextlib.suppress(Exception):
            driver.quit()

# ====================== 直链获取（下载前兜底） =======================

def fetch_video_details(url: str, priority: str = 'highest', headless: bool = True, images_enabled: bool = False) -> Dict[str, Optional[str]]:
    d = get_chrome_driver(headless=headless, images_enabled=images_enabled)
    try:
        d.get(url)
        time.sleep(1.0)
        with contextlib.suppress(Exception):
            d.find_element(By.CSS_SELECTOR, 'div.plyr > button').click(); time.sleep(1.0)
        title = ''
        with contextlib.suppress(Exception):
            title = d.find_element(By.ID, 'shareBtn-title').text.strip()
        if not title:
            with contextlib.suppress(Exception):
                title = d.title.split(' - ')[0].strip()
        links = []
        with contextlib.suppress(Exception):
            for v in d.find_elements(By.TAG_NAME, 'video'):
                src = v.get_attribute('src')
                if src: links.append(src)
        with contextlib.suppress(Exception):
            html = d.page_source
            links += re.findall(r'https?://[^\s"\']+\.m3u8[^\s"\']*', html)
            links += re.findall(r'https?://[^\s"\']+\.mp4[^\s"\']*', html)
        links = list(dict.fromkeys(links))
        best_link, best_quality = select_best_quality(links, priority)
        return {'original_title': title, 'best_link': best_link, 'best_quality': best_quality, 'all_links': links}
    finally:
        with contextlib.suppress(Exception):
            d.quit()

# ====================== 下载实现（requests / ffmpeg） =======================

def ensure_ffmpeg() -> bool:
    return shutil.which('ffmpeg') is not None


def download_with_ffmpeg(url: str, output_path: Path) -> bool:
    cmd = ['ffmpeg', '-y', '-i', url, '-c', 'copy', '-bsf:a', 'aac_adtstoasc', '-loglevel', 'error', '-stats', str(output_path)]
    try:
        subprocess.run(cmd, check=True)
        return output_path.exists()
    except FileNotFoundError:
        c_err('未检测到 ffmpeg，请先安装')
        return False
    except subprocess.CalledProcessError as e:
        c_err(f'ffmpeg 返回非零：{e}')
        return False
    except Exception as e:
        c_err(f'ffmpeg 异常：{e}')
        return False


def download_with_requests(url: str, output_path: Path, progress: Optional[Progress]=None, task_id: Optional[int]=None) -> bool:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://hanime1.me/',
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
    }
    try:
        with requests.Session() as s:
            with s.get(url, headers=headers, stream=True, timeout=30) as r:
                r.raise_for_status()
                total = int(r.headers.get('content-length', 0))
                downloaded = 0
                chunk = 1024 * 64
                if progress is not None and task_id is not None and total:
                    progress.update(task_id, total=total)
                with open(output_path, 'wb') as f:
                    for part in r.iter_content(chunk_size=chunk):
                        if not part:
                            continue
                        f.write(part)
                        downloaded += len(part)
                        if progress is not None and task_id is not None and total:
                            progress.update(task_id, completed=downloaded)
        return output_path.exists()
    except requests.exceptions.Timeout:
        c_err('下载超时')
        return False
    except Exception as e:
        c_err(f'requests 下载失败：{e}')
        return False

# ====================== 线程 worker & 并行驱动 =======================

def worker_download(item: VideoItem, outdir: Path, priority: str, retry: int, headless: bool, images_enabled: bool,
                    ui: Optional["Progress"]=None, global_task: Optional[int]=None, files_ui: Optional["Progress"]=None):
    title = item.original_title or item.title
    name = sanitize_filename(title)
    out = outdir / f'{name}.mp4'

    # 同名文件处理（10 秒默认跳过）
    if out.exists():
        overwrite = ask_overwrite_skip(out, timeout=10)
        if not overwrite:
            c_info(f"跳过已存在：{out.name}")
            if RICH and ui is not None and global_task is not None:
                ui.advance(global_task)
            return
        else:
            with contextlib.suppress(Exception):
                out.unlink()
            c_warn(f"已删除旧文件，准备重新下载：{out.name}")

    link = item.best_link
    q = item.best_quality or 'unknown'
    if not link:
        det = fetch_video_details(item.url, priority=priority, headless=headless, images_enabled=images_enabled)
        link = det.get('best_link')
        q = det.get('best_quality') or q
    if not link:
        raise RuntimeError('无法获取直链')

    task_id = None
    if RICH and files_ui is not None:
        # 关键修复：用 total=1 作为占位，后续在 download_with_requests 里替换为真实 total
        task_id = files_ui.add_task("FILE", total=1, start=False, name=name, q=q)
        files_ui.start_task(task_id)

    success = False
    for i in range(retry):
        if i: time.sleep(2)
        if '.m3u8' in link:
            success = download_with_ffmpeg(link, out)
        else:
            success = download_with_requests(link, out, progress=files_ui, task_id=task_id)
        if success:
            break

    if not success:
        raise RuntimeError(f'重试 {retry} 次仍失败')

    if RICH and files_ui is not None and task_id is not None:
        task = files_ui.get_task(task_id)
        # 若没拿到 content-length，就把 completed=total（1）以结束
        files_ui.update(task_id, completed=task.total)
        files_ui.stop_task(task_id)
    if RICH and ui is not None and global_task is not None:
        ui.advance(global_task)


def run_parallel_download(items: List[VideoItem]):
    total = len(items)
    if total == 0:
        c_warn('没有可下载的条目')
        return
    CFG.directory.mkdir(parents=True, exist_ok=True)
    c_info(f'开始下载：{total} 个文件 → {CFG.directory} | 线程={CFG.threads} | 重试={CFG.retry} | 延迟={CFG.delay}s | 错峰={CFG.stagger}s')

    stop_event = threading.Event()
    def _sigint_handler(signum, frame):
        stop_event.set()
    with contextlib.suppress(Exception):
        signal.signal(signal.SIGINT, _sigint_handler)

    if RICH:
        global_cols = [
            TextColumn("[good]全局[/good]", justify="left"),
            BarColumn(bar_width=40),
            TextColumn("{task.completed}/{task.total}", justify="right"),
            TimeRemainingColumn(),
        ]
        file_cols = [
            SpinnerColumn(),
            TextColumn("[hl]{task.fields[name]}[/hl] • {task.fields[q]}", justify="left"),
            BarColumn(bar_width=28),
            # 只显示 completed/total（total 初始为 1，后续会被替换），不会再触发 None 格式化
            TextColumn("{task.completed}/{task.total}", justify="right"),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
        ]
        progress = Progress(*global_cols, transient=False, expand=True, console=console)
        files_progress = Progress(*file_cols, transient=False, expand=True, console=console)
        with progress, files_progress:
            global_task = progress.add_task("ALL", total=total)
            with cf.ThreadPoolExecutor(max_workers=CFG.threads) as ex:
                futures = []
                for it in items:
                    if stop_event.is_set():
                        break
                    f = ex.submit(
                        worker_download,
                        it, CFG.directory, CFG.priority, CFG.retry,
                        CFG.headless, False,  # 下载阶段图片可关闭
                        progress, global_task, files_progress
                    )
                    futures.append(f)
                    time.sleep(CFG.stagger)
                for f in cf.as_completed(futures):
                    with contextlib.suppress(Exception):
                        f.result()
    else:
        done = 0; lock = threading.Lock()
        def _wrap(it: VideoItem):
            nonlocal done
            try:
                worker_download(it, CFG.directory, CFG.priority, CFG.retry, CFG.headless, False)
                c_ok(f"完成：{it.original_title or it.title}")
            except Exception as e:
                c_err(f"失败：{it.original_title or it.title} | {e}")
            finally:
                with lock:
                    done += 1
                    print(f"进度 {done}/{total}")
                time.sleep(CFG.delay)
        with cf.ThreadPoolExecutor(max_workers=CFG.threads) as ex:
            futs = []
            for it in items:
                futs.append(ex.submit(_wrap, it))
                time.sleep(CFG.stagger)
            for f in cf.as_completed(futs):
                pass
    c_ok('全部任务完成')

# ====================== 交互式菜单 =======================

def banner():
    if RICH:
        console.print(Panel.fit(
            Text("视频下载器 CLI Pro\n单/多线程 · 防风控 · 智能重试", justify="center", style="hl"),
            title="✨ HANIME1 助手", subtitle=f"默认下载目录: {CFG.directory}", border_style="hl"
        ))
    else:
        print("="*70)
        print(f"{BOLD}视频下载器 CLI Pro{RESET}  |  单/多线程 · 防风控 · 智能重试")
        print("-"*70)
        print(f"默认下载目录: {CFG.directory}")
        print("="*70)


def menu_table() -> None:
    if RICH:
        t = Table(title="请选择操作（输入编号，或一行速用：<编号> <URL/文件>）", title_style="info")
        t.add_column("编号", justify="center", style="hl", no_wrap=True)
        t.add_column("操作")
        t.add_column("说明", style="dim")
        t.add_row("1", "解析页面（仅查看）", "不下载，只列标题/系列/画质；可保存 plan.json 供后续批量")
        t.add_row("2", "下载当前视频", "仅下载当前 watch 页对应视频")
        t.add_row("3", "下载同系列", "自动识别与当前同系列条目并全部下载")
        t.add_row("4", "下载播放列表全部", "先抓全量链接，再逐个按 \"原名\" 下载")
        t.add_row("5", "使用计划文件下载", "从 plan.json 读取清单（可在 1 中生成/编辑）")
        t.add_row("6", "设置选项", "目录/重试/延迟/错峰/线程数/画质/headless/解析图片/标题策略")
        t.add_row("7", "退出", "再见")
        console.print(t)
        console.print("[dim]小技巧：\n  • 直接一行：`2 https://hanime1.me/watch?v=123456`\n  • 也可：`5 D:/plan.json`\n  • 风控重：把线程调低(1-2)并加大错峰/延迟。[/dim]")
    else:
        print("\n请选择操作：")
        print("  1) 解析页面（仅查看）  —— 列标题/系列/画质，可保存 plan.json")
        print("  2) 下载当前视频        —— 仅下载当前 watch 页")
        print("  3) 下载同系列          —— 自动识别同系列并全部下载")
        print("  4) 下载播放列表全部    —— 先抓全量链接，再逐个按原名下载")
        print("  5) 使用计划文件下载    —— 从 plan.json 读取清单")
        print("  6) 设置选项            —— 目录/重试/延迟/错峰/线程/画质/headless/解析图片/标题策略")
        print("  7) 退出")


def parse_choice_line(line: str) -> Tuple[Optional[int], Optional[str]]:
    line = (line or '').strip()
    if not line:
        return None, None
    parts = line.split(maxsplit=1)
    try:
        opt = int(parts[0])
    except ValueError:
        return None, None
    arg = parts[1].strip() if len(parts) > 1 else None
    return opt, arg


def ask(prompt: str, default: Optional[str] = None) -> str:
    if RICH:
        return Prompt.ask(prompt, default=default)
    sfx = f" [{default}]" if default is not None else ''
    val = input(f"{prompt}{sfx}: ").strip()
    return default if (val == '' and default is not None) else val


def choose_url(arg_from_inline: Optional[str] = None) -> str:
    url = arg_from_inline or ask('贴上视频 URL (https://hanime1.me/watch?v=数字)')
    if not WATCH_RE.match(url):
        raise ValueError('URL 不合法：需要形如 https://hanime1.me/watch?v=123456')
    return url


def choose_plan_path(arg_from_inline: Optional[str] = None) -> Path:
    p = arg_from_inline or ask('输入计划文件路径 (plan.json)')
    path = Path(p).expanduser()
    if not path.exists():
        raise FileNotFoundError(f'找不到文件：{path}')
    return path


def configure_settings():
    if RICH:
        console.print(Panel.fit("当前设置", style="hl"))
        table = Table(show_header=False)
        table.add_row("下载目录", f"{CFG.directory}")
        table.add_row("失败重试", f"{CFG.retry}")
        table.add_row("同线程延迟(秒)", f"{CFG.delay}")
        table.add_row("任务错峰(秒)", f"{CFG.stagger}")
        table.add_row("并发线程", f"{CFG.threads}")
        table.add_row("画质优先级", f"{CFG.priority}")
        table.add_row("标题策略", f"{CFG.title_mode}  (share_h3=统一原名, as_shown=页面显示)")
        table.add_row("无头浏览器(headless)", "是" if CFG.headless else "否")
        table.add_row("解析时加载图片", "是" if CFG.parse_with_images else "否")
        console.print(table)
    else:
        c_info(f"下载目录: {CFG.directory}\n重试: {CFG.retry}  延迟: {CFG.delay}s  错峰: {CFG.stagger}s  线程: {CFG.threads}\n画质: {CFG.priority}  标题策略: {CFG.title_mode}  headless: {'是' if CFG.headless else '否'}  解析加载图片: {'是' if CFG.parse_with_images else '否'}")

    d = ask('下载目录', str(CFG.directory))
    with contextlib.suppress(Exception):
        CFG.directory = Path(d).expanduser(); CFG.directory.mkdir(parents=True, exist_ok=True)

    try:
        CFG.retry = int(ask('失败重试次数', str(CFG.retry)))
        CFG.delay = int(ask('同一线程文件间延迟(秒)', str(CFG.delay)))
        CFG.stagger = float(ask('任务提交错峰(秒)', str(CFG.stagger)))
        CFG.threads = max(1, int(ask('并发线程数(建议 1~5)', str(CFG.threads))))
    except ValueError:
        c_warn('数字输入无效，保持原值。')

    pr = ask('画质优先级 (highest/balanced/fastest)', CFG.priority)
    if pr in ('highest','balanced','fastest'):
        CFG.priority = pr
    else:
        c_warn('画质优先级无效，保持原值。')

    tm = ask('标题策略 (share_h3/as_shown)', CFG.title_mode)
    if tm in ('share_h3','as_shown'):
        CFG.title_mode = tm
    else:
        c_warn('标题策略无效，保持原值。')

    hd = ask('启用无头浏览器(headless)? (Y/n)', 'Y').lower()
    CFG.headless = hd not in ('n','no','0')

    img = ask('解析阶段加载图片? (Y/n)', 'Y').lower()
    CFG.parse_with_images = img not in ('n','no','0')


def interactive_main():
    banner()
    while True:
        try:
            menu_table()
            line = ask('输入编号（或一行速用：<编号> <URL/文件>）')
            opt, arg = parse_choice_line(line)
            if not opt:
                c_warn('请输入 1-7 的数字。'); continue
            if opt == 7:
                console.print('[dim]Bye![/dim]'); return
            elif opt == 6:
                configure_settings(); continue
            elif opt == 1:
                url = choose_url(arg)
                res = analyze_watch(url, priority=CFG.priority, headless=CFG.headless, images_enabled=CFG.parse_with_images)
                if RICH:
                    table = Table(title="解析结果", title_style="info")
                    table.add_column('#', justify='right')
                    table.add_column('当前', justify='center')
                    table.add_column('系列', justify='center')
                    table.add_column('画质', justify='center')
                    table.add_column('标题(统一原名)')
                    for i, v in enumerate(res.playlist, 1):
                        table.add_row(str(i), '✓' if v.is_current else '', '✓' if v.is_same_series else '', v.best_quality or '', v.original_title or v.title)
                    console.print(table)
                else:
                    print(f"\n{BOLD}标题{RESET}: {res.title or '-'}\n{BOLD}系列{RESET}: {res.series_name or '-'}\n{BOLD}条目{RESET}: {len(res.playlist)}\n")
                    header = f"{'#':>3}  {'当前':^4}  {'系列':^4}  {'画质':^6}  标题"; print(header); print('-'*len(header))
                    for i, v in enumerate(res.playlist, 1):
                        cur = '✓' if v.is_current else ''; ser = '✓' if v.is_same_series else ''; q = v.best_quality or ''
                        print(f"{i:>3}  {cur:^4}  {ser:^4}  {q:^6}  {v.original_title or v.title}")
                want = Confirm.ask('保存为计划文件?', default=False) if RICH else (ask('保存为计划文件? (y/N)', 'N').lower() in ('y','yes','1'))
                if want:
                    path = Path(ask('保存文件名', 'plan.json')).expanduser()
                    plan = {'analyze': {'url': res.url, 'title': res.title, 'series_name': res.series_name, 'timestamp': res.timestamp},
                            'playlist': [asdict(p) for p in res.playlist]}
                    path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding='utf-8')
                    c_ok(f'已保存：{path}')
            elif opt in (2,3,4):
                url = choose_url(arg)
                res = analyze_watch(url, priority=CFG.priority, headless=CFG.headless, images_enabled=CFG.parse_with_images)
                if opt == 2:
                    items = [res.playlist[0]]
                elif opt == 3:
                    items = [x for x in res.playlist if x.is_same_series] or [res.playlist[0]]
                else:
                    items = list(res.playlist)
                c_info(f"将下载 {len(items)} 个条目到：{CFG.directory}")
                run_parallel_download(items)
            elif opt == 5:
                plan_path = choose_plan_path(arg)
                data = json.loads(plan_path.read_text(encoding='utf-8'))
                items = [VideoItem(**p) for p in data.get('playlist', [])]
                c_info(f"从计划载入 {len(items)} 个条目 → {CFG.directory}")
                choose = ask('直接全部下载? (Y/n)', 'Y').lower()
                if choose in ('n','no','0'):
                    print('输入要下载的编号（例：1,3,5），空回车默认全部：')
                    sel = input('> ').strip()
                    if sel:
                        idxs=[]
                        for part in re.split(r'[，,\s]+', sel):
                            if not part: continue
                            with contextlib.suppress(ValueError):
                                idxs.append(int(part))
                        items = [items[i-1] for i in idxs if 1<=i<=len(items)] or items
                run_parallel_download(items)
            else:
                c_warn('请输入 1-7 的数字。')
        except KeyboardInterrupt:
            console.print('\n[dim]已取消，返回菜单[/dim]')
        except Exception as e:
            c_err(str(e))

# ====================== 传统子命令 =======================

def build_parser(prog_name: str) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog=prog_name, description='视频批量下载器（交互式 + 多线程）')
    p.add_argument('--headless', dest='headless', action='store_true', help='启用无头浏览器 (默认)')
    p.add_argument('--no-headless', dest='headless', action='store_false', help='关闭无头，打开可视化调试')
    p.set_defaults(headless=True)
    p.add_argument('--threads', type=int, default=None, help='并发线程数，默认 3')
    p.add_argument('--stagger', type=float, default=None, help='任务提交错峰秒数，默认 0.8')
    p.add_argument('--dir', default=None, help='下载目录，默认 ~/Downloads/Videos')
    p.add_argument('--priority', choices=['highest','balanced','fastest'], default='highest')
    p.add_argument('--title-mode', choices=['share_h3','as_shown'], default=None, help='标题策略：share_h3=统一原名；as_shown=页面显示')
    p.add_argument('--parse-images', dest='parse_images', action='store_true', help='解析阶段加载图片 (默认开)')
    p.add_argument('--no-parse-images', dest='parse_images', action='store_false', help='解析阶段禁用图片加载')
    p.set_defaults(parse_images=True)

    sub = p.add_subparsers(dest='cmd')

    pa = sub.add_parser('analyze', help='解析 watch 页面（仅查看）')
    pa.add_argument('url', help='https://hanime1.me/watch?v=12345')
    pa.add_argument('--json', action='store_true')
    pa.add_argument('--save-plan', metavar='FILE')

    pd = sub.add_parser('download', help='解析并下载（可选 all/series-only/ids）')
    pd.add_argument('--url', help='watch 页面 URL（与 --plan 二选一）')
    pd.add_argument('--plan', help='使用 analyze 保存的计划 JSON')
    g = pd.add_mutually_exclusive_group()
    g.add_argument('--all', action='store_true', help='下载播放列表全部')
    g.add_argument('--series-only', action='store_true', help='仅下载同系列')
    g.add_argument('--ids', help="按编号下载，如 '1,3,5'")
    pd.add_argument('--delay', type=int, default=2, help='同线程连续文件延迟秒数（防风控）')
    pd.add_argument('--retry', type=int, default=3, help='失败重试次数')
    pd.add_argument('--json', action='store_true', help='结果 JSON 输出（仅汇总）')

    return p


def cli_main(argv: List[str]):
    if len(argv) == 1:
        interactive_main(); return

    parser = build_parser(Path(argv[0]).name)
    args = parser.parse_args(argv[1:])

    CFG.headless = bool(getattr(args, 'headless', True))
    CFG.parse_with_images = bool(getattr(args, 'parse_images', True))
    if getattr(args, 'threads', None) is not None:
        CFG.threads = max(1, args.threads)
    if getattr(args, 'stagger', None) is not None:
        CFG.stagger = max(0.0, float(args.stagger))
    if getattr(args, 'dir', None):
        CFG.directory = Path(args.dir).expanduser(); CFG.directory.mkdir(parents=True, exist_ok=True)
    if getattr(args, 'priority', None):
        CFG.priority = args.priority
    if getattr(args, 'title_mode', None):
        CFG.title_mode = args.title_mode

    if args.cmd == 'analyze':
        res = analyze_watch(args.url, priority=CFG.priority, headless=CFG.headless, images_enabled=CFG.parse_with_images)
        if args.json:
            print(json.dumps({'url':res.url,'title':res.title,'series_name':res.series_name,
                              'playlist':[asdict(p) for p in res.playlist],'timestamp':res.timestamp}, ensure_ascii=False, indent=2))
            return
        if RICH:
            tbl = Table(title="解析结果", title_style="info")
            tbl.add_column('#', justify='right'); tbl.add_column('当前', justify='center'); tbl.add_column('系列', justify='center'); tbl.add_column('画质', justify='center'); tbl.add_column('标题(统一原名)')
            for i, v in enumerate(res.playlist, 1):
                tbl.add_row(str(i), '✓' if v.is_current else '', '✓' if v.is_same_series else '', v.best_quality or '', v.original_title or v.title)
            console.print(tbl)
        else:
            print(f"\n{BOLD}标题{RESET}: {res.title or '-'}\n{BOLD}系列{RESET}: {res.series_name or '-'}\n{BOLD}条目{RESET}: {len(res.playlist)}\n")
            header = f"{'#':>3}  {'当前':^4}  {'系列':^4}  {'画质':^6}  标题"; print(header); print('-'*len(header))
            for i, v in enumerate(res.playlist, 1):
                cur = '✓' if v.is_current else ''; ser = '✓' if v.is_same_series else ''; q = v.best_quality or ''
                print(f"{i:>3}  {cur:^4}  {ser:^4}  {q:^6}  {v.original_title or v.title}")
        if args.save_plan:
            plan = {'analyze': {'url': res.url, 'title': res.title, 'series_name': res.series_name, 'timestamp': res.timestamp}, 'playlist': [asdict(p) for p in res.playlist]}
            Path(args.save_plan).write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding='utf-8')
            c_ok(f'已保存计划到 {args.save_plan}')
        return

    if args.cmd == 'download':
        if args.plan and Path(args.plan).exists():
            data = json.loads(Path(args.plan).read_text(encoding='utf-8'))
            items = [VideoItem(**p) for p in data.get('playlist', [])]
        elif args.url:
            res = analyze_watch(args.url, priority=CFG.priority, headless=CFG.headless, images_enabled=CFG.parse_with_images)
            if args.all:
                items = list(res.playlist)
            elif args.series_only:
                items = [x for x in res.playlist if x.is_same_series] or [res.playlist[0]]
            elif args.ids:
                idxs = []
                for part in re.split(r'[，,\s]+', args.ids.strip()):
                    if not part: continue
                    with contextlib.suppress(ValueError):
                        idxs.append(int(part))
                items = [res.playlist[i-1] for i in idxs if 1 <= i <= len(res.playlist)] or [res.playlist[0]]
            else:
                items = [res.playlist[0]]
        else:
            raise SystemExit('download 需要 --url 或 --plan')

        CFG.delay = int(getattr(args, 'delay', CFG.delay))
        CFG.retry = int(getattr(args, 'retry', CFG.retry))

        run_parallel_download(items)
        return

    interactive_main()

# ====================== 入口 =======================
if __name__ == '__main__':
    with contextlib.suppress(Exception):
        DEFAULT_DIR.mkdir(parents=True, exist_ok=True)
    cli_main(sys.argv)
