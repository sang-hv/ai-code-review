from typing import TYPE_CHECKING

from loguru import logger

from argus_review.config import settings

if TYPE_CHECKING:
    from loguru import Logger

logger.remove()
logger.add(
    sink=lambda msg: print(msg, end=""),
    format=settings.logger.format,
    level=settings.logger.level,
)


def get_logger(name: str) -> "Logger":
    return logger.bind(logger_name=name)
