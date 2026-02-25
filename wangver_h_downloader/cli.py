"""
CLI 入口与 Rich 终端界面：主菜单、交互式流程、统一进度与结果展示。
"""
import asyncio
import sys
from pathlib import Path
from typing import List, Optional

from rich.console import Console, Group
from rich.panel import Panel
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    DownloadColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
)
from rich.prompt import Prompt, IntPrompt, Confirm
from rich.rule import Rule
from rich.table import Table
from rich.text import Text
from rich import box

from . import ui_theme as theme
from .config import (
    DEFAULT_OUTPUT_DIR,
    DEFAULT_USER_DATA_DIR,
    DEFAULT_MAX_CONCURRENT_TASKS,
    DEFAULT_CHUNK_THREADS,
    DEFAULT_QUALITY,
    QUALITY_OPTIONS,
)
from .parser import (
    VideoTarget,
    parse_single_page_html,
    collect_urls_from_batch_file,
    extract_list_page_video_links,
)
from .browser_cf import BrowserCFHandler, SessionCredentials
from .downloader import download_task


# 全局控制台（单例）
console = Console(force_terminal=True, no_color=False)


def _cf_alert_rich(message: str) -> None:
    """CF 触发时在 Rich 控制台输出醒目提示。"""
    console.print()
    console.print(Panel(
        Text(message, style="bold red"),
        title="[bold]🚨 Cloudflare 拦截[/bold]",
        border_style="red",
        box=box.DOUBLE,
        padding=(1, 2),
    ))
    console.print("[dim]请在弹出窗口中完成验证后，回到此处按 Enter 继续。[/]")
    console.print()


def show_banner() -> None:
    """显示应用横幅。"""
    title = Text("WangVer H-Downloader", style="bold magenta")
    subtitle = Text("专为 hanime1.me 定制 · 浏览器过 CF + 多线程下载", style="dim white")
    console.print()
    console.print(Rule(style="cyan"))
    console.print(Panel(
        Group(title, Text(), subtitle),
        border_style="blue",
        box=box.ROUNDED,
        padding=(1, 3),
    ))
    console.print(Rule(style="cyan"))
    console.print()


def show_main_menu() -> str:
    """显示主菜单并返回用户选择。"""
    table = Table.grid(expand=True)
    table.add_column(style="bold yellow", width=4)
    table.add_column(style="dim white")
    table.add_row("1", "单链接下载 — 输入一集视频页 URL")
    table.add_row("2", "批量下载 — 从 .txt 文件导入多个链接")
    table.add_row("3", "列表页下载 — 输入系列/列表页 URL 自动抓取全部")
    table.add_row("4", "设置 — 输出目录、并发数、画质等")
    table.add_row("0", "退出")
    console.print(Panel(
        table,
        title="[bold blue] 请选择操作[/]",
        border_style="blue",
        box=box.ROUNDED,
        padding=(1, 2),
    ))
    return Prompt.ask(
        "[cyan]请输入选项[/]",
        choices=["0", "1", "2", "3", "4"],
        default="1",
    )


def prompt_settings(
    default_output: Path,
    default_max_tasks: int,
    default_chunk_threads: int,
    default_quality: str,
) -> tuple:
    """交互式设置并返回 (output_dir, max_tasks, chunk_threads, quality)。"""
    console.print(Panel(
        "[dim]修改以下设置（直接回车保留当前值）[/]",
        border_style="blue",
        box=box.ROUNDED,
    ))
    out = Prompt.ask("  输出目录", default=str(default_output))
    output_dir = Path(out).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    max_tasks = IntPrompt.ask("  最大并行下载数", default=default_max_tasks)
    chunk_threads = IntPrompt.ask("  单任务分块线程数", default=default_chunk_threads)
    quality = Prompt.ask(
        f"  画质 [{'/'.join(QUALITY_OPTIONS)}]",
        default=default_quality,
        choices=list(QUALITY_OPTIONS),
    )
    console.print("[green]已更新设置[/]")
    return output_dir, max_tasks, chunk_threads, quality


def create_progress(description: str = "下载中") -> Progress:
    """创建统一风格的进度条。"""
    return Progress(
        SpinnerColumn(style="cyan"),
        TextColumn("[bold]{task.description}", style="cyan"),
        BarColumn(bar_width=40, style="bar.back", complete_style="bar.complete"),
        TaskProgressColumn(),
        DownloadColumn(),
        TimeRemainingColumn(),
        console=console,
        expand=True,
    )


def show_result_table(success: List[str], failed: List[str], output_dir: Path) -> None:
    """用表格展示下载结果汇总。"""
    table = Table(title="下载结果", box=box.ROUNDED, border_style="blue")
    table.add_column("状态", style="bold", width=6)
    table.add_column("文件 / 说明")
    for name in success:
        table.add_row("[green]成功[/]", name)
    for name in failed:
        table.add_row("[red]失败[/]", name)
    if success:
        table.add_row("[dim]保存位置[/]", str(output_dir), end_section=True)
    console.print(Panel(table, border_style="blue", box=box.ROUNDED))
    console.print()


async def run_single(
    target: VideoTarget,
    output_dir: Path,
    credentials: Optional[SessionCredentials],
    chunk_threads: int = DEFAULT_CHUNK_THREADS,
) -> Optional[Path]:
    """单链接：根据已解析的 target 下载。"""
    console.print(Panel(
        f"[cyan]{target.title}[/]\n[dim]{target.direct_url[:80]}...[/]",
        title="解析结果",
        border_style="blue",
        box=box.ROUNDED,
    ))
    with create_progress(target.title) as progress:
        task_id = progress.add_task(target.title, total=None)
        received = [0]

        def cb(n: int):
            received[0] += n
            progress.update(task_id, completed=received[0])

        path = await download_task(
            target.direct_url,
            target.title,
            output_dir,
            credentials,
            chunk_threads=chunk_threads,
            progress_callback=cb,
        )
    console.print(f"[green]✓ 已保存: {path}[/]")
    return path


async def run_batch(
    urls: List[str],
    output_dir: Path,
    max_concurrent_tasks: int = DEFAULT_MAX_CONCURRENT_TASKS,
    chunk_threads: int = DEFAULT_CHUNK_THREADS,
    preferred_quality: str = DEFAULT_QUALITY,
    user_data_dir: Optional[Path] = None,
    headless: bool = False,
) -> List[str]:
    """批量：启动浏览器 -> 逐个打开页面解析 -> 取得凭证后关闭浏览器 -> 并发下载。返回成功保存的文件名列表。"""
    handler = BrowserCFHandler(
        user_data_dir=user_data_dir or DEFAULT_USER_DATA_DIR,
        headless=headless,
        on_cf_triggered=_cf_alert_rich,
    )
    await handler.start()
    credentials: Optional[SessionCredentials] = None
    targets: List[VideoTarget] = []

    try:
        for i, page_url in enumerate(urls):
            console.print(f"[cyan][{i+1}/{len(urls)}][/] 解析: [dim]{page_url[:60]}...[/]")
            creds = await handler.goto_and_handle_cf(page_url, wait_for_enter=True)
            credentials = creds
            html = await handler.get_page_content()
            t = parse_single_page_html(html, page_url, preferred_quality=preferred_quality)
            if t:
                targets.append(t)
                console.print(f"  [green]✓[/] {t.title}")
            else:
                console.print(f"  [yellow]跳过: 无法解析直链[/]")

        if not targets:
            console.print("[yellow]没有可下载的目标。[/]")
            return []

        # 已取得凭证与目标，关闭浏览器后再下载（无需保持浏览器打开）
        await handler.close()
        handler = None

        console.print(Panel(
            f"共 [bold]{len(targets)}[/] 个任务，开始并发下载…",
            border_style="blue",
            box=box.ROUNDED,
        ))
        sem = asyncio.Semaphore(max_concurrent_tasks)
        success_list: List[str] = []

        async def run_one(t: VideoTarget):
            async with sem:
                with create_progress(t.title) as progress:
                    task_id = progress.add_task(t.title, total=None)
                    received = [0]

                    def cb(n: int):
                        received[0] += n
                        progress.update(task_id, completed=received[0])

                    try:
                        await download_task(
                            t.direct_url,
                            t.title,
                            output_dir,
                            credentials,
                            chunk_threads=chunk_threads,
                            progress_callback=cb,
                        )
                        success_list.append(t.title)
                        console.print(f"[green]✓ 完成: {t.title}[/]")
                    except Exception as e:
                        console.print(f"[red]✗ {t.title}: {e}[/]")

        await asyncio.gather(*[run_one(t) for t in targets])
        return success_list
    finally:
        if handler is not None:
            await handler.close()


async def run_list_page(
    list_page_url: str,
    output_dir: Path,
    max_concurrent_tasks: int = DEFAULT_MAX_CONCURRENT_TASKS,
    chunk_threads: int = DEFAULT_CHUNK_THREADS,
    preferred_quality: str = DEFAULT_QUALITY,
    user_data_dir: Optional[Path] = None,
    headless: bool = False,
) -> List[str]:
    """列表页：打开列表页 -> 提取所有单集链接 -> 关闭浏览器 -> 同批量流程。返回成功列表。"""
    handler = BrowserCFHandler(
        user_data_dir=user_data_dir or DEFAULT_USER_DATA_DIR,
        headless=headless,
        on_cf_triggered=_cf_alert_rich,
    )
    await handler.start()
    try:
        console.print(Panel(
            f"[cyan]正在加载列表页[/]\n[dim]{list_page_url}[/]",
            border_style="blue",
            box=box.ROUNDED,
        ))
        await handler.goto_and_handle_cf(list_page_url, wait_for_enter=True)
        html = await handler.get_page_content()
        urls = extract_list_page_video_links(html, list_page_url)
        console.print(f"[green]共解析到 {len(urls)} 个视频链接。[/]")
    finally:
        await handler.close()

    if not urls:
        console.print("[yellow]未解析到任何视频链接。[/]")
        return []
    return await run_batch(
        urls,
        output_dir,
        max_concurrent_tasks=max_concurrent_tasks,
        chunk_threads=chunk_threads,
        preferred_quality=preferred_quality,
        user_data_dir=user_data_dir,
        headless=headless,
    )


# ---------- 交互式流程 ----------

_session_output_dir = DEFAULT_OUTPUT_DIR
_session_max_tasks = DEFAULT_MAX_CONCURRENT_TASKS
_session_chunk_threads = DEFAULT_CHUNK_THREADS
_session_quality = DEFAULT_QUALITY


def run_interactive() -> None:
    """无参数启动时：主菜单循环。"""
    show_banner()
    while True:
        choice = show_main_menu()
        if choice == "0":
            console.print("[dim]再见。[/]")
            return
        if choice == "4":
            global _session_output_dir, _session_max_tasks, _session_chunk_threads, _session_quality
            _session_output_dir, _session_max_tasks, _session_chunk_threads, _session_quality = prompt_settings(
                _session_output_dir, _session_max_tasks, _session_chunk_threads, _session_quality,
            )
            continue

        output_dir = _session_output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        if choice == "1":
            url = Prompt.ask("[cyan]请输入单集视频页 URL[/]")
            if not url.strip():
                console.print("[yellow]已取消。[/]")
                continue

            async def do_single():
                handler = BrowserCFHandler(
                    user_data_dir=DEFAULT_USER_DATA_DIR,
                    headless=False,
                    on_cf_triggered=_cf_alert_rich,
                )
                await handler.start()
                try:
                    creds = await handler.goto_and_handle_cf(url, wait_for_enter=True)
                    html = await handler.get_page_content()
                    target = parse_single_page_html(html, url, preferred_quality=_session_quality)
                    if target:
                        # 已取得凭证与解析结果，关闭浏览器后再下载
                        await handler.close()
                        await run_single(target, output_dir, creds, chunk_threads=_session_chunk_threads)
                        show_result_table([target.title], [], output_dir)
                    else:
                        console.print("[red]无法从页面解析出视频直链或标题。[/]")
                finally:
                    await handler.close()

            asyncio.run(do_single())

        elif choice == "2":
            path_str = Prompt.ask("[cyan]请输入 .txt 文件路径（每行一个 URL）[/]")
            path = Path(path_str).expanduser().resolve()
            if not path.exists():
                console.print(f"[red]文件不存在: {path}[/]")
                continue
            urls = collect_urls_from_batch_file(path)
            if not urls:
                console.print("[red]文件中没有有效 URL。[/]")
                continue
            console.print(f"[green]已读取 {len(urls)} 个链接。[/]")
            success = asyncio.run(run_batch(
                urls, output_dir,
                max_concurrent_tasks=_session_max_tasks,
                chunk_threads=_session_chunk_threads,
                preferred_quality=_session_quality,
            ))
            show_result_table(success, [] if len(success) == len(urls) else [f"共 {len(urls)} 条链接，成功 {len(success)} 条"], output_dir)

        elif choice == "3":
            list_url = Prompt.ask("[cyan]请输入系列/列表页 URL[/]")
            if not list_url.strip():
                console.print("[yellow]已取消。[/]")
                continue
            success = asyncio.run(run_list_page(
                list_url, output_dir,
                max_concurrent_tasks=_session_max_tasks,
                chunk_threads=_session_chunk_threads,
                preferred_quality=_session_quality,
            ))
            show_result_table(success, [], output_dir)

        if choice in ("1", "2", "3"):
            if not Confirm.ask("[cyan]是否继续使用主菜单[/]", default=True):
                break
    console.print()


def main() -> None:
    """命令行入口：有参数则直接执行；无参数则进入交互式主菜单。"""
    import argparse
    parser = argparse.ArgumentParser(
        description="WangVer H-Downloader - 专为 hanime1.me 定制的高效视频下载工具",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("url", nargs="?", help="单集视频页 URL 或系列列表页 URL")
    parser.add_argument("-b", "--batch", type=Path, help="批量 URL 文件路径（.txt，每行一个链接）")
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT_DIR, help="下载输出目录")
    parser.add_argument("--max-tasks", type=int, default=DEFAULT_MAX_CONCURRENT_TASKS, help="最大并行下载任务数")
    parser.add_argument("--chunk-threads", type=int, default=DEFAULT_CHUNK_THREADS, help="单任务分块下载线程数")
    parser.add_argument("--user-data-dir", type=Path, default=DEFAULT_USER_DATA_DIR, help="浏览器用户数据目录")
    parser.add_argument("--headless", action="store_true", help="使用无头浏览器（不推荐，CF 易拦截）")
    parser.add_argument("--no-ui", action="store_true", help="禁用交互菜单，仅显示帮助")
    parser.add_argument("--quality", type=str, default=DEFAULT_QUALITY, choices=list(QUALITY_OPTIONS), help="优先画质")
    args = parser.parse_args()

    if not args.url and not args.batch and not args.no_ui:
        run_interactive()
        return

    if args.url or args.batch:
        output_dir = Path(args.output).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        if args.batch:
            urls = collect_urls_from_batch_file(args.batch)
            if not urls:
                console.print("[red]批量文件中没有有效 URL。[/]")
                sys.exit(1)
            asyncio.run(run_batch(
                urls,
                output_dir,
                max_concurrent_tasks=args.max_tasks,
                chunk_threads=args.chunk_threads,
                preferred_quality=args.quality,
                user_data_dir=args.user_data_dir,
                headless=args.headless,
            ))
        elif args.url:
            if "/videos" in args.url or "/series" in args.url or "/search" in args.url:
                asyncio.run(run_list_page(
                    args.url,
                    output_dir,
                    max_concurrent_tasks=args.max_tasks,
                    chunk_threads=args.chunk_threads,
                    preferred_quality=args.quality,
                    user_data_dir=args.user_data_dir,
                    headless=args.headless,
                ))
            else:
                async def single_flow():
                    handler = BrowserCFHandler(
                        user_data_dir=args.user_data_dir,
                        headless=args.headless,
                        on_cf_triggered=_cf_alert_rich,
                    )
                    await handler.start()
                    try:
                        creds = await handler.goto_and_handle_cf(args.url, wait_for_enter=True)
                        html = await handler.get_page_content()
                        target = parse_single_page_html(html, args.url, preferred_quality=args.quality)
                        if target:
                            await handler.close()
                            await run_single(target, output_dir, creds, chunk_threads=args.chunk_threads)
                        else:
                            console.print("[red]无法从页面解析出视频直链或标题。[/]")
                    finally:
                        await handler.close()

                asyncio.run(single_flow())
        return

    parser.print_help()
    console.print()
    console.print(Panel(
        "[dim]示例：[/]\n"
        "  单集   python -m wangver_h_downloader.cli \"https://hanime1.me/watch/xxx\"\n"
        "  批量   python -m wangver_h_downloader.cli -b urls.txt -o ./downloads\n"
        "  列表   python -m wangver_h_downloader.cli \"https://hanime1.me/videos/...\"\n\n"
        "[bold]直接运行不加参数将进入交互式菜单。[/]",
        title="用法",
        border_style="blue",
        box=box.ROUNDED,
    ))
    sys.exit(0)


if __name__ == "__main__":
    main()
