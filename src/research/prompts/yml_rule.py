# ymlファイルを書くうえでのルールを記述したプロンプトをまとめてください
from research.log_output.log import log
YML_RULES = """
- YAML の内容だけを出力してください。Markdown の ```yaml や ``` は出力しないでください。
- インデントは GitHub Actions の公式仕様に沿ってください
- 必ず on: と jobs: を含む完全な GitHub Actions YAML 構造にしてください
- on:のイベントにはworkflow_dispatchのみを指定してください、ただしコメントで他のイベントの追加の仕方を説明してください
- コメントは#で始めてください
- ジョブ、ステップの内容を必ずコメントで説明してください
- ビルドとテストは必ず分けて記述してください
- 必ずバージョンを指定して記述してください
- キーは小文字のスネークケースで記述してください
- 値は基本的に文字列で、必要に応じてリストやマップを使用してください
- ...
"""

def get_yml_rules():
    log("info", "GitHub Actionsのyml記述ルールを取得しました。")
    return YML_RULES
