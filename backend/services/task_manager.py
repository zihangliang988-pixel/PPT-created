"""任务管理器 — 状态追踪/进度管理"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from models.enums import TaskStatus
from models.schemas import TaskInfo, PageOutline, WSMessage
from utils.helpers import generate_task_id

logger = logging.getLogger(__name__)


class TaskManager:
    """管理所有生成任务的状态和进度"""

    def __init__(self):
        self._tasks: dict[str, TaskInfo] = {}
        self._meta: dict[str, dict] = {}          # 任务元数据（模板、动画等）
        self._ws_queues: dict[str, list[asyncio.Queue]] = {}
        self._cancel_flags: dict[str, asyncio.Event] = {}
        self._ws_connected: dict[str, asyncio.Event] = {}  # 标记是否有WS连接

    def create_task(self) -> str:
        """创建新任务，返回 task_id"""
        task_id = generate_task_id()
        self._tasks[task_id] = TaskInfo(
            task_id=task_id, status=TaskStatus.PENDING, progress=0, step_text="准备中...",
        )
        self._ws_queues[task_id] = []
        self._cancel_flags[task_id] = asyncio.Event()
        self._ws_connected[task_id] = asyncio.Event()  # 初始化连接事件
        logger.info(f"任务已创建: {task_id}")
        return task_id

    async def wait_for_ws(self, task_id: str, timeout: int = 60):
        """等待 WebSocket 连接建立"""
        event = self._ws_connected.get(task_id)
        if not event:
            return
        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
            logger.info(f"任务 {task_id[:8]}: WebSocket 连接已建立")
        except asyncio.TimeoutError:
            logger.warning(f"任务 {task_id[:8]}: 等待 WS 连接超时，继续执行")

    def get_task(self, task_id: str) -> Optional[TaskInfo]:
        return self._tasks.get(task_id)

    def update_progress(
        self, task_id: str, status: TaskStatus, progress: int, step_text: str = "", detail: str = ""
    ):
        """更新任务进度"""
        task = self._tasks.get(task_id)
        if not task:
            return
        task.status = status
        task.progress = progress
        task.step_text = step_text
        if detail:
            task.error = detail if status == TaskStatus.FAILED else None

    def set_pages(self, task_id: str, pages: list[PageOutline]):
        """设置任务的大纲页面"""
        task = self._tasks.get(task_id)
        if task:
            task.pages = pages

    def set_result(self, task_id: str, file_size: Optional[int] = None):
        """设置任务完成结果"""
        task = self._tasks.get(task_id)
        if task:
            task.file_size = file_size

    def is_cancelled(self, task_id: str) -> bool:
        """检查任务是否被取消"""
        flag = self._cancel_flags.get(task_id)
        return flag is not None and flag.is_set()

    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        flag = self._cancel_flags.get(task_id)
        if flag:
            flag.set()
        task = self._tasks.get(task_id)
        if task and task.status not in (TaskStatus.COMPLETED, TaskStatus.FAILED):
            task.status = TaskStatus.CANCELLED
            return True
        return False

    def set_meta(self, task_id: str, **kwargs):
        """存储任务元数据（模板 ID、动画开关等）"""
        self._meta.setdefault(task_id, {}).update(kwargs)

    def get_meta(self, task_id: str) -> dict:
        """获取任务元数据"""
        return self._meta.get(task_id, {})

    # ── WebSocket 订阅 ──

    def subscribe(self, task_id: str) -> asyncio.Queue:
        """客户端订阅任务进度推送"""
        queue: asyncio.Queue = asyncio.Queue()
        if task_id in self._ws_queues:
            self._ws_queues[task_id].append(queue)
            # 标记 WebSocket 已连接
            event = self._ws_connected.get(task_id)
            if event and not event.is_set():
                event.set()
                logger.info(f"任务 {task_id[:8]}: 客户端已订阅")
        return queue

    def unsubscribe(self, task_id: str, queue: asyncio.Queue):
        """取消订阅"""
        queues = self._ws_queues.get(task_id)
        if queues and queue in queues:
            queues.remove(queue)

    async def broadcast(self, task_id: str, message: WSMessage):
        """广播进度到所有订阅者"""
        queues = self._ws_queues.get(task_id, [])
        dead = []
        for q in queues:
            try:
                await q.put(message)
            except Exception:
                dead.append(q)
        for q in dead:
            queues.remove(q)

    # ── 清理 ──

    def remove_task(self, task_id: str):
        """移除已完成的任务"""
        self._tasks.pop(task_id, None)
        self._ws_queues.pop(task_id, None)
        self._cancel_flags.pop(task_id, None)

    def cleanup_old_tasks(self, max_age_hours: int = 2):
        """清理超时任务"""
        now = datetime.now(timezone.utc).timestamp()
        # 暂不实现，保持简单


# 全局单例
task_manager = TaskManager()
