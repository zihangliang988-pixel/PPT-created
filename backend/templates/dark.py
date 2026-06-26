"""深色格调 —— 暗色高级感"""
from pptx.util import Inches
from .base import BaseTemplate
from models.enums import AnimationType, TransitionType

class DarkTemplate(BaseTemplate):
    id = "dark"
    name = "深色格调"
    description = "暗色背景配金色点缀，适合高端发布会"
    primary = (0, 140, 240)
    secondary = (50, 170, 255)
    accent = (255, 195, 50)
    bg = (24, 26, 34)
    dark_bg = (18, 20, 28)
    text = (220, 222, 230)
    text_light = (130, 135, 150)
    text_on_dark = (215, 220, 230)
    light_gray = (34, 36, 46)
    border = (55, 58, 70)
    default_animation = AnimationType.ZOOM
    default_transition = TransitionType.COVER
