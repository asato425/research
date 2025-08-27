"""
RAG（Retrieval-Augmented Generation）関連の処理をまとめるモジュール。
WebやGitHubなどから情報を取得し、LLMに渡すための構造化データを生成する関数やクラスを実装。
"""

from typing import Any, Callable
import os

def file_filter_factory(allow_exts=None, deny_exts=None, allow_all=False):
    """
    柔軟なファイルフィルター関数を生成するファクトリー。
    allow_exts: 許可する拡張子リスト（例: ['.md', '.py']）
    deny_exts: 除外する拡張子リスト（例: ['.png', '.jpg']）
    allow_all: Trueなら全て許可
    戻り値: file_path:str -> bool な関数
    """
    def _filter(file_path: str) -> bool:
        if allow_all:
            return True
        ext = os.path.splitext(file_path)[1].lower()
        if deny_exts and ext in deny_exts:
            return False
        if allow_exts:
            return ext in allow_exts
        # デフォルトは.md, .mdx, .py, .txt, .jsonのみ許可
        return ext in ['.md', '.mdx', '.py', '.txt', '.json']
    return _filter

def _git_loader(clone_url: str, repo_path: str, file_filter: Callable, branch: str = "master") -> list:
    """
    指定したGitリポジトリからドキュメントを読み込む関数。
    すでにローカルにリポジトリが存在する場合はクローンせずに読み込みます。
    """
    from langchain_community.document_loaders import GitLoader
    from langchain.schema import Document

    if os.path.exists(repo_path):
        print(f"Repository already exists at {repo_path}. Loading documents...")
        raw_docs = []
        for root, dirs, files in os.walk(repo_path):
            for file_name in files:
                file_path = os.path.join(root, file_name)
                if file_filter(file_path):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            raw_docs.append(Document(page_content=content, metadata={"source": file_path}))
                    except Exception as e:
                        print(f"Error reading {file_path}: {e}")
    else:
        print(f"Cloning repository from {clone_url}...")
        loader = GitLoader(
            clone_url=clone_url,
            repo_path=repo_path,
            branch=branch,
            file_filter=file_filter,
        )
        raw_docs = loader.load()
    print(f"Loaded {len(raw_docs)} documents.")
    return raw_docs

def _web_loader(url: str) -> list:
    from langchain_community.document_loaders import WebBaseLoader
    loader = WebBaseLoader(url)
    raw_docs = loader.load()
    print(f"Loaded {len(raw_docs)} documents from {url}")
    def ensure_str_content(docs):
        for doc in docs:
            if isinstance(doc.page_content, dict):
                doc.page_content = str(doc.page_content)
        return docs
    return ensure_str_content(raw_docs)

def _document_transformer(raw_docs: list, chunk_size=1000, chunk_overlap=0) -> list:
    from langchain_text_splitters import CharacterTextSplitter
    print(f"Using CharacterTextSplitter with chunk_size={chunk_size} and chunk_overlap={chunk_overlap}")
    text_splitter = CharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    docs = text_splitter.split_documents(raw_docs)
    return docs

def _embedding(model_name: str = "gemini"):
    from langchain_google_genai.embeddings import GoogleGenerativeAIEmbeddings
    from langchain_openai import OpenAIEmbeddings
    if model_name == "gemini":
        api_key = os.environ.get("GOOGLE_API_KEY")
        embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004", google_api_key=api_key)
    elif model_name == "gpt":
        embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    else:
        raise ValueError("model_nameは 'gemini' または 'gpt' のみ指定可能です")
    return embeddings

def _save(docs: list, embeddings) -> Any:
    from langchain_community.vectorstores import Chroma
    db = Chroma.from_documents(docs, embeddings)
    return db

def rag_git(clone_url: str, repo_path: str, file_filter: Callable, branch: str = "main"):
    raw_docs = _git_loader(clone_url, repo_path, file_filter, branch)
    docs = _document_transformer(raw_docs)
    embeddings_model = _embedding()
    db = _save(docs, embeddings_model)
    retriever = db.as_retriever()
    return retriever

def rag_web(url: str):
    raw_docs = _web_loader(url)
    docs = _document_transformer(raw_docs)
    embeddings_model = _embedding()
    db = _save(docs, embeddings_model)
    retriever = db.as_retriever()
    return retriever

