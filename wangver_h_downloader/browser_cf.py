"""
浏览器模拟与 CF 盾牌半自动化接管：
真实浏览器 + 非无头 + 用户数据持久化 + 智能拦截挂起 + 人工介入 + 会话接力。
"""
import asyncio
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Callable, Awaitable

from playwright.async_api import async_playwright, BrowserContext, Page, Response

from .config import (
    DEFAULT_USER_DATA_DIR,
    CF_FORBIDDEN_STATUS,
    CF_INDICATOR_TEXTS,
    CF_INDICATOR_SELECTORS,
)


@dataclass
class SessionCredentials:
    """验证通过后的会话凭证，供下载引擎使用。"""
    cookies: list  # 列表 of dict with name, value, domain, path 等
    user_agent: str


def _default_cf_alert_callback(message: str) -> None:
    """默认：在控制台输出醒目提示。"""
    print("\n" + "=" * 60)
    print("🚨 " + message)
    print("=" * 60 + "\n")


class BrowserCFHandler:
    """
    真实浏览器驱动 + CF 检测 + 挂起/恢复 + Cookies/UA 提取。
    """

    def __init__(
        self,
        user_data_dir: Optional[Path] = None,
        headless: bool = False,
        on_cf_triggered: Optional[Callable[[str], None]] = None,
    ):
        self.user_data_dir = Path(user_data_dir or DEFAULT_USER_DATA_DIR)
        self.headless = headless
        self.on_cf_triggered = on_cf_triggered or _default_cf_alert_callback

        self._playwright = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._cf_detected = asyncio.Event()  # 触发 CF 时 set
        self._cf_passed = asyncio.Event()   # 验证通过后 set
        self._last_response_status: Optional[int] = None

    async def start(self) -> None:
        """启动 Playwright 与浏览器，使用持久化用户数据目录。"""
        self._playwright = await async_playwright().start()
        self._context = await self._playwright.chromium.launch_persistent_context(
            str(self.user_data_dir),
            headless=self.headless,
            channel="chrome",
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width": 1280, "height": 720},
        )
        self._page = await self._context.new_page()

        # 监听响应：403 时标记 CF 触发
        async def on_response(response: Response):
            self._last_response_status = response.status
            if response.status == CF_FORBIDDEN_STATUS:
                self._cf_detected.set()

        self._page.on("response", on_response)

    async def goto_and_handle_cf(
        self,
        url: str,
        wait_until: str = "domcontentloaded",
        real_content_selector: Optional[str] = None,
        wait_for_enter: bool = True,
    ) -> SessionCredentials:
        """
        导航至目标页，若检测到 CF 则挂起并提示人工介入，验证通过后提取凭证。
        - real_content_selector: 真实视频页加载后的 DOM 选择器，用于轮询判断是否通过。
        - wait_for_enter: 是否同时等待用户在终端按 Enter 确认放行。
        """
        self._cf_detected.clear()
        self._cf_passed.clear()
        await self._page.goto(url, wait_until=wait_until, timeout=60000)

        # 轮询：若当前页有 CF 特征则挂起并提示
        async def check_and_pause():
            while True:
                await asyncio.sleep(0.5)
                if self._cf_detected.is_set():
                    self.on_cf_triggered(
                        "触发 Cloudflare 拦截，请在弹出的浏览器窗口中手动完成验证！"
                    )
                    break
                content = await self._page.content()
                if any(t in content for t in CF_INDICATOR_TEXTS):
                    self._cf_detected.set()
                    self.on_cf_triggered(
                        "触发 Cloudflare 拦截，请在弹出的浏览器窗口中手动完成验证！"
                    )
                    break
                for sel in CF_INDICATOR_SELECTORS:
                    try:
                        if await self._page.locator(sel).count() > 0:
                            self._cf_detected.set()
                            self.on_cf_triggered(
                                "触发 Cloudflare 拦截，请在弹出的浏览器窗口中手动完成验证！"
                            )
                            break
                    except Exception:
                        pass
                else:
                    # 本轮未发现 CF 特征，结束轮询
                    break
                break

        await check_and_pause()

        # 若触发了 CF，等待“验证通过”：轮询真实内容或用户按 Enter
        page_content = await self._page.content()
        if self._cf_detected.is_set() or any(t in page_content for t in CF_INDICATOR_TEXTS):
            async def wait_real_content():
                while True:
                    await asyncio.sleep(1)
                    if real_content_selector:
                        try:
                            if await self._page.locator(real_content_selector).count() > 0:
                                self._cf_passed.set()
                                return
                        except Exception:
                            pass
                    # 或 403 消失、状态码正常
                    if self._last_response_status != CF_FORBIDDEN_STATUS:
                        content = await self._page.content()
                        if not any(t in content for t in CF_INDICATOR_TEXTS):
                            self._cf_passed.set()
                            return

            if wait_for_enter:
                loop = asyncio.get_event_loop()
                await asyncio.gather(
                    wait_real_content(),
                    asyncio.get_event_loop().run_in_executor(None, lambda: input("验证完成后请按 Enter 继续... ")),
                )
            else:
                await wait_real_content()

        # 提取 Cookies 与 User-Agent
        cookies = await self._context.cookies()
        ua = await self._page.evaluate("() => navigator.userAgent")
        return SessionCredentials(cookies=cookies, user_agent=ua)

    async def get_page_content(self) -> str:
        """获取当前页面 HTML，用于解析直链与标题。"""
        if self._page:
            return await self._page.content()
        return ""

    def get_page(self) -> Optional[Page]:
        return self._page

    async def close(self) -> None:
        if self._context:
            await self._context.close()
        if self._playwright:
            await self._playwright.stop()
        self._page = None
        self._context = None
        self._playwright = None
