# research

## Poetryの利用方法

### 1. Poetryのインストール

Poetryが未インストールの場合は、以下のコマンドでインストールしてください。

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

### 2. 依存パッケージのインストール

```bash
poetry install
```
### 4. パッケージの追加

```bash
poetry add パッケージ名
```

### 5. パッケージの削除

```bash
poetry remove パッケージ名
```

### 6. バージョンの更新

```bash
poetry version patch   # パッチバージョンを+1
poetry version minor   # マイナーバージョンを+1
poetry version major   # メジャーバージョンを+1
```

### 7. テストの実行

```bash
poetry run pytest
```

### 8. requirements.txtの生成（必要な場合）

```bash
poetry export -f requirements.txt --output requirements.txt
```

---

詳細は[Poetry公式ドキュメント](https://python-poetry.org/docs/)も参照してください。

## テストの実行方法
```shell
poetry run pytest tests/test_github.py # 特定のテストファイルの実行

poetry run pytest tests/ # フォルダ内の全てのテストを実行
```

## 必要なインストールなど
```shell
# インストール
brew install pinact

brew install actionlint

brew install suzuki-shunsuke/ghalint/ghalint

# 環境設定
touch .env
# このファイルに必要なAPIキーを設定してください
# 例）
# GITHUB_TOKEN=********
# # GPTの環境変数
# OPENAI_API_KEY= "******"
# #Gemini の環境変数
# GOOGLE_API_KEY=******* ※ダブルクォーテーションで囲まないでください
# #Anthropic の環境変数
# ANTHROPIC_API_KEY="******"

```


## best_practices
- 本来LLMに生成させるがコスト削減のためGPT-5-miniで生成させたものを使い回す