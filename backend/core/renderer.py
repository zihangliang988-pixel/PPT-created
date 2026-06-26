"""PPT 渲染器 —— 将规划好的内容渲染为 .pptx 文件"""

from __future__ import annotations

import logging
from typing import Optional

from pptx import Presentation

from models.schemas import PageOutline
from models.enums import TransitionType
from core.designer import LayoutDesigner

logger = logging.getLogger(__name__)

TRANSITION_MAP = {
    "fade": TransitionType.FADE,
    "push": TransitionType.PUSH,
    "wipe": TransitionType.WIPE,
    "zoom": TransitionType.ZOOM,
    "cover": TransitionType.COVER,
}


class PPTRenderer:
    """将规划好的内容渲染为 .pptx 文件"""

    def __init__(
        self,
        template_id: str = "modern",
        custom_style_desc: Optional[str] = None,
        animation_enabled: bool = True,
        transition_style: Optional[str] = None,
    ):
        self.designer = LayoutDesigner(template_id, custom_style_desc)
        self.animation_enabled = animation_enabled
        self.transition_override = transition_style

    def render(
        self,
        title: str,
        pages: list[PageOutline],
        output_path: str,
        subtitle: str = "",
    ) -> str:
        """渲染 PPT，返回输出路径"""
        prs = Presentation()
        template = self.designer.template
        template.apply_theme(prs)

        for page in pages:
            # 根据页面类型选择布局
            if page.type == "cover":
                template.layout_cover(prs, page.title or title, subtitle)
            elif page.type == "summary":
                template.layout_summary(prs, page.title, page.points)
            elif page.type == "chapter":
                template.layout_chapter(prs, page.title, page.points)
            elif page.type == "cards":
                template.layout_cards(prs, page.title, page.points)
            elif page.chart:
                # 如果页面包含图表数据，使用图表布局
                template.layout_chart(prs, page.title, page.points, page.chart)
            else:
                template.layout_content(prs, page.title, page.points)

            # 设置切换效果
            if self.animation_enabled:
                slide = prs.slides[-1]
                transition = self.transition_override
                final_trans = (
                    TRANSITION_MAP.get(transition, template.default_transition)
                    if transition
                    else template.default_transition
                )
                template.set_transition(slide, final_trans)

        prs.save(output_path)
        logger.info("PPT 已生成: %s (模板: %s)", output_path, template.id)
        return output_path
