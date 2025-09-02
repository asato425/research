# ログ出力用の関数を実装

str_futoji = "\033[1m"
str_kasen = "\033[4m"
str_red = "\033[31m"    # バグ、エラーの出力用
str_green = "\033[32m"
str_yellow = "\033[33m" # 警告を示すもの
str_blue = "\033[34m"
str_magenta = "\033[35m"
str_cyan = "\033[36m"
str_reset = "\033[0m"

def log(status: str, message: str, log_is: bool=True) -> None:
    """
    ログメッセージを出力する関数
    """
    if log_is:
        if status == "success":
            print(f"{str_futoji}{str_green}(LOG){status}: {message}{str_reset}")
        elif status == "warning":
            print(f"{str_futoji}{str_yellow}(LOG){status}: {message}{str_reset}")
        elif status == "info":
            print(f"{str_futoji}{str_blue}(LOG){status}: {message}{str_reset}")
        else:
            print(f"{str_futoji}{str_red}(LOG){status}: {message}{str_reset}")
