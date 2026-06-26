"""现代简约模板 — 干净留白 + 蓝色主调 + 卡片布局"""

from pptx.util import Inches
from .base import BaseTemplate
from models.enums import AnimationType, TransitionType


class ModernTemplate(BaseTemplate):
    id = "modern"
    name = "现代简约"
    description = "简洁明快，留白大方，适合各类通用场景"
    thumbnail = "https://picsum.photos/160/120?random=2"

    theme_color = (64, 158, 255)
    background_color = (255, 255, 255)
    font_color = (48, 49, 51)
    accent_color = (103, 194, 58)
    section_bg = (240, 246, 255)
    default_animation = AnimationType.FLY_IN
    default_transition = TransitionType.PUSH

    def layout_content(self, prs, title, points):
        slide = self.create_slide(prs)
        self.add_bg(slide)
        # 顶部蓝色条
        self.add_rect(slide, Inches(0), Inches(0), Inches(13.333), Inches(0.1), self.theme_color)
        self.add_textbox(slide, Inches(0.6), Inches(0.4), Inches(12), Inches(0.6),
                         title, font_size=22, bold=True, color=self.theme_color)
        self.add_rect(slide, Inches(0.6), Inches(1.05), Inches(12), Inches(0.015),
                      (200, 220, 240))
        self._layout_points(slide, Inches(0.6), Inches(1.4), Inches(12), Inches(5.5),
                            points, font_size=15, spacing=10)
        return slide

    def layout_chapter(self, prs, title, points):
        slide = self.create_slide(prs)
        self.add_bg(slide, (235, 243, 255))
        self.add_rect(slide, Inches(0), Inches(3.4), Inches(13.333), Inches(0.06), self.theme_color)
        self.add_textbox(slide, Inches(1.5), Inches(1.8), Inches(10.3), Inches(1.5),
                         title, font_size=36, bold=True, color=self.theme_color, alignment="center")
        if points:
            self.add_textbox(slide, Inches(2), Inches(3.8), Inches(9.3), Inches(1),
                             points[0], font_size=14, color=(100, 110, 120), alignment="center")
        return slide
