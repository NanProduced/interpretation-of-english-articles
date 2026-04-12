"""
日志配置模块。

使用 Python logging 标准配置，支持：
- 控制台输出（带颜色）
- 分层 logger（uvicorn / app）
- 可配置日志级别
"""

from logging import DEBUG, INFO, WARNING, Formatter, StreamHandler, getLogger
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.config.settings import Settings, get_settings


def setup_logging(settings: Settings | None = None) -> None:
    """配置应用日志系统。"""
    if settings is None:
        settings = get_settings()

    # 日志级别映射
    level_map = {
        "DEBUG": DEBUG,
        "INFO": INFO,
        "WARNING": WARNING,
    }
    app_level = level_map.get(settings.log_level.upper(), INFO)

    # --- formatter ---
    detailed_formatter = Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    simple_formatter = Formatter(
        fmt="%(levelname)-8s | %(message)s",
    )

    # --- console handler ---
    console_handler = StreamHandler()
    console_handler.setLevel(app_level)
    console_handler.setFormatter(detailed_formatter)

    # --- file handler（可选，保留最近 10MB 日志） ---
    log_dir = Path(__file__).parent.parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    file_handler = RotatingFileHandler(
        log_dir / "app.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(DEBUG)
    file_handler.setFormatter(detailed_formatter)

    # --- 根 logger（uvicorn 系列） ---
    root_logger = getLogger()
    root_logger.setLevel(WARNING)  # uvicorn access/钟式日志只显示 WARNING+
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # --- app logger ---
    app_logger = getLogger("app")
    app_logger.setLevel(app_level)
    app_logger.handlers.clear()
    app_logger.addHandler(console_handler)
    app_logger.addHandler(file_handler)
    # 防止日志向上传播到 root，避免重复输出
    app_logger.propagate = False

    # --- uvicorn / fastapi 日志降级 ---
    # uvicorn 默认输出太多，改为只显示 WARNING+
    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
        uv_logger = getLogger(logger_name)
        uv_logger.setLevel(WARNING)
        uv_logger.handlers.clear()
        # 仅控制台，不写文件
        handler = StreamHandler()
        handler.setFormatter(simple_formatter)
        uv_logger.addHandler(handler)
        uv_logger.propagate = False

    # --- third-party loggers（降低噪声） ---
    noisy_loggers = {
        "sqlalchemy.engine": WARNING,
        "httpx": WARNING,
        "openai": WARNING,
        "langchain": WARNING,
        "temporal": WARNING,
    }
    for name, level in noisy_loggers.items():
        lg = getLogger(name)
        lg.setLevel(level)
        lg.propagate = True  # 继承 root handler
