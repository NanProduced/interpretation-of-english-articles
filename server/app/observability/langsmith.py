import logging
import os

from app.config.settings import Settings

logger = logging.getLogger(__name__)

_LANGSMITH_INITIALIZED = False


def setup_langsmith(settings: Settings) -> bool:
    """Initialize LangSmith tracing if environment is configured.

    Returns True when LangSmith was initialized successfully, otherwise False.
    """

    global _LANGSMITH_INITIALIZED

    if _LANGSMITH_INITIALIZED:
        return True

    if not settings.langsmith_enabled:
        logger.info("LangSmith disabled by configuration.")
        return False

    if not settings.langsmith_api_key:
        logger.warning("LangSmith enabled but LANGSMITH_API_KEY is missing.")
        return False

    os.environ["LANGSMITH_TRACING"] = str(settings.langsmith_tracing).lower()
    os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
    os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
    os.environ["LANGSMITH_ENDPOINT"] = settings.langsmith_endpoint

    if settings.langsmith_workspace_id:
        os.environ["LANGSMITH_WORKSPACE_ID"] = settings.langsmith_workspace_id

    try:
        from langsmith.integrations.otel import configure
        from pydantic_ai import Agent
    except ImportError as exc:
        logger.exception("LangSmith dependencies are not available: %s", exc)
        return False

    try:
        configure(project_name=settings.langsmith_project)
        Agent.instrument_all()
        _LANGSMITH_INITIALIZED = True
        logger.info(
            "LangSmith initialized for project '%s'.",
            settings.langsmith_project,
        )
        return True
    except Exception as exc:  # pragma: no cover - defensive startup guard
        logger.exception("Failed to initialize LangSmith: %s", exc)
        return False

