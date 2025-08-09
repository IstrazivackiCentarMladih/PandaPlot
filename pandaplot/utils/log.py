import logging
from pathlib import Path

def setup_logging(
    log_file: str | Path = "application.log",
    level: int = logging.INFO,
    cli_level: int = logging.INFO,
    file_level: int = logging.DEBUG,
    datefmt: str = "%Y-%m-%d %H:%M:%S"
):
    """
    Sets up logging for a PySide6 application to both file and CLI.

    Parameters
    ----------
    log_file : str | Path
        Path to the log file.
    level : int
        Minimum logging level for the root logger.
    cli_level : int
        Logging level for console output.
    file_level : int
        Logging level for file output.
    datefmt : str
        Format for timestamps in logs.
    """
    log_file = Path(log_file)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger()
    logger.setLevel(level)

    # Prevent duplicate handlers if called multiple times
    logger.handlers.clear()

    # Format: timestamp | level | logger name (module/class) | function | message
    log_format = "%(asctime)s | %(levelname)s | %(name)s | %(funcName)s | %(message)s"
    formatter = logging.Formatter(fmt=log_format, datefmt=datefmt)

    # File handler
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(file_level)
    file_handler.setFormatter(formatter)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(cli_level)
    console_handler.setFormatter(formatter)

    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logger.debug(f"Logging initialized. Log file at: {log_file}")
    return logger