"""科技感 —— 深色赛博"""
from pptx.util import Inches
from .base import BaseTemplate
from models.enums import AnimationType, TransitionType

class TechTemplate(BaseTemplate):
    id = "tech"
    name = "科技感"
    description = "深色赛博风格，适合技术分享与产品发布"
    primary = (0, 160, 255)
    secondary = (0, 210, 255)
    accent = (120, 255, 200)
    bg = (10, 18, 40)
    dark_bg = (8, 14, 32)
    text = (220, 230, 245)
    text_light = (110, 140, 175)
    text_on_dark = (210, 225, 245)
    light_gray = (16, 28, 55)
    border = (40, 55, 85)
    default_animation = AnimationType.WIPE
    default_transition = TransitionType.WIPE
