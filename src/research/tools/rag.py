"""
RAG（Retrieval-Augmented Generation）関連の処理をまとめるモジュール。
WebやGitHubなどから情報を取得し、LLMに渡すための構造化データを生成する関数やクラスを実装。
"""
from typing import Any, Callable
import os
from langchain_community.retrievers import TavilySearchAPIRetriever
from research.log_output.log import log
from research.tools.llm import LLMTool
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

class RAGTool:
    """
    RAG（Retrieval-Augmented Generation）関連の処理をまとめたクラス。
    WebやGitHubなどから情報を取得し、LLMに渡すための構造化データを生成する。
    """
    def __init__(self, embedding_model: str = "gpt"):
        self.embedding_model = embedding_model

    def file_filter_factory(self, allow_exts=None, deny_exts=None, allow_all=False):
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
        log("info", f"ファイルフィルターを生成しました。\nallow_exts={allow_exts}, \ndeny_exts={deny_exts}, \nallow_all={allow_all}")
        return _filter

    def _git_loader(self, clone_url: str, local_path: str, file_filter: Callable, branch: str = "master") -> list:
        """
        指定したGitリポジトリからドキュメントを読み込む関数。
        すでにローカルにリポジトリが存在する場合はクローンせずに読み込みます。
        """
        from langchain_community.document_loaders import GitLoader
        from langchain.schema import Document

        if os.path.exists(local_path):
            log("info", f"リポジトリが既に存在します。{local_path}からドキュメントを読み込みます。")
            raw_docs = []
            for root, dirs, files in os.walk(local_path):
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    if file_filter(file_path):
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                raw_docs.append(Document(page_content=content, metadata={"source": file_path}))
                        except Exception as e:
                            log("error", f"Error reading {file_path}: {e}")
        else:
            log("info", f"{clone_url}からリポジトリをクローンします。")
            loader = GitLoader(
                clone_url=clone_url,
                repo_path=local_path,
                branch=branch,
                file_filter=file_filter,
            )
            raw_docs = loader.load()
        log("info", f"{len(raw_docs)}個のドキュメントを読み込みました。")
        return raw_docs

    def _web_loader(self, url: str) -> list:
        from langchain_community.document_loaders import WebBaseLoader
        loader = WebBaseLoader(url)
        raw_docs = loader.load()
        log("info", f"{len(raw_docs)}個のドキュメントを読み込みました。")
        def ensure_str_content(docs):
            for doc in docs:
                if isinstance(doc.page_content, dict):
                    doc.page_content = str(doc.page_content)
            return docs
        return ensure_str_content(raw_docs)

    def _document_transformer(self, raw_docs: list, chunk_size=1000, chunk_overlap=0) -> list:
        from langchain_text_splitters import CharacterTextSplitter
        log("info", f"CharacterTextSplitterを使用します。chunk_size={chunk_size}, chunk_overlap={chunk_overlap}")
        text_splitter = CharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        docs = text_splitter.split_documents(raw_docs)
        return docs

    def _embedding(self):
        from langchain_google_genai.embeddings import GoogleGenerativeAIEmbeddings
        from langchain_openai import OpenAIEmbeddings
        if self.embedding_model == "gemini":
            api_key = os.environ.get("GOOGLE_API_KEY")
            embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004", google_api_key=api_key)
        elif self.embedding_model == "gpt":
            embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        else:
            log("error", f"Embeddingモデル '{self.embedding_model}' はサポートされていません。")
            raise ValueError("model_nameは 'gemini' または 'gpt' のみ指定可能です")

        log("info", f"Embeddingモデル '{self.embedding_model}' を使用します。")
        return embeddings

    def _save(self, docs: list, embeddings) -> Any:
        from langchain_community.vectorstores import Chroma
        db = Chroma.from_documents(docs, embeddings)
        log("info", f"ベクトルストアに {len(docs)} 個のドキュメントを保存しました。")
        return db

    def rag_git(self, clone_url: str, local_path: str, file_filter: Callable, branch: str = "main"):
        '''
        Gitリポジトリからドキュメントを読み込み、RAG用のRetrieverを作成します。
        Return:
            Retriever
        '''
        raw_docs = self._git_loader(clone_url, local_path, file_filter, branch)
        docs = self._document_transformer(raw_docs)
        embeddings_model = self._embedding()
        db = self._save(docs, embeddings_model)
        retriever = db.as_retriever()
        log("info", f"GitHubリポジトリ{clone_url}のretrieverを作成しました。")
        return retriever

    def rag_web(self, url: str):
        '''
        Webページからドキュメントを読み込み、RAG用のRetrieverを作成します。
        Return:
            Retriever
        '''
        raw_docs = self._web_loader(url)
        docs = self._document_transformer(raw_docs)
        embeddings_model = self._embedding()
        db = self._save(docs, embeddings_model)
        retriever = db.as_retriever()
        log("info", f"{url}のretrieverを作成しました。")
        return retriever

    def rag_tavily(self, max_results: int = 5):
        '''
        Tavily APIを使用してドキュメントを検索し、RAG用のRetrieverを作成します。
        Return:
            Retriever
        '''
        retriever = TavilySearchAPIRetriever(k=max_results)
        log("info", "Tavilyのretrieverを作成しました。")
        return retriever
    
    def generate_query(error_text: str):
        
        llm = LLMTool()
        prompt = ChatPromptTemplate.from_messages([
            ("system", "あなたはGitHub Actionsのエキスパートです。"),
            ("human", f"以下のエラー内容をもとに、このエラーを解決するための検索クエリを生成してください\n【エラー内容】\n{error_text}")
        ])
        chain = prompt | llm.create_model(model_name="gpt-5-mini") | StrOutputParser()
        return chain.invoke({"error": error_text})
    
    def summarize_web_info(query: str, web_info: str):
        llm = LLMTool()
        prompt = ChatPromptTemplate.from_messages([
            ("system", "あなたはGitHub Actionsのエキスパートです。"),
            ("human", f"以下の情報をもとに{query}に関する検索結果を要約してください。Webページにそのような情報が含まれていない場合は、Noneを出力してください。\n【検索結果】\n{web_info}")
        ])
        chain = prompt | llm.create_model(model_name="gpt-5-mini") | StrOutputParser()
        return chain.invoke({"web_info": web_info, "query": query})
# poetry run python src/research/tools/rag.py
if __name__ == "__main__":
    rag = RAGTool(embedding_model="gpt")
    error = "some error log"
    query = rag.generate_query(error)
    search_docs = rag.rag_tavily.retriever.invoke(query)
    web_info = "\n\n".join([doc.page_content for doc in search_docs])
    web_summary = rag.summarize_web_info(query, web_info)

    print("【検索結果】")
    print(web_info)
    print("【要約結果】")
    print(web_summary)