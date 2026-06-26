"""多彩活力 —— 明亮色彩碰撞"""
from pptx.util import Inches
from .base import BaseTemplate
from models.enums import AnimationType, TransitionType

class ColorfulTemplate(BaseTemplate):
    id = "colorful"
    name = "多彩活力"
    description = "明快色彩碰撞，适合团队建设与活动策划"
    primary = (255, 100, 100)
    secondary = (70, 200, 230)
    accent = (255, 215, 60)
    bg = (255, 255, 255)
    dark_bg = (40, 45, 55)
    text = (55, 55, 75)
    text_light = (160, 155, 170)
    text_on_dark = (235, 238, 245)
    light_gray = (255, 245, 242)
    border = (235, 230, 235)
    default_animation = AnimationType.BOUNCE
    default_transition = TransitionType.PUSH
