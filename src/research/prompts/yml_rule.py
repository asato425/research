# ymlファイルを書くうえでのルールを記述したプロンプトをまとめてください
from research.log_output.log import log
YML_RULES = """
書き方についてのルール:
- インデントは GitHub Actions の公式仕様に沿ってください
- 必ず on: と jobs: を含む完全な GitHub Actions YAML 構造にしてください
- コメントは#で始めてください
- ジョブ、ステップの内容を必ずコメントで説明してください
ジョブやステップについてのルール:
- on:のイベントにはworkflow_dispatchのみを指定してください、ただしコメントで他のイベントの追加の仕方を説明してください
- ビルドとテストの2つのジョブのみ作成してください
- ジョブは適切に必要最低限のpermissionを設定してください
- ジョブでは必ず適切なタイムアウトを設定してください
- actions/checkout アクションを使用するときは必ず適切にpersist-credentialsを設定してください
- ジョブやステップには必ずnameキーでわかりやすく簡潔な名前をつけてください
- 必ずバージョンを指定して記述してください
- キーは小文字のスネークケースで記述してください
- 値は基本的に文字列で、必要に応じてリストやマップを使用してください
その他のルール:
- YAML の内容だけを出力してください。Markdown の ```yaml や ``` は出力しないでください。
生成例：
name: CI
on: 
  workflow_dispatch:
jobs:
  build:
    ...  # ビルドジョブの詳細
  tests:
    ...  # テストジョブの詳細
"""

def get_yml_rules():
    log("info", "GitHub Actionsのyml記述ルールを取得しました。")
    return YML_RULES
