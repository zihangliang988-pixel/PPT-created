"""
PPT 智造 — 后端 API 服务
FastAPI 应用入口，端口 3000
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from config import settings
from models.enums import TaskStatus
from models.schemas import (
    GenerateRequest, GenerateResponse, TaskInfo,
    TemplateInfo, PageOutline, OutlineEditRequest, RestyleRequest,
    ModifyRequest, WSMessage, PageRecommendation,
)
from services.llm_client import LLMClient, LLMTimeoutError
from services.file_service import FileService
from services.task_manager import task_manager
from core.parser import DocumentParser
from core.planner import ContentPlanner
from core.polisher import ContentPolisher
from core.renderer import PPTRenderer
from templates.registry import get_template_list

logger = logging.getLogger(__name__)

# ── 全局服务实例 ──
llm = LLMClient()
file_service = FileService()
planner = ContentPlanner(llm)
polisher = ContentPolisher(llm)


# ══════════════════════════════════════════
# FastAPI 应用
# ══════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("PPT 智造后端启动")
    os.makedirs(settings.upload_dir, exist_ok=True)
    os.makedirs(settings.output_dir, exist_ok=True)
    yield
    logger.info("PPT 智造后端关闭")


app = FastAPI(title="PPT 智造 API", version="2.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])


# ══════════════════════════════════════════
# 辅助函数
# ══════════════════════════════════════════

def _validate_file(file: UploadFile) -> Optional[str]:
    ext = Path(file.filename or "").suffix.lower()
    if ext not in settings.allowed_extensions:
        return f"不支持的文件格式 '{ext}'"
    return None


def _make_error_msg(exc: Exception) -> str:
    if isinstance(exc, LLMTimeoutError):
        return (
            "LLM 请求超时。ClawClaw 推理模型处理大量内容时可能较慢，"
            "建议：1) 减少输入内容  2) 降低页数  3) 分多次生成"
        )
    msg = str(exc)
    return msg[:300] if msg else "未知错误"


async def _send_error(task_id: str, stage: str, exc: Exception):
    detail = _make_error_msg(exc)
    logger.error("%s 失败: %s", stage, detail)
    task_manager.update_progress(task_id, TaskStatus.FAILED, 0, stage, detail=detail)
    await task_manager.broadcast(
        task_id,
        WSMessage(event="error", stage="failed", stage_name=f"{stage}失败",
                  percentage=0, detail=detail),
    )


async def _with_heartbeat(task_id: str, stage: str, coro, interval: int = 15):
    """在 LLM 调用期间持续发送心跳，防止 WebSocket 断连 + 让用户知道在跑。

    用法: result = await _with_heartbeat(task_id, "规划大纲", llm.chat(...))
    """
    cancelled = False
    start = time.time()

    async def beat():
        while not cancelled:
            await asyncio.sleep(interval)
            if cancelled:
                break
            elapsed = int(time.time() - start)
            logger.info("任务 %s: %s 进行中... %d 秒", task_id[:8], stage, elapsed)
            await task_manager.broadcast(
                task_id,
                WSMessage(stage="planning",
                          stage_name=f"AI {stage}中...（已等待 {elapsed} 秒）",
                          percentage=20),
            )

    heartbeat_task = asyncio.create_task(beat())
    try:
        result = await coro
        elapsed = int(time.time() - start)
        logger.info("任务 %s: %s 完成，耗时 %d 秒", task_id[:8], stage, elapsed)
        return result
    finally:
        cancelled = True
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass


# ══════════════════════════════════════════
# REST API
# ══════════════════════════════════════════

@app.get("/api/templates", response_model=list[TemplateInfo])
async def list_templates():
    return get_template_list()


@app.post("/api/recommend-pages", response_model=PageRecommendation)
async def recommend_pages(content: str = Form(...)):
    """基于上传内容智能推荐页数"""
    from core.content_analyzer import ContentAnalyzer
    info = ContentAnalyzer.analyze(content)
    pages = ContentAnalyzer.recommend_page_count(content)
    reasons = []
    if info["headings"]["h2"] > 0:
        reasons.append(f"文档包含 {info['headings']['h2']} 个主要章节")
    if info["tables"] > 0:
        reasons.append(f"{info['tables']} 个数据表格")
    if info["metrics"]["count"] > 0:
        reasons.append(f"{info['metrics']['count']} 个关键数据指标")
    reasons.append(f"建议 {pages} 页")
    return PageRecommendation(
        recommended_pages=pages,
        analysis={
            "total_chars": info["total_chars"],
            "sections": info["headings"]["h2"],
            "subsections": info["headings"]["h3"],
            "tables": info["tables"],
            "metrics": info["metrics"]["count"],
        },
        reason="；".join(reasons),
    )


@app.post("/api/generate", response_model=GenerateResponse)
async def generate_ppt(request: GenerateRequest):
    task_id = task_manager.create_task()
    if not request.text_content or not request.text_content.strip():
        return GenerateResponse(task_id=task_id, status=TaskStatus.FAILED,
                                message="请提供文字内容")
    task_manager.set_meta(task_id, template_id=request.template_id,
                          animation_enabled=request.animation_enabled)
    logger.info("任务 %s: 开始生成（纯文本模式，%d 页）", task_id[:8], request.page_count)
    asyncio.create_task(_run_generation(task_id, request))
    return GenerateResponse(task_id=task_id, status=TaskStatus.PENDING, message="任务已提交")


@app.post("/api/generate/upload", response_model=GenerateResponse)
async def generate_ppt_with_files(
    files: list[UploadFile] = File([]),
    title: Optional[str] = Form(None),
    page_count: int = Form(10),
    detail: str = Form("moderate"),
    template_id: str = Form("modern"),
    custom_style_desc: Optional[str] = Form(None),
    text_content: Optional[str] = Form(None),
):
    for f in files:
        err = _validate_file(f)
        if err:
            raise HTTPException(status_code=400, detail=f"{f.filename}: {err}")

    has_files = len(files) > 0
    has_text = bool(text_content and text_content.strip())
    if not has_files and not has_text:
        raise HTTPException(status_code=400, detail="请提供文字内容或上传文件")

    task_id = task_manager.create_task()
    task_manager.set_meta(task_id, template_id=template_id, animation_enabled=True)

    all_text_parts = []
    failed_files = []
    for f in files:
        content = await f.read()
        if len(content) > settings.max_file_size:
            raise HTTPException(status_code=400, detail=f"'{f.filename}' 超过 20MB 限制")
        path = file_service.save_upload(content, f.filename)
        try:
            parsed = DocumentParser.parse(path)
            all_text_parts.append(parsed)
            logger.info("任务 %s: 已解析文件 %s (%d 字符)", task_id[:8], f.filename, len(parsed))
        except Exception as e:
            logger.warning("任务 %s: 文件解析失败 %s - %s", task_id[:8], f.filename, e)
            failed_files.append(f.filename)
            all_text_parts.append(f"# {f.filename}\n（文件解析失败）")

    if has_text:
        user_text = DocumentParser.parse_text(text_content, "用户输入")
        all_text_parts.append(user_text)
        logger.info("任务 %s: 用户输入 %d 字符", task_id[:8], len(user_text))

    combined = "\n\n".join(all_text_parts)
    logger.info("任务 %s: 合并内容共 %d 字符，%d 个文件", task_id[:8], len(combined), len(files))

    # 记录解析失败的文件信息
    if failed_files:
        task_manager.set_meta(task_id, failed_files=failed_files)
        logger.warning("任务 %s: %d 个文件解析失败: %s", task_id[:8], len(failed_files), ", ".join(failed_files))

    request = GenerateRequest(
        text_content=combined, title=title, page_count=page_count,
        detail=detail, template_id=template_id, custom_style_desc=custom_style_desc,
    )
    asyncio.create_task(_run_generation(task_id, request))
    return GenerateResponse(task_id=task_id, status=TaskStatus.PENDING, message="任务已提交")


@app.post("/api/generate/outline", response_model=GenerateResponse)
async def confirm_outline(request: OutlineEditRequest):
    task = task_manager.get_task(request.task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    task_manager.set_pages(request.task_id, request.pages)
    logger.info("任务 %s: 大纲已确认（%d 页），开始润色渲染", request.task_id[:8], len(request.pages))
    asyncio.create_task(_run_polish_and_render(request.task_id))
    return GenerateResponse(task_id=request.task_id, status=TaskStatus.PENDING,
                            message="大纲已确认，开始生成")


@app.post("/api/modify", response_model=GenerateResponse)
async def modify_ppt(request: ModifyRequest):
    task = task_manager.get_task(request.task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if not task.pages:
        raise HTTPException(status_code=400, detail="没有可修改的页面")
    asyncio.create_task(_run_modify(request.task_id, request.new_text, request.modify_scope))
    return GenerateResponse(task_id=request.task_id, status=TaskStatus.PENDING, message="开始修改")


@app.post("/api/restyle", response_model=GenerateResponse)
async def restyle_ppt(request: RestyleRequest):
    task = task_manager.get_task(request.task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if not task.pages:
        raise HTTPException(status_code=400, detail="没有可渲染的页面")
    task_manager.set_meta(request.task_id, template_id=request.template_id)
    asyncio.create_task(_run_restyle(request.task_id, request.template_id,
                                     request.custom_style_desc))
    return GenerateResponse(task_id=request.task_id, status=TaskStatus.PENDING, message="开始重新生成")


@app.get("/api/task/{task_id}", response_model=TaskInfo)
async def get_task_status(task_id: str):
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


@app.get("/api/download/{task_id}")
async def download_ppt(task_id: str):
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task.status != TaskStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="任务尚未完成")
    path = file_service.get_output_path(task_id)
    if not file_service.file_exists(path):
        raise HTTPException(status_code=404, detail="文件不存在或已过期")
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=f"PPT_智造_{task_id}.pptx",
    )


@app.post("/api/cancel/{task_id}", response_model=GenerateResponse)
async def cancel_task(task_id: str):
    task_manager.cancel_task(task_id)
    await task_manager.broadcast(
        task_id,
        WSMessage(event="cancelled", stage="cancelled", stage_name="已取消", percentage=0),
    )
    return GenerateResponse(task_id=task_id, status=TaskStatus.CANCELLED, message="任务已取消")


# ══════════════════════════════════════════
# WebSocket
# ══════════════════════════════════════════

@app.websocket("/ws/task/{task_id}")
async def websocket_progress(websocket: WebSocket, task_id: str):
    await websocket.accept()
    queue = task_manager.subscribe(task_id)
    try:
        while True:
            message = await queue.get()
            if isinstance(message, WSMessage):
                await websocket.send_json(message.model_dump())
            task = task_manager.get_task(task_id)
            if task and task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                break
    except WebSocketDisconnect:
        pass
    finally:
        task_manager.unsubscribe(task_id, queue)


# ══════════════════════════════════════════
# 生成流程
# ══════════════════════════════════════════

async def _run_generation(task_id: str, request: GenerateRequest):
    """阶段 1：解析内容 → 规划大纲 → 返回给前端预览"""
    try:
        tid = task_id[:8]

        content = request.text_content or ""
        if request.title:
            content = f"# {request.title}\n\n{content}"

        logger.info("任务 %s: 开始规划大纲（内容 %d 字符，%d 页）", tid, len(content), request.page_count)
        await task_manager.broadcast(
            task_id, WSMessage(stage="planning", stage_name="AI 规划大纲中...", percentage=10))

        pages = await _with_heartbeat(
            task_id, "规划大纲",
            planner.plan(
                content=content,
                page_count=request.page_count,
                detail=request.detail,
                title=request.title,
                user_prompt=request.custom_style_desc,
            ),
        )

        logger.info("任务 %s: 大纲生成完毕，共 %d 页", tid, len(pages))
        for i, p in enumerate(pages):
            logger.info("  第 %d 页 [%s] %s (%d 要点)", i + 1, p.type, p.title, len(p.points))

        task_manager.set_pages(task_id, pages)
        task_manager.update_progress(task_id, TaskStatus.PLANNED, 40, "大纲已生成")
        
        # 等待 WebSocket 连接建立
        await task_manager.wait_for_ws(task_id)
        
        await task_manager.broadcast(
            task_id,
            WSMessage(event="planned", stage="planned", stage_name="大纲已生成，请确认",
                      percentage=40, detail=f"共 {len(pages)} 页", pages=pages),
        )
    except Exception as e:
        await _send_error(task_id, "大纲生成", e)


async def _run_polish_and_render(task_id: str):
    """阶段 2：逐页润色 → 逐页推送 → 渲染 PPTX → 通知下载"""
    task = task_manager.get_task(task_id)
    if not task or not task.pages:
        return

    tid = task_id[:8]
    pages = task.pages
    total = len(pages)
    logger.info("任务 %s: 开始逐页润色 (%d 页)", tid, total)

    try:
        # ═══════════ 逐页润色并实时推送 ═══════════
        polished_pages = []
        for i, page in enumerate(pages):
            pct = 50 + int(20 * (i + 1) / total)  # 50% ~ 70%

            await task_manager.broadcast(
                task_id,
                WSMessage(stage="polishing",
                          stage_name=f"润色第 {i + 1}/{total} 页...",
                          percentage=pct,
                          detail=f"正在处理: {page.title}"),
            )
            logger.info("任务 %s: 润色 %d/%d [%s] %s", tid, i + 1, total, page.type, page.title)

            single = [page]
            try:
                polished = await polisher.polish(single)
                polished_pages.append(polished[0] if (polished and len(polished) == 1) else page)
            except Exception as e:
                logger.warning("任务 %s: 润色第 %d 页失败 - %s", tid, i + 1, e)
                polished_pages.append(page)

            # 实时更新预览
            task_manager.set_pages(task_id, polished_pages + pages[i + 1:])
            await task_manager.broadcast(
                task_id,
                WSMessage(event="page_ready", stage="polishing",
                          stage_name=f"第 {i + 1}/{total} 页完成",
                          percentage=pct,
                          pages=polished_pages + pages[i + 1:],
                          detail=f"已完成: {page.title}"),
            )

        logger.info("任务 %s: 润色完毕 (%d 页) → 开始生成 PPTX 文件", tid, len(polished_pages))

        if task_manager.is_cancelled(task_id):
            return

        # ═══════════ 渲染 PPTX ═══════════
        task_manager.update_progress(task_id, TaskStatus.RENDERING, 85, "正在生成 PPT 文件...")
        await task_manager.broadcast(
            task_id,
            WSMessage(event="rendering", stage="rendering",
                      stage_name="正在生成 PPT 文件...", percentage=85),
        )

        output_path = file_service.get_output_path(task_id)
        meta = task_manager.get_meta(task_id)
        template_id = meta.get("template_id", "modern")
        animation = meta.get("animation_enabled", True)

        # 在线程池中执行同步渲染，避免阻塞事件循环
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            _render_sync, template_id, polished_pages, output_path, animation,
        )

        file_size = file_service.get_file_size(output_path)
        task_manager.set_result(task_id, file_size)
        task_manager.set_pages(task_id, polished_pages)

        size_str = f"{file_size / 1024:.1f}KB" if file_size else "未知"
        logger.info("任务 %s: ✅ 完成！文件已生成 (%s)", tid, size_str)

        # ═══════════ 通知完成 ═══════════
        task_manager.update_progress(task_id, TaskStatus.COMPLETED, 100, "生成完成，可以下载")
        await task_manager.broadcast(
            task_id,
            WSMessage(event="completed", stage="completed",
                      stage_name="生成完成，可以下载",
                      percentage=100, pages=polished_pages,
                      detail=f"文件大小: {size_str}"),
        )
    except Exception as e:
        await _send_error(task_id, "生成", e)


def _render_sync(template_id: str, pages: list, output_path: str, animation: bool):
    """同步渲染 PPTX 文件（在线程池中调用）"""
    renderer = PPTRenderer(template_id=template_id, animation_enabled=animation)
    title = pages[0].title if pages else "PPT"
    renderer.render(title=title, pages=pages, output_path=output_path)


async def _run_modify(task_id: str, new_text: str, scope: Optional[str] = None):
    task = task_manager.get_task(task_id)
    if not task or not task.pages:
        return
    tid = task_id[:8]
    try:
        logger.info("任务 %s: 开始增量修改", tid)
        await task_manager.broadcast(
            task_id, WSMessage(stage="planning", stage_name="AI 调整结构中...", percentage=10))

        new_pages = await _with_heartbeat(
            task_id, "调整结构",
            planner.plan_for_modify(task.pages, new_text, scope),
        )
        task_manager.set_pages(task_id, new_pages)

        # 逐页润色
        polished_pages = []
        for i, page in enumerate(new_pages):
            pct = 40 + int(35 * (i + 1) / len(new_pages))
            single = [page]
            try:
                result = await polisher.polish(single)
                polished_pages.append(result[0] if result else page)
            except Exception:
                polished_pages.append(page)
            task_manager.set_pages(task_id, polished_pages + new_pages[i + 1:])

        # 渲染
        output_path = file_service.get_output_path(task_id)
        meta = task_manager.get_meta(task_id)
        template_id = meta.get("template_id", "modern")

        renderer = PPTRenderer(template_id=template_id, animation_enabled=True)
        renderer.render(
            title=polished_pages[0].title if polished_pages else "PPT",
            pages=polished_pages, output_path=output_path,
        )

        file_size = file_service.get_file_size(output_path)
        task_manager.set_result(task_id, file_size)
        task_manager.set_pages(task_id, polished_pages)
        task_manager.update_progress(task_id, TaskStatus.COMPLETED, 100, "修改完成")
        logger.info("任务 %s: 修改完成", tid)
        await task_manager.broadcast(
            task_id,
            WSMessage(event="completed", stage="completed", stage_name="修改完成",
                      percentage=100, pages=polished_pages),
        )
    except Exception as e:
        await _send_error(task_id, "修改", e)


async def _run_restyle(task_id: str, template_id: str, custom_desc: Optional[str] = None):
    task = task_manager.get_task(task_id)
    if not task or not task.pages:
        return
    tid = task_id[:8]
    try:
        logger.info("任务 %s: 换风格为 %s", tid, template_id)
        task_manager.update_progress(task_id, TaskStatus.RENDERING, 50, "换风格渲染中...")
        await task_manager.broadcast(
            task_id, WSMessage(stage="designing", stage_name="换风格渲染中...", percentage=50))

        output_path = file_service.get_output_path(task_id)
        renderer = PPTRenderer(template_id=template_id, custom_style_desc=custom_desc)
        renderer.render(
            title=task.pages[0].title if task.pages else "PPT",
            pages=task.pages, output_path=output_path,
        )

        file_size = file_service.get_file_size(output_path)
        task_manager.set_result(task_id, file_size)
        task_manager.update_progress(task_id, TaskStatus.COMPLETED, 100, "生成完成")
        logger.info("任务 %s: 换风格完成", tid)
        await task_manager.broadcast(
            task_id,
            WSMessage(event="completed", stage="completed", stage_name="生成完成",
                      percentage=100, pages=task.pages),
        )
    except Exception as e:
        await _send_error(task_id, "换风格", e)


# ══════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    uvicorn.run("main:app", host=settings.host, port=settings.port, reload=True)
