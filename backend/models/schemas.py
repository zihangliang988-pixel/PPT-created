"""Pydantic 数据模型"""

from __future__ import annotations

from typing import Optional, List
from pydantic import BaseModel, Field

from .enums import DetailLevel, PageType, TaskStatus, ChartType


# ── 请求模型 ──


class GenerateRequest(BaseModel):
    """生成 PPT 请求"""

    text_content: Optional[str] = None
    title: Optional[str] = None
    page_count: int = Field(default=10, ge=3, le=50)
    detail: DetailLevel = DetailLevel.MODERATE
    template_id: str = "modern"
    custom_style_desc: Optional[str] = None
    animation_enabled: bool = True
    transition_style: Optional[str] = None


class OutlineEditRequest(BaseModel):
    """大纲编辑后提交"""

    task_id: str
    pages: list[PageOutline]


class RestyleRequest(BaseModel):
    """一键换风格"""

    task_id: str
    template_id: str
    custom_style_desc: Optional[str] = None


class ModifyRequest(BaseModel):
    """增量修改 — 基于已有 PPT 继续调整"""

    task_id: str
    new_text: str
    modify_scope: Optional[str] = None  # 如 "仅修改第3页" / "新增一页关于XX" / "整体精简"


# ── 图表数据模型 ──


class ChartData(BaseModel):
    """图表数据结构"""
    
    type: ChartType = ChartType.COLUMN
    title: Optional[str] = None
    categories: List[str] = []  # X轴标签/分类
    series: List[dict] = []     # 数据系列，每个系列包含 name 和 values
    # series 格式: [{"name": "系列1", "values": [10, 20, 30]}, ...]


# ── 响应模型 ──


class PageOutline(BaseModel):
    """页面大纲"""

    id: str
    type: PageType = PageType.CONTENT
    title: str
    points: list[str] = []
    chart: Optional[ChartData] = None  # 图表数据（可选）


class GenerateResponse(BaseModel):
    """生成响应"""

    task_id: str
    status: TaskStatus
    message: str = ""


class TaskInfo(BaseModel):
    """任务信息"""

    task_id: str
    status: TaskStatus
    progress: int = 0
    step_text: str = ""
    pages: list[PageOutline] = []
    file_size: Optional[int] = None
    error: Optional[str] = None


class TemplateInfo(BaseModel):
    """模板信息"""

    id: str
    name: str
    description: str = ""
    thumbnail: str = ""


# ── WebSocket 消息 ──


class PreviewPage(BaseModel):
    """预览页信息"""

    index: int
    type: str = "content"
    title: str
    subtitle: str = ""
    points: list[str] = []


class PageRecommendation(BaseModel):
    """页面推荐信息"""

    title: Optional[str] = None
    page_type: str = "content"
    suggested_points: list[str] = []
    recommended_pages: int = 10
    analysis: Optional[dict] = None
    reason: str = ""


class WSMessage(BaseModel):
    """WebSocket 进度消息"""

    event: str = "progress"
    stage: str = ""
    stage_name: str = ""
    percentage: int = 0
    detail: str = ""
    pages: Optional[list[PageOutline]] = None
