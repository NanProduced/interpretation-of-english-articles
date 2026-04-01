import logging
import os

from app.config.settings import Settings

logger = logging.getLogger(__name__)

# 全局标志：用于记录 LangSmith 是否已完成初始化，避免重复初始化
_LANGSMITH_INITIALIZED = False


def setup_langsmith(settings: Settings) -> bool:
    """Initialize LangSmith tracing if environment is configured.

    Args:
        settings: 应用程序配置对象，包含 LangSmith 相关的配置项

    Returns:
        bool: LangSmith 初始化成功返回 True，否则返回 False
    """

    global _LANGSMITH_INITIALIZED

    # 如果已经初始化过，直接返回成功
    if _LANGSMITH_INITIALIZED:
        return True

    # 检查配置是否启用了 LangSmith
    if not settings.langsmith_enabled:
        logger.info("LangSmith disabled by configuration.")
        return False

    # 检查 API Key 是否配置
    if not settings.langsmith_api_key:
        logger.warning("LangSmith enabled but LANGSMITH_API_KEY is missing.")
        return False

    # 设置 LangSmith 所需的环境变量。
    # 当前项目以 LangGraph / LangSmith SDK tracing 为主，
    # 不再混用 PydanticAI 全局 OTel 自动 instrumentation。
    tracing_enabled = str(settings.langsmith_tracing).lower()
    os.environ["LANGSMITH_TRACING"] = tracing_enabled
    os.environ["LANGSMITH_TRACING_V2"] = tracing_enabled
    os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
    os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
    os.environ["LANGSMITH_ENDPOINT"] = settings.langsmith_endpoint

    # 如果配置了工作区 ID，则设置对应环境变量
    if settings.langsmith_workspace_id:
        os.environ["LANGSMITH_WORKSPACE_ID"] = settings.langsmith_workspace_id

    _LANGSMITH_INITIALIZED = True
    logger.info(
        "LangSmith environment initialized for project '%s'.",
        settings.langsmith_project,
    )
    return True
