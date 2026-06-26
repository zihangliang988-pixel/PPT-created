"""内容规划器 —— 将内容拆解为 PPT 页面结构"""

from __future__ import annotations

import json
import logging
from typing import Optional

from config import settings
from models.enums import DetailLevel
from models.schemas import PageOutline
from services.llm_client import LLMClient, LLMError, LLMTimeoutError
from utils.helpers import parse_json_output

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════
# Prompts
# ══════════════════════════════════════════

PLANNER_SYSTEM = """你是一个资深的 PPT 内容策划师。根据用户输入，生成 PPT 内容大纲。

## 工作模式（重要）：请根据输入内容的类型自动切换

### 模式 A：输入包含具体数据/文档内容
- 用户提供了文档、数据、公司信息等具体内容
- **严格基于素材**：只提炼、润色、结构化，不要编造事实和数据
- 可以润色表述、提炼核心、优化逻辑顺序，但不能添加不存在的数据
- 内容优先级（从高到低）：产品功能 > 客户案例 > 财务数据 > 战略规划 > 公司背景

### 模式 B：输入是主题/请求（如 "吉他基础教学" "Python入门"）
- 用户只给了话题，没有提供具体内容
- **自主创作**：根据你的知识生成 PPT 内容
- 内容要权威、准确、有条理，按教学逻辑组织章节
- 每页要有信息量，适合演讲展示

## 页面类型：
- "cover"    → 封面（第 1 页）
- "content"  → 标准内容页：3-5 个要点
- "cards"    → 卡片页：并列展示 3-6 个同类要点（功能/优势/案例）
- "chapter"  → 章节分隔页：标识演示节奏
- "summary"  → 总结页（最后 1 页）：3-5 个结论

输出纯 JSON 数组。"""

SUMMARY_SYSTEM = """你是一个文档摘要专家。请将以下文档内容提炼为结构化的要点摘要。

要求：
- 提取核心主题和关键论点
- 保留重要数据、名称、术语
- 按原始文档的逻辑顺序组织
- 输出纯文本，使用 Markdown 标题（##）分层
- 总长度控制在 3000 字以内"""


# ══════════════════════════════════════════
# ContentPlanner
# ══════════════════════════════════════════

class ContentPlanner:
    """内容规划器"""

    def __init__(self, llm: LLMClient):
        self.llm = llm

    async def plan(
        self,
        content: str,
        page_count: int,
        detail: DetailLevel,
        title: Optional[str] = None,
        user_prompt: Optional[str] = None,
    ) -> list[PageOutline]:
        """将内容拆解为 PPT 页面结构"""
        detail_hint = {
            DetailLevel.SIMPLE: "内容精简，每页 3-4 个要点",
            DetailLevel.MODERATE: "内容适中，每页 4-5 个要点",
            DetailLevel.DETAILED: "内容详细，每页 5-6 个要点，可适当展开",
        }.get(detail, "内容适中")

        # 长文档先做摘要
        working_content = content
        if len(content) > settings.content_summary_threshold:
            logger.info("内容较长 (%d 字符)，先做摘要", len(content))
            try:
                summary = await self._summarize(content[: settings.content_max_chars])
                if summary:
                    working_content = summary
                    logger.info("摘要完成 (%d 字符)", len(summary))
            except Exception as e:
                logger.warning("摘要失败，使用截断内容: %s", e)
                working_content = content[: settings.content_max_chars]
        else:
            working_content = content[: settings.content_max_chars]

        # 构建 prompt
        user_text = f"""文档内容：
{working_content}

生成要求：
- 页数：{page_count} 页
- 内容详细程度：{detail_hint}
"""
        if title:
            user_text += f"- PPT 标题：{title}\n"
        if user_prompt:
            user_text += f"- 补充说明：{user_prompt}\n"

        # 调用 LLM
        try:
            raw = await self.llm.chat(
                messages=[
                    {"role": "system", "content": PLANNER_SYSTEM},
                    {"role": "user", "content": user_text},
                ],
                temperature=0.3,
                max_tokens=settings.llm_max_tokens_plan,
            )
        except LLMTimeoutError:
            raise  # 直接透传超时异常，让上层给用户友好提示
        except LLMError as e:
            raise ValueError(f"内容规划失败: {e}")

        if not raw.strip():
            raise ValueError("LLM 返回内容为空，请重试")

        # 解析 JSON
        data = parse_json_output(raw)

        # 兼容各种嵌套格式
        if isinstance(data, dict):
            data = data.get("pages") or data.get("slides") or data.get("result") or []
        if isinstance(data, dict) and isinstance(data.get("pages"), list):
            data = data["pages"]

        if not isinstance(data, list) or len(data) == 0:
            raise ValueError(
                "LLM 返回的内容无法解析为 PPT 大纲。"
                "请尝试减少输入内容或调整页数后重试。"
            )

        # 构建 PageOutline 列表
        outlines = []
        for i, item in enumerate(data):
            if not isinstance(item, dict):
                continue
            page_type = str(item.get("type", "content")).lower()
            if page_type not in ("cover", "content", "chapter", "summary", "cards"):
                page_type = "content"
            
            # 解析图表数据
            chart_data = None
            chart_info = item.get("chart")
            if isinstance(chart_info, dict):
                chart_type = chart_info.get("type", "column")
                chart_categories = chart_info.get("categories", [])
                chart_series = chart_info.get("series", [])
                # 验证图表数据有效性
                if chart_categories and chart_series and isinstance(chart_series, list):
                    valid_series = []
                    for s in chart_series:
                        if isinstance(s, dict) and "name" in s and "values" in s:
                            values = s["values"]
                            if isinstance(values, list) and len(values) == len(chart_categories):
                                valid_series.append(s)
                    if valid_series:
                        chart_data = {
                            "type": chart_type,
                            "title": chart_info.get("title"),
                            "categories": chart_categories,
                            "series": valid_series,
                        }
            
            outlines.append(PageOutline(
                id=f"page_{i}",
                type=page_type,
                title=str(item.get("title", f"第 {i + 1} 页")),
                points=[
                    str(p)[:100] for p in item.get("points", item.get("bullets", []))
                    if p and str(p).strip()
                ],
                chart=chart_data,
            ))

        if not outlines:
            raise ValueError("LLM 返回的大纲为空")

        logger.info("规划完成: %d 页大纲", len(outlines))
        return outlines

    # ── 长文档摘要 ──

    async def _summarize(self, content: str) -> str:
        """对长文档先做摘要，降低后续规划 prompt 长度"""
        raw = await self.llm.chat(
            messages=[
                {"role": "system", "content": SUMMARY_SYSTEM},
                {"role": "user", "content": content},
            ],
            temperature=0.2,
            max_tokens=settings.llm_max_tokens_summary,
        )
        return raw.strip()

    # ── 增量修改 ──

    async def plan_for_modify(
        self,
        existing_pages: list[PageOutline],
        new_text: str,
        modify_scope: Optional[str] = None,
    ) -> list[PageOutline]:
        """在现有大纲基础上根据新输入调整"""
        existing_json = json.dumps(
            [{"id": p.id, "type": p.type, "title": p.title, "points": p.points, "chart": p.chart}
             for p in existing_pages],
            ensure_ascii=False, indent=2,
        )
        scope_hint = modify_scope or "根据新内容合理调整现有页面"

        try:
            raw = await self.llm.chat(
                messages=[
                    {"role": "system", "content": PLANNER_SYSTEM},
                    {"role": "user", "content": (
                        f"已有 PPT 大纲：\n{existing_json}\n\n"
                        f"用户新输入：\n{new_text}\n\n"
                        f"修改要求：{scope_hint}\n\n"
                        f"输出调整后的完整 JSON 数组。可修改、新增或删除页面。"
                    )},
                ],
                temperature=0.3,
                max_tokens=settings.llm_max_tokens_plan,
            )
            data = parse_json_output(raw)
            if isinstance(data, dict):
                data = data.get("pages") or data.get("slides") or []
            if isinstance(data, list):
                result = []
                for i, item in enumerate(data):
                    # 解析图表数据
                    chart_data = None
                    chart_info = item.get("chart")
                    if isinstance(chart_info, dict):
                        chart_type = chart_info.get("type", "column")
                        chart_categories = chart_info.get("categories", [])
                        chart_series = chart_info.get("series", [])
                        if chart_categories and chart_series and isinstance(chart_series, list):
                            valid_series = []
                            for s in chart_series:
                                if isinstance(s, dict) and "name" in s and "values" in s:
                                    values = s["values"]
                                    if isinstance(values, list) and len(values) == len(chart_categories):
                                        valid_series.append(s)
                            if valid_series:
                                chart_data = {
                                    "type": chart_type,
                                    "title": chart_info.get("title"),
                                    "categories": chart_categories,
                                    "series": valid_series,
                                }
                    result.append(PageOutline(
                        id=item.get("id", f"page_{i}"),
                        type=item.get("type", "content"),
                        title=item.get("title", f"第 {i + 1} 页"),
                        points=item.get("points", []),
                        chart=chart_data,
                    ))
                return result
        except Exception as e:
            logger.error("增量修改失败: %s", e)

        return existing_pages  # 修改失败时保留原文
