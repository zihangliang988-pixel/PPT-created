"""文档解析器 —— 提取上传文件或输入文字内容"""

from __future__ import annotations

import os
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    from docx import Document as DocxDocument
except ImportError:
    DocxDocument = None


class DocumentParser:
    """解析上传文件为纯文本"""

    @classmethod
    def parse(cls, file_path: str) -> str:
        """解析文件，返回 Markdown 格式文本"""
        ext = Path(file_path).suffix.lower()
        filename = os.path.basename(file_path)

        if ext == ".pdf":
            return cls._parse_pdf(file_path, filename)
        elif ext == ".docx":
            return cls._parse_docx(file_path, filename)
        elif ext in (".txt", ".md"):
            return cls._parse_plain(file_path, filename)
        else:
            raise ValueError(f"不支持的文件格式: {ext}，仅支持 PDF、DOCX、TXT、MD")

    @classmethod
    def parse_text(cls, text: str, label: str = "用户输入") -> str:
        """将用户手动输入的文本包装为结构化 Markdown。

        不做任意分段——纯文本原样保留，仅加来源标记。
        """
        text = text.strip()
        if not text:
            return ""
        return f"# 文档来源：{label}\n\n{text}"

    # ── 内部解析方法 ──

    @staticmethod
    def _parse_pdf(path: str, filename: str) -> str:
        if fitz is None:
            raise ImportError("缺少 PyMuPDF 库，请运行: pip install PyMuPDF")
        doc = fitz.open(path)
        parts = [f"# 文档来源：{filename}（共 {len(doc)} 页）\n"]
        for i, page in enumerate(doc):
            text = page.get_text().strip()
            if text:
                parts.append(f"\n## 第 {i + 1} 页\n\n{text}")
        return "\n".join(parts)

    @staticmethod
    def _parse_docx(path: str, filename: str) -> str:
        if DocxDocument is None:
            raise ImportError("缺少 python-docx 库，请运行: pip install python-docx")
        doc = DocxDocument(path)
        parts = [f"# 文档来源：{filename}\n"]
        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue
            style = (para.style.name or "").lower()
            if "heading 1" in style:
                parts.append(f"\n# {text}")
            elif "heading 2" in style:
                parts.append(f"\n## {text}")
            elif "heading 3" in style:
                parts.append(f"\n### {text}")
            else:
                parts.append(text)
        return "\n".join(parts)

    @staticmethod
    def _parse_plain(path: str, filename: str) -> str:
        """解析纯文本 / Markdown 文件"""
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        return f"# 文档来源：{filename}\n\n{content}"
