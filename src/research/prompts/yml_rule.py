# ymlファイルを書くうえでのルールを記述したプロンプトをまとめてください
from research.log_output.log import log
YML_RULES = """
- YAML の内容だけを出力してください。Markdown の ```yaml や ``` は出力しないでください。
- インデントは GitHub Actions の公式仕様に沿ってください
- 必ず on: と jobs: を含む完全な GitHub Actions YAML 構造にしてください
- on:のイベントにはworkflow_dispatchのみを指定する
- コメントは#で始める
- ジョブの内容を必ずコメントで説明する
- ビルドとテストは必ず分けて記述する
- 必ずバージョンを指定して記述する
- キーは小文字のスネークケースで記述する
- 値は基本的に文字列で、必要に応じてリストやマップを使用する
- ...
"""

def get_yml_rules():
    log("info", "GitHub Actionsのyml記述ルールを取得しました。")
    return YML_RULES
