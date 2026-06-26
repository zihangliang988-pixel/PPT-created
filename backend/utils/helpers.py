"""通用辅助函数"""

import os
import uuid
import json
import re
from datetime import datetime, timezone


def generate_task_id() -> str:
    """生成唯一任务 ID"""
    return f"task_{uuid.uuid4().hex[:12]}"


def ensure_dir(path: str):
    """确保目录存在"""
    os.makedirs(path, exist_ok=True)


def safe_filename(filename: str) -> str:
    """清理文件名，移除不安全字符"""
    name, ext = os.path.splitext(filename)
    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    return f"{name}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}{ext}"


def format_file_size(size_bytes: int) -> str:
    """格式化文件大小"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def parse_json_output(text: str):
    """从 LLM 输出中提取 JSON，增强容错能力"""
    import logging
    logger = logging.getLogger(__name__)
    
    # 记录原始输出（用于调试）
    if text and len(text) < 2000:
        logger.debug(f"LLM 原始输出: {text[:500]}...")
    
    # 尝试直接解析
    text = text.strip()
    
    # 移除开头的解释文字 — 查找第一个 JSON 起始字符 { 或 [
    first_json = re.search(r'[\[{]', text)
    if first_json:
        text = text[first_json.start():]
    
    # 移除 markdown 代码块标记（可能在 JSON 前后）
    text = re.sub(r"^```(?:json)?\s*\n?", "", text)
    text = re.sub(r"\n?\s*```$", "", text)
    text = text.strip()
    
    # 尝试直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.debug(f"直接解析失败: {e}")
        pass
    
    # 尝试提取 JSON 对象 {...}
    obj_match = re.search(r"\{[\s\S]*\}", text)
    if obj_match:
        try:
            return json.loads(obj_match.group())
        except json.JSONDecodeError:
            pass
    
    # 尝试提取 JSON 数组 [...]
    arr_match = re.search(r"\[[\s\S]*\]", text)
    if arr_match:
        try:
            return json.loads(arr_match.group())
        except json.JSONDecodeError:
            pass
    
    # 尝试修复常见的 JSON 格式问题
    try:
        # 添加缺失的引号
        fixed = text
        fixed = re.sub(r'(\{|\[|\,)\s*(\w+)\s*:', r'\1 "\2":', fixed)  # 键添加引号
        fixed = re.sub(r':\s*(\w+)(\s*[,}\]])', r': "\1"\2', fixed)   # 简单值添加引号
        fixed = re.sub(r"'", '"', fixed)  # 单引号转双引号
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass
    
    logger.error(f"无法解析 LLM 输出: {text[:200]}")
    raise ValueError("无法从 LLM 输出中解析 JSON")
