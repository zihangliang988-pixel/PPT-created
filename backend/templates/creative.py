"""创意设计 —— 暖色卡片风"""
from pptx.util import Inches
from .base import BaseTemplate
from models.enums import AnimationType, TransitionType

class CreativeTemplate(BaseTemplate):
    id = "creative"
    name = "创意设计"
    description = "暖色调卡片风，适合创意提案与团队活动"
    primary = (255, 100, 100)
    secondary = (255, 160, 80)
    accent = (255, 200, 100)
    bg = (255, 255, 255)
    dark_bg = (50, 40, 40)
    text = (55, 55, 70)
    text_light = (160, 150, 160)
    text_on_dark = (240, 235, 235)
    light_gray = (255, 248, 248)
    border = (235, 225, 225)
    default_animation = AnimationType.BOUNCE
    default_transition = TransitionType.COVER
