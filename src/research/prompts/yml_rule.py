# ymlファイルを書くうえでのルールを記述したプロンプトをまとめてください
from research.log_output.log import log


def get_yml_rules(branch_name:str):
    log("info", "GitHub Actionsのyml記述ルールを取得しました。")
    YML_RULES = f"""
      書き方についてのルール:
      - インデントは GitHub Actions の公式仕様に沿ってください
      - 必ず on: と jobs: を含む完全な GitHub Actions YAML 構造にしてください
      - コメントは#で始めてください
      - ジョブ、ステップの内容を必ずコメントで説明してください
      ジョブやステップについてのルール:
      - on:のイベントにはpush(ブランチは{branch_name})のみを指定してください、ただしコメントで他のイベントの追加の仕方を説明してください
      - ビルドとテストの2つのジョブのみ作成してください(テストに関連するファイルが存在しない場合などは、テストジョブは省略してください)
      - Lintの実行を記述する際は必ず、continue-on-error: trueを指定してください
      - ジョブは適切に必要最低限のpermissionを設定してください
      - ジョブでは必ず適切なタイムアウトを設定してください
      - actions/checkout アクションを使用するときは必ず適切にpersist-credentialsを設定してください
      - キャッシュは必ず必要な場合以外は使用しないでください
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
    return YML_RULES
