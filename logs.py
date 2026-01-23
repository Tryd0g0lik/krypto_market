# logs.py
"""
This module provides logging configuration.
Logs are output to both console and a log file (default: 'log_putout.log').
"""

import logging
import os
import threading
import time
from typing import Optional

_log_maintenance_started = False

_log_lock = threading.Lock()


def configure_logging(
    level: int = logging.INFO, log_file: str = "log_putout.log"
) -> None:
    """
    Initialize logging configuration.

    Args:
        level: Logging level (default: logging.INFO)
        log_file: Name of the log file (default: 'log_putout.log')

    Example:
        import logging
        from rabbit.logs import configure_logging
        log = logging.getLogger(__name__)
        configure_logging(logging.INFO)
        log.info("Application started")
    """
    # Clear any existing handlers
    logging.getLogger().handlers.clear()

    # Create formatter
    formatter = logging.Formatter(
        "[%(asctime)s.%(msecs)03d] %(levelname)s - %(name)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S.%u",
    )

    # File handler
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    # # Console handler
    # console_handler = logging.StreamHandler()
    # console_handler.setLevel(level)
    # console_handler.setFormatter(formatter)

    # Configure root logger
    # logging.basicConfig(
    #     level=level, handlers=[file_handler, console_handler], force=True
    # )
    #
    logging.basicConfig(level=level, handlers=[file_handler], force=True)

    # Start log file maintenance thread ONLY ONCE
    global _log_maintenance_started
    with _log_lock:
        threading.Thread(
            target=check_log_file,
            args=(log_file,),
            daemon=True,
            name="LogFileMaintenance",
        ).start()
        _log_maintenance_started = True


def check_log_file(
    log_file: str, max_lines: int = 3000, check_interval: int = 1800
) -> None:
    """
    Check log file size and rotate if needed.

    Args:
        log_file: Path to log file
        max_lines: Maximum lines before rotation (default: 3000)
        check_interval: Check interval in seconds (default: 1800 = 30 min)
    """
    while True:
        time.sleep(check_interval)
        try:
            with _log_lock:
                if not os.path.exists(log_file):
                    continue
                with open(log_file, "r+", encoding="utf-8") as f:
                    lines = f.readlines()
                    if len(lines) >= max_lines:
                        # ---------------- new lines
                        backup_file = f"{log_file}.backup"
                        if os.path.exists(backup_file):
                            os.remove(backup_file)
                        os.rename(log_file, backup_file)
                        # ---------------- end new lines
                        # f.seek(0)
                        # f.truncate()
                        logging.warning(
                            "Log file %s was cleared (%d lines exceeded limit of %d)",
                            log_file,
                            len(lines),
                            max_lines,
                        )
        except Exception as e:
            logging.error("Error checking log file: %s", str(e), exc_info=True)


class Logger:
    """Utility class for logging operations."""

    @staticmethod
    def get_class_name(obj: object) -> str:
        """Get class name of an object."""
        return obj.__class__.__name__


# ======================= Additional =======================
# Дополнительные рекомендации:
# Не вызывайте configure_logging() многократно в тестах.
# Используйте setUp/tearDown или фикстуры pytest для одноразовой настройки.
# Используйте RotatingFileHandler из стандартной библиотеки:
# from logging.handlers import RotatingFileHandler
#
# file_handler = RotatingFileHandler(
#     log_file, maxBytes=10*1024*1024, backupCount=5, encoding="utf-8"
# )
# Он сам управляет ротацией и потокобезопасен.
# В тестах можно отключать проверку лог-файла:
# if not os.environ.get("PYTEST_CURRENT_TEST"):
#     threading.Thread(...).start()
# Главная причина ошибки — закомментированный time.sleep, из-за которого потоки без задержки пытаются одновременно читать файл, блокируя друг друга.
# ==========================================================
