"""优雅高端 —— 金色米白"""
from pptx.util import Inches
from .base import BaseTemplate
from models.enums import AnimationType, TransitionType

class ElegantTemplate(BaseTemplate):
    id = "elegant"
    name = "优雅高端"
    description = "金色点缀米白基底，高端品牌推介"
    primary = (175, 145, 75)
    secondary = (200, 170, 100)
    accent = (140, 110, 60)
    bg = (250, 248, 242)
    dark_bg = (45, 42, 38)
    text = (55, 50, 45)
    text_light = (175, 165, 150)
    text_on_dark = (235, 230, 220)
    light_gray = (243, 240, 233)
    border = (225, 218, 205)
    default_animation = AnimationType.FADE
    default_transition = TransitionType.FADE
