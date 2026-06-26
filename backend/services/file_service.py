"""文件上传/清理服务"""

from __future__ import annotations

import os
import shutil
import logging
from pathlib import Path
from typing import Optional

from config import settings
from utils.helpers import ensure_dir, safe_filename

logger = logging.getLogger(__name__)


class FileService:
    """文件管理服务"""

    def __init__(self):
        self._upload_dir = Path(settings.upload_dir).absolute()
        self._output_dir = Path(settings.output_dir).absolute()
        ensure_dir(str(self._upload_dir))
        ensure_dir(str(self._output_dir))

    def save_upload(self, file_data: bytes, original_name: str) -> str:
        """保存上传文件，返回路径"""
        safe_name = safe_filename(original_name)
        path = self._upload_dir / safe_name
        with open(path, "wb") as f:
            f.write(file_data)
        logger.info(f"文件已保存: {path}")
        return str(path)

    def save_text_as_file(self, text: str, title: str = "输入内容") -> str:
        """将输入文字保存为临时文件"""
        name = safe_filename(f"{title}.txt")
        path = self._upload_dir / name
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return str(path)

    def get_output_path(self, task_id: str) -> str:
        """获取任务输出 PPT 路径"""
        return str(self._output_dir / f"{task_id}.pptx")

    def get_file_size(self, path: str) -> Optional[int]:
        """获取文件大小"""
        try:
            return os.path.getsize(path)
        except OSError:
            return None

    def file_exists(self, path: str) -> bool:
        """检查文件是否存在"""
        return os.path.isfile(path)

    def cleanup_task(self, task_id: str):
        """清理任务相关文件"""
        ppt_path = self._output_dir / f"{task_id}.pptx"
        if ppt_path.exists():
            ppt_path.unlink()
            logger.info(f"已清理: {ppt_path}")

    def cleanup_all(self):
        """清理所有临时文件"""
        if self._upload_dir.exists():
            shutil.rmtree(str(self._upload_dir))
            ensure_dir(str(self._upload_dir))
        if self._output_dir.exists():
            shutil.rmtree(str(self._output_dir))
            ensure_dir(str(self._output_dir))
        logger.info("已清理所有临时文件")
