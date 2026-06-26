"""文案润色器 —— 让文案更精炼、更具 PPT 风格"""

from __future__ import annotations

import json
import logging

from config import settings
from models.schemas import PageOutline
from services.llm_client import LLMClient
from utils.helpers import parse_json_output

logger = logging.getLogger(__name__)

POLISHER_SYSTEM = """你是 PPT 文案润色专家。优化每页内容的文案。

规则：
1. 每项要点 5-25 个字
2. 去除冗余修饰词，动词开头（推动、提升、实现、建立…）
3. 数据和具体数字保留
4. 保持专业简洁
5. 输出纯 JSON，保留原始结构（id/type/title/points）"""


class ContentPolisher:
    """文案润色器"""

    def __init__(self, llm: LLMClient):
        self.llm = llm

    async def polish(self, pages: list[PageOutline]) -> list[PageOutline]:
        """对页面文案进行润色。失败时返回原文。"""
        if not pages:
            return pages

        # 构造输入
        items = [
            {"id": p.id, "type": p.type, "title": p.title, "points": p.points}
            for p in pages
        ]
        prompt = (
            f"请润色以下 PPT 页面文案：\n\n"
            f"{json.dumps(items, ensure_ascii=False, indent=2)}\n\n"
            f"只输出润色后的 JSON 数组。"
        )

        try:
            raw = await self.llm.chat(
                messages=[
                    {"role": "system", "content": POLISHER_SYSTEM},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=settings.llm_max_tokens_polish,
            )
        except Exception as e:
            logger.warning("文案润色 LLM 调用失败，使用原文: %s", e)
            return pages

        if not raw.strip():
            logger.warning("LLM 返回空内容，使用原文")
            return pages

        try:
            data = parse_json_output(raw)
        except ValueError as e:
            logger.warning("润色结果 JSON 解析失败，使用原文: %s", e)
            return pages

        if not isinstance(data, list) or len(data) != len(pages):
            logger.warning("润色结果页数不匹配 (%d vs %d)，使用原文", len(data) if isinstance(data, list) else 0, len(pages))
            return pages

        # 合并结果
        polished = []
        for item, original in zip(data, pages):
            if not isinstance(item, dict):
                polished.append(original)
                continue
            pts = [
                str(p)[:80] for p in item.get("points", original.points)
                if p and str(p).strip()
            ]
            if not pts:
                pts = [str(p)[:80] for p in original.points if p and str(p).strip()]
            polished.append(PageOutline(
                id=item.get("id", original.id),
                type=item.get("type", original.type),
                title=item.get("title", original.title),
                points=pts,
            ))
        return polished
