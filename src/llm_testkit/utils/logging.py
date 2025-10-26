"""日誌系統模組。

提供統一的日誌配置與管理。
"""

import logging
import sys
from pathlib import Path


def setup_logger(
    name: str = "qfoundry",
    level: str = "INFO",
    log_file: str | Path | None = None,
) -> logging.Logger:
    """設定日誌系統。

    Args:
        name: Logger 名稱
        level: 日誌級別（DEBUG, INFO, WARNING, ERROR, CRITICAL）
        log_file: 日誌檔案路徑（可選）

    Returns:
        配置好的 Logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    # 避免重複添加 handler
    if logger.handlers:
        return logger

    # 格式化
    formatter = logging.Formatter(
        "%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler（可選）
    if log_file:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


# 預設 logger
default_logger = setup_logger()
