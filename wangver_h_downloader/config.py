"""
全局配置：输出目录、并发数、浏览器用户数据目录等。
"""
from pathlib import Path
import os

# 默认输出目录（下载视频存放位置）
DEFAULT_OUTPUT_DIR = Path(os.getenv("WANGVER_OUTPUT", "./downloads")).resolve()

# 浏览器用户数据目录（持久化 Cookies/Session，减少重复验证）
DEFAULT_USER_DATA_DIR = Path(os.getenv("WANGVER_USER_DATA", "./browser_user_data")).resolve()

# 并发控制（提高以提升下载速度，走代理时建议保持或适当调低）
DEFAULT_MAX_CONCURRENT_TASKS = 3   # 同时下载的视频数量
DEFAULT_CHUNK_THREADS = 8          # 单任务分块下载的并发块数（越多越快，受代理/带宽影响）
DEFAULT_CHUNK_SIZE = 4 * 1024 * 1024  # 单块大小 4MB，减少请求次数

# 目标平台
TARGET_BASE_URL = "https://hanime1.me"

# 文件名非法字符（需剔除）
INVALID_FILENAME_CHARS = r'[\\/:*?"<>|]'

# 临时文件后缀（断点续传）
PART_SUFFIX = ".part"

# 画质选项（解析时优先选择）
QUALITY_OPTIONS = ("360p", "480p", "720p", "1080p")
DEFAULT_QUALITY = "1080p"

# CF 特征检测
CF_FORBIDDEN_STATUS = 403
CF_INDICATOR_TEXTS = ("Just a moment", "cf-turnstile", "Checking your browser")
CF_INDICATOR_SELECTORS = [
    ".cf-turnstile",
    "#challenge-running",
    "#challenge-form",
]
