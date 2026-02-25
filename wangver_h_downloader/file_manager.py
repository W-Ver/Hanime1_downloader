"""
断点续传与媒体文件管理：.part 识别、智能重命名、输出目录管理。
"""
import re
from pathlib import Path
from typing import Optional

from .config import DEFAULT_OUTPUT_DIR, INVALID_FILENAME_CHARS, PART_SUFFIX


def sanitize_filename(name: str) -> str:
    """剔除文件名中的非法字符，便于媒体库刮削。"""
    if not name or not name.strip():
        return "未命名"
    s = re.sub(INVALID_FILENAME_CHARS, "", name.strip())
    s = re.sub(r"\s+", " ", s)
    return s[:200].strip() if len(s) > 200 else s


def find_part_file(output_dir: Path, base_name: str, ext: str) -> Optional[Path]:
    """
    在输出目录中查找与 base_name + ext 对应的 .part 临时文件，用于断点续传。
    约定：part 文件名为 {base_name}{ext}.part 或 {base_name}.part。
    """
    output_dir = Path(output_dir)
    if not output_dir.exists():
        return None
    candidate = output_dir / f"{base_name}{ext}{PART_SUFFIX}"
    if candidate.exists():
        return candidate
    candidate2 = output_dir / f"{base_name}{PART_SUFFIX}"
    if candidate2.exists():
        return candidate2
    return None


def build_output_path(output_dir: Path, title: str, ext: str = ".mp4") -> Path:
    """根据标题生成最终输出文件路径。"""
    safe = sanitize_filename(title)
    return Path(output_dir) / f"{safe}{ext}"
