# ymlファイルを書くうえでのルールを記述したプロンプトをまとめてください
from ..log_output.log import log
YML_RULES = """
- インデントはスペース2つ
- コメントは#で始める
- キーは小文字のスネークケースで記述する
- 値は基本的に文字列で、必要に応じてリストやマップを使用する
- ...
"""
    
def get_yml_rules(log_is:bool = True):
    log("info", "GitHub Actionsのyml記述ルールを取得しました。", log_is)
    return YML_RULES
