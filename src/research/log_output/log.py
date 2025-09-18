
import logging
import sys

class ColorFormatter(logging.Formatter):
    COLOR_MAP = {
        "SUCCESS": "\033[32m",
        "WARNING": "\033[33m",
        "INFO": "\033[34m",
        "ERROR": "\033[31m",
        "FAIL": "\033[31m",
    }
    STR_BOLD = "\033[1m"
    STR_RESET = "\033[0m"

    def format(self, record):
        levelname = record.levelname
        color = self.COLOR_MAP.get(levelname, "\033[31m")
        msg = super().format(record)
        return f"{self.STR_BOLD}{color}{levelname}: {msg}{self.STR_RESET}"

# ロガー設定
logger = logging.getLogger("research")
handler = logging.StreamHandler(sys.stdout)
formatter = ColorFormatter("%(message)s")
handler.setFormatter(formatter)
logger.handlers = [handler]
logger.setLevel(logging.INFO)

log_is = True
def set_log_is(value: bool):
    global log_is
    log_is = value

def log(status: str, message: str) -> None:
    """
    loggingモジュールを使ったログ出力関数
    status: success/info/warning/error/fail など
    """
    if not log_is:
        return
    # status→levelname変換
    level_map = {
        "success": "SUCCESS",
        "info": "INFO",
        "warning": "WARNING",
        "error": "ERROR",
        "fail": "FAIL",
    }
    levelname = level_map.get(status.lower(), "ERROR")
    # カスタムレベル追加（SUCCESS, FAIL）
    if not hasattr(logging, levelname):
        logging.addLevelName(25, "SUCCESS")
        logging.addLevelName(35, "FAIL")
    if levelname == "SUCCESS":
        logger.log(25, message)
    elif levelname == "FAIL":
        logger.log(35, message)
    elif levelname == "INFO":
        logger.info(message)
    elif levelname == "WARNING":
        logger.warning(message)
    else:
        logger.error(message)
