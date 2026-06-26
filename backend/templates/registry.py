"""模板注册表 — 所有模板的注册与管理"""

from __future__ import annotations

from typing import Optional

from models.schemas import TemplateInfo

# 延迟导入避免循环依赖
_template_classes: dict[str, type] = {}
_initialized = False


def _lazy_init():
    """延迟加载所有模板类"""
    global _initialized, _template_classes
    if _initialized:
        return

    from templates.classic import ClassicTemplate
    from templates.modern import ModernTemplate
    from templates.tech import TechTemplate
    from templates.creative import CreativeTemplate
    from templates.minimal import MinimalTemplate
    from templates.elegant import ElegantTemplate
    from templates.colorful import ColorfulTemplate
    from templates.dark import DarkTemplate

    _template_classes = {
        "classic": ClassicTemplate,
        "modern": ModernTemplate,
        "tech": TechTemplate,
        "creative": CreativeTemplate,
        "minimal": MinimalTemplate,
        "elegant": ElegantTemplate,
        "colorful": ColorfulTemplate,
        "dark": DarkTemplate,
    }
    _initialized = True


def get_template(template_id: str):
    """获取模板实例"""
    _lazy_init()
    cls = _template_classes.get(template_id)
    if not cls:
        # 默认使用 modern
        cls = _template_classes.get("modern")
    return cls() if cls else None


def get_template_list() -> list[TemplateInfo]:
    """获取模板列表"""
    _lazy_init()
    templates = []
    for tid, cls in _template_classes.items():
        inst = cls()
        templates.append(
            TemplateInfo(
                id=tid,
                name=inst.name,
                description=inst.description,
                thumbnail=inst.thumbnail,
            )
        )
    return templates


def get_template_names() -> list[str]:
    """获取所有模板 ID 列表"""
    _lazy_init()
    return list(_template_classes.keys())
