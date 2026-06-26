"""全局配置"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    # 服务
    host: str = "0.0.0.0"
    port: int = 3000

    # LLM — 请通过环境变量或 .env 文件设置
    # 复制 .env.example 到 .env 并填写你的配置
    llm_model: str = ""
    llm_api_url: str = ""
    llm_api_key: str = ""
    llm_timeout: int = 300
    llm_max_tokens_plan: int = 32768          # 规划阶段 token 预算
    llm_max_tokens_polish: int = 8192         # 润色阶段 token 预算
    llm_max_tokens_summary: int = 4096        # 摘要阶段 token 预算
    content_max_chars: int = 15000            # 单次传给 LLM 的最大字符数
    content_summary_threshold: int = 10000    # 超过此长度先摘要再规划

    # 文件
    upload_dir: str = "uploads"
    output_dir: str = "output"
    max_file_size: int = 20 * 1024 * 1024  # 20MB
    allowed_extensions: list[str] = [".pdf", ".docx", ".txt", ".md"]

    # 任务
    task_cleanup_hours: int = 2


settings = Settings()
