# research

## 利用方法

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
詳細は[Poetry公式ドキュメント](https://python-poetry.org/docs/)も参照してください。

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

##ここからは任意
# #Gemini の環境変数
# GOOGLE_API_KEY=******* ※ダブルクォーテーションで囲まないでください
# #Anthropic の環境変数
# ANTHROPIC_API_KEY="******"
```
gpt-5-mini以外で利用したい場合`src/research/main.py`のMODEL_NAME,TEMPERATUREと`src/research/tools/llm.py`の`create_model`関数の`models`にモデルを追加してください。


## best_practices
- 本来LLMに生成させるがコスト削減のためGPT-5で生成させたものを使い回すよう設定しています。
- この設定を無効にしたい場合は、`src/research/main.py`の`BEST_PRACTICES_ENABLE_REUSE`を`False`に設定してください。
```python
BEST_PRACTICES_ENABLE_REUSE = False
```

## 実行方法
```bash
# まず、
# 実行方法:src/research/main.pyの実行制御フラグなどの設定値(6~35行)を確認してください。初期値では誤作動によりLLMが利用されないよう、Falseに設定しています。利用したい場合はTrueに修正してください。
poetry run python src/research/main.py --repo_url "リポジトリのURL" --work_ref "作業用のブランチ名" --yml_file_name "生成されるYAMLファイル名" --max_required_files 5 --loop_count_max 5 --lint_loop_count_max 3 --best_practice_num 10
# --repo_urlのみ必須、他は任意(src/research/main.pyの28~32行目でも設定可能)
# 実行例）
poetry run python  src/research/main.py --repo_url "https://github.com/asato425/test"
```