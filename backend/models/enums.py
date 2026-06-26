"""枚举定义"""

from enum import Enum


class TaskStatus(str, Enum):
    PENDING = "pending"
    PLANNING = "planning"
    PLANNED = "planned"  # 大纲已生成，等待用户确认
    POLISHING = "polishing"
    DESIGNING = "designing"
    RENDERING = "rendering"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PageType(str, Enum):
    COVER = "cover"
    CONTENT = "content"
    CHAPTER = "chapter"
    SUMMARY = "summary"
    CARDS = "cards"        # 卡片式布局


class DetailLevel(str, Enum):
    SIMPLE = "simple"
    MODERATE = "moderate"
    DETAILED = "detailed"


class AnimationType(str, Enum):
    FADE = "fade"
    FLY_IN = "fly_in"
    ZOOM = "zoom"
    BOUNCE = "bounce"
    WIPE = "wipe"
    SPLIT = "split"
    SHAPE = "shape"
    WHEEL = "wheel"


class TransitionType(str, Enum):
    NONE = "none"
    FADE = "fade"
    PUSH = "push"
    WIPE = "wipe"
    COVER = "cover"
    UNCOVER = "uncover"
    ZOOM = "zoom"
    MORPH = "morph"


class ChartType(str, Enum):
    """图表类型枚举"""
    COLUMN = "column"          # 柱状图
    BAR = "bar"                # 条形图
    LINE = "line"              # 折线图
    PIE = "pie"                # 饼图
    AREA = "area"              # 面积图
    SCATTER = "scatter"        # 散点图
    DOUGHNUT = "doughnut"      # 环形图
