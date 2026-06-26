"""内容分析器 — 分析文档结构，智能推荐页数"""

from __future__ import annotations

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ContentAnalyzer:
    """分析文档内容，提取结构信息"""

    @staticmethod
    def analyze(content: str) -> dict:
        """分析文档结构，返回结构化信息"""
        lines = content.split("\n")
        
        # 统计标题层级
        h1_count = 0
        h2_count = 0
        h3_count = 0
        headings = []
        
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("# "):
                h1_count += 1
                headings.append(("h1", stripped[2:].strip()))
            elif stripped.startswith("## "):
                h2_count += 1
                headings.append(("h2", stripped[3:].strip()))
            elif stripped.startswith("### "):
                h3_count += 1
                headings.append(("h3", stripped[4:].strip()))
        
        # 统计表格
        table_count = 0
        in_table = False
        for line in lines:
            if "|" in line and line.strip().startswith("|"):
                # 检测表格分隔行
                if re.match(r"^\|[-\s|]+\|$", line):
                    in_table = True
                elif in_table and line.strip().endswith("|"):
                    pass
            else:
                if in_table:
                    table_count += 1
                    in_table = False
        
        # 统计关键数据
        total_chars = len(content)
        
        # 统计数字指标（带单位的数字）
        metrics = re.findall(
            r'(\d+[.,]?\d*\s*(?:[%亿元万元千万千倍↑↓%]|同比增长|增长|提升|下降|缩短|突破|超过))',
            content
        )
        metric_count = len(metrics)
        
        # 统计列表项
        bullet_count = len([l for l in lines if l.strip().startswith(("- ", "* ", "+ "))]) + \
                       len([l for l in lines if re.match(r"^\d+[.、)]", l.strip())])
        
        # 估算段落数（空行分隔）
        para_count = 0
        prev_empty = True
        for line in lines:
            if line.strip():
                if prev_empty:
                    para_count += 1
                prev_empty = False
            else:
                prev_empty = True
        
        result = {
            "total_chars": total_chars,
            "headings": {
                "h1": h1_count,
                "h2": h2_count,
                "h3": h3_count,
                "total": h1_count + h2_count + h3_count,
                "items": headings,
            },
            "tables": table_count,
            "metrics": {
                "count": metric_count,
                "items": metrics[:20],
            },
            "bullets": bullet_count,
            "paragraphs": para_count,
            "lines": len(lines),
        }
        
        return result

    @staticmethod
    def recommend_page_count(content: str, min_pages: int = 5, max_pages: int = 30) -> int:
        """基于内容分析推荐页数"""
        info = ContentAnalyzer.analyze(content)
        
        h2_count = info["headings"]["h2"]
        h3_count = info["headings"]["h3"]
        
        if h2_count == 0 and h3_count == 0:
            paragraphs = info["paragraphs"]
            chars = info["total_chars"]
            estimated_by_chars = max(3, chars // 300)
            estimated_by_para = max(3, paragraphs // 3)
            recommended = (estimated_by_chars + estimated_by_para) // 2
        else:
            # 核心内容页：主要章节(h2)每章约 1 页
            # 子章节作为合并到主章节中的内容，不额外增加页数
            major_pages = max(1, round(h2_count * 1.0))
            cover_summary = 2
            # 每 3-4 个 content 页插入一个章节分隔
            chapter_dividers = max(0, (major_pages - 1) // 4) if major_pages > 3 else 0
            
            recommended = cover_summary + major_pages + chapter_dividers
            
            # 数据丰富加成
            if info["tables"] > 0:
                recommended += 1
            if info["metrics"]["count"] > 15:
                recommended += 1
        
        final_count = max(min_pages, min(max_pages, int(recommended)))
        logger.info(
            "内容分析: %d 字符, %d h2, %d h3, "
            "%d 指标, %d 表格 → 推荐 %d 页",
            info["total_chars"], h2_count, h3_count,
            info["metrics"]["count"], info["tables"], final_count,
        )
        return final_count
