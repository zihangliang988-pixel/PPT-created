"""LLM 客户端 —— 封装 OpenAI 兼容 API 调用"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from openai import AsyncOpenAI

from config import settings

logger = logging.getLogger(__name__)


class LLMError(RuntimeError):
    """LLM 调用失败的专用异常"""


class LLMTimeoutError(LLMError):
    """LLM 请求超时"""


class LLMClient:
    """LLM 调用封装"""

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_api_url,
        )
        self.model = settings.llm_model
        self.timeout = settings.llm_timeout

    async def chat(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.3,
        max_tokens: int = 16384,
        response_format: Optional[dict] = None,
        extra_body: Optional[dict] = None,
    ) -> str:
        """调用 LLM 并返回纯文本内容。

        超时不重试（推理模型重试无意义），其他错误重试 1 次。
        失败时抛出 LLMError 或 LLMTimeoutError。
        """
        last_error: Optional[Exception] = None

        for attempt in range(2):
            try:
                kwargs: dict = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
                if response_format:
                    kwargs["response_format"] = response_format
                if extra_body:
                    kwargs["extra_body"] = extra_body

                response = await asyncio.wait_for(
                    self.client.chat.completions.create(**kwargs),
                    timeout=self.timeout,
                )
                content = response.choices[0].message.content or ""
                logger.debug(
                    "LLM 调用成功 tokens(prompt=%d completion=%d)",
                    response.usage.prompt_tokens if response.usage else 0,
                    response.usage.completion_tokens if response.usage else 0,
                )
                return content

            except asyncio.TimeoutError:
                last_error = LLMTimeoutError(
                    f"LLM 请求超时（{self.timeout} 秒）。"
                    f"ClawClaw 推理模型处理大量内容时可能需要较长时间，"
                    f"请尝试减少输入内容或增加页数。"
                )
                logger.warning(str(last_error))
                break  # 超时不重试

            except Exception as e:
                last_error = LLMError(f"LLM 调用失败: {str(e)[:200]}")
                logger.warning("LLM 调用失败 (尝试 %d/2): %s", attempt + 1, e)
                if attempt < 1:
                    await asyncio.sleep(2)

        raise last_error or LLMError("LLM 服务不可用")
