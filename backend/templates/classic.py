"""经典商务 —— 深蓝沉稳"""
from pptx.util import Inches
from .base import BaseTemplate
from models.enums import AnimationType, TransitionType

class ClassicTemplate(BaseTemplate):
    id = "classic"
    name = "经典商务"
    description = "深蓝沉稳，适合正式汇报与提案"
    primary = (25, 55, 109)
    secondary = (60, 100, 170)
    accent = (190, 160, 100)
    bg = (255, 255, 255)
    dark_bg = (20, 30, 50)
    text = (40, 42, 48)
    text_light = (130, 135, 145)
    text_on_dark = (230, 235, 245)
    light_gray = (242, 244, 248)
    border = (215, 218, 225)
    default_animation = AnimationType.FADE
    default_transition = TransitionType.FADE
