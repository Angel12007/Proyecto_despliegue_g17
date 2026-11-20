"""Configuración de la API UCI Analytics."""
import logging
import os
import sys

from loguru import logger


class Settings:
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "UCI Analytics API - Grupo 17"
    # Orígenes permitidos (CORS), separados por coma. "*" permite todos.
    BACKEND_CORS_ORIGINS: list[str] = os.getenv("CORS_ORIGINS", "*").split(",")
    LOGGING_LEVEL: int = logging.INFO


class InterceptHandler(logging.Handler):
    """Envía los mensajes de uvicorn a loguru."""

    def emit(self, record: logging.LogRecord) -> None:  # pragma: no cover
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = str(record.levelno)
        logger.opt(exception=record.exc_info).log(level, record.getMessage())


def setup_app_logging(config: "Settings") -> None:
    logging.getLogger().handlers = [InterceptHandler()]
    for nombre in ("uvicorn.asgi", "uvicorn.access"):
        logging.getLogger(nombre).handlers = [InterceptHandler(level=config.LOGGING_LEVEL)]
    logger.configure(handlers=[{"sink": sys.stderr, "level": config.LOGGING_LEVEL}])


settings = Settings()
