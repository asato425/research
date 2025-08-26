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

### 3. 仮想環境の有効化

```bash
poetry env activate

# 次に表示されたコマンドをコピーして実行
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
