"""极简风格 —— 黑白灰学术"""
from pptx.util import Inches
from .base import BaseTemplate
from models.enums import AnimationType, TransitionType

class MinimalTemplate(BaseTemplate):
    id = "minimal"
    name = "极简风格"
    description = "黑白灰极简，适合学术报告与设计展示"
    primary = (35, 35, 35)
    secondary = (100, 100, 110)
    accent = (180, 180, 190)
    bg = (252, 252, 252)
    dark_bg = (30, 30, 35)
    text = (40, 40, 45)
    text_light = (155, 155, 160)
    text_on_dark = (235, 235, 240)
    light_gray = (248, 248, 248)
    border = (225, 225, 228)
    default_animation = AnimationType.ZOOM
    default_transition = TransitionType.NONE
