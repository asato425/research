# ymlファイルを書くうえでのルールを記述したプロンプトをまとめてください
from research.log_output.log import log
YML_RULES = """
- インデントはスペース2つ
- onキーは必ず記述し、イベントにはworkflow_dispatchのみを指定する
- コメントは#で始める
- ジョブの内容を必ずコメントで説明する
- ビルドとテストは必ず分けて記述する
- 必ずバージョンを指定して記述する
- アクションはバージョンを指定するのではなく、SHAを指定する
- キーは小文字のスネークケースで記述する
- 値は基本的に文字列で、必要に応じてリストやマップを使用する
- ...
"""

def get_yml_rules():
    log("info", "GitHub Actionsのyml記述ルールを取得しました。")
    return YML_RULES
