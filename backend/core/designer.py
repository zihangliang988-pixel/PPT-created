"""布局设计师 — 根据模板和风格描述分配布局"""

from __future__ import annotations

from typing import Optional

from templates.registry import get_template
from models.enums import TransitionType


class LayoutDesigner:
    """布局设计师 — 模板匹配 + 样式分配"""

    def __init__(self, template_id: str, custom_style_desc: Optional[str] = None):
        self.template = get_template(template_id)
        self.custom_desc = custom_style_desc or ""

    def get_layout_method(self, page_type: str):
        """获取页面类型的布局方法"""
        return self.template.get_layout_method(page_type)

    def get_transition(self) -> TransitionType:
        """获取切换效果"""
        return self.template.default_transition

    def get_animation(self) -> str:
        """获取动画效果"""
        return self.template.default_animation.value
