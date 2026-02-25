"""
多线程/并发下载引擎：接力浏览器凭证，分块多线程下载，多任务并发。
"""
import asyncio
from pathlib import Path
from typing import Optional, Callable

import httpx
import aiofiles

from .config import (
    DEFAULT_CHUNK_SIZE,
    DEFAULT_CHUNK_THREADS,
    PART_SUFFIX,
)
from .browser_cf import SessionCredentials
from .file_manager import find_part_file, sanitize_filename


def _cookies_to_headers(cookies: list) -> dict:
    """将 Playwright cookies 列表转为 Cookie 请求头。"""
    parts = []
    for c in cookies:
        name = c.get("name")
        value = c.get("value")
        if name and value is not None:
            parts.append(f"{name}={value}")
    if not parts:
        return {}
    return {"Cookie": "; ".join(parts)}


# 下载请求：跟随重定向、较长超时（走代理时需更长时间）；默认走系统/环境代理
HTTPX_DOWNLOAD_KWARGS = {"follow_redirects": True, "timeout": 120, "trust_env": True}


async def _head_for_range(url: str, credentials: Optional[SessionCredentials]) -> tuple[int, bool]:
    """HEAD 请求获取文件大小与是否支持 Range。"""
    headers = {}
    if credentials:
        headers["User-Agent"] = credentials.user_agent
        headers.update(_cookies_to_headers(credentials.cookies))
    async with httpx.AsyncClient(**HTTPX_DOWNLOAD_KWARGS) as client:
        r = await client.head(url, headers=headers)
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        accept_ranges = (r.headers.get("accept-ranges") or "").lower() == "bytes"
        return total, accept_ranges


async def download_single_chunk(
    client: httpx.AsyncClient,
    url: str,
    start: int,
    end: int,
    dest_path: Path,
    credentials: Optional[SessionCredentials],
    progress_callback: Optional[Callable[[int], None]],
) -> int:
    """下载一个分块并写入文件指定偏移，返回写入字节数。"""
    headers = {"Range": f"bytes={start}-{end}"}
    if credentials:
        headers["User-Agent"] = credentials.user_agent
        headers.update(_cookies_to_headers(credentials.cookies))

    r = await client.get(url, headers=headers)
    r.raise_for_status()
    data = r.content
    n = len(data)

    async with aiofiles.open(dest_path, "r+b") as f:
        await f.seek(start)
        await f.write(data)

    if progress_callback:
        progress_callback(n)
    return n


async def download_chunked(
    url: str,
    dest_path: Path,
    credentials: Optional[SessionCredentials],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    max_concurrent_chunks: int = DEFAULT_CHUNK_THREADS,
    progress_callback: Optional[Callable[[int], None]] = None,
    semaphore: Optional[asyncio.Semaphore] = None,
) -> Path:
    """
    分块并发下载到 dest_path（可为 .part 路径，支持断点续传：已存在则跳过已下载区间）。
    返回最终文件路径（若为 .part 则返回 .part 路径，由调用方在完成后重命名）。
    """
    total, accept_ranges = await _head_for_range(url, credentials)
    if total <= 0:
        # 不支持 Content-Length 时整块下载
        headers = {}
        if credentials:
            headers["User-Agent"] = credentials.user_agent
            headers.update(_cookies_to_headers(credentials.cookies))
        async with httpx.AsyncClient(**HTTPX_DOWNLOAD_KWARGS) as client:
            r = await client.get(url, headers=headers)
            r.raise_for_status()
            async with aiofiles.open(dest_path, "wb") as f:
                await f.write(r.content)
        return dest_path

    # 确定已下载范围（断点续传）
    done_ranges: list[tuple[int, int]] = []
    if dest_path.exists():
        size = dest_path.stat().st_size
        if size > 0:
            done_ranges.append((0, min(size, total) - 1))

    def _ranges_to_download() -> list[tuple[int, int]]:
        if not accept_ranges:
            return [(0, total - 1)] if total > 0 else []
        needed = []
        pos = 0
        while pos < total:
            end = min(pos + chunk_size, total) - 1
            # 检查是否已被 done_ranges 覆盖
            covered = False
            for a, b in done_ranges:
                if a <= pos and end <= b:
                    covered = True
                    break
            if not covered:
                needed.append((pos, end))
            pos = end + 1
        return needed

    chunks = _ranges_to_download()
    if not chunks:
        return dest_path

    # 确保目标文件存在且长度足够，便于分块写入
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    if not dest_path.exists():
        async with aiofiles.open(dest_path, "wb") as f:
            await f.seek(total - 1)
            await f.write(b"\x00")
    else:
        current_size = dest_path.stat().st_size
        if current_size < total:
            async with aiofiles.open(dest_path, "r+b") as f:
                await f.seek(total - 1)
                await f.write(b"\x00")

    async def do_one(chunk_start: int, chunk_end: int):
        async with (semaphore or asyncio.Semaphore(max_concurrent_chunks)):
            async with httpx.AsyncClient(**HTTPX_DOWNLOAD_KWARGS) as client:
                await download_single_chunk(
                    client, url, chunk_start, chunk_end,
                    dest_path, credentials, progress_callback,
                )

    await asyncio.gather(*[do_one(s, e) for s, e in chunks])
    return dest_path


async def download_task(
    url: str,
    title: str,
    output_dir: Path,
    credentials: Optional[SessionCredentials],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_threads: int = DEFAULT_CHUNK_THREADS,
    progress_callback: Optional[Callable[[int], None]] = None,
) -> Path:
    """
    单任务：解析文件名、检查 .part 断点、分块下载、完成后重命名为最终文件名。
    """
    safe_title = sanitize_filename(title)
    ext = ".mp4" if ".m3u8" not in url.lower() else ".m3u8"
    final_name = safe_title + ext
    final_path = output_dir / final_name

    part_path = find_part_file(output_dir, safe_title, ext)
    if part_path is None:
        part_path = output_dir / (safe_title + ext + PART_SUFFIX)

    await download_chunked(
        url,
        part_path,
        credentials,
        chunk_size=chunk_size,
        max_concurrent_chunks=chunk_threads,
        progress_callback=progress_callback,
    )

    if part_path.suffix == PART_SUFFIX or part_path.name.endswith(PART_SUFFIX):
        part_path.rename(final_path)
        return final_path
    return part_path
