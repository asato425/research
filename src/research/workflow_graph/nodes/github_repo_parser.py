# github_repo_parser.py
"""
このモジュールはGitHubリポジトリ情報の取得を担当します。
"""
from research.log_output.log import log
from research.tools.github import GitHubTool
from research.tools.llm import LLMTool
from research.tools.rag import RAGTool
from research.tools.parser import ParserTool
from research.workflow_graph.state import WorkflowState, WorkflowRequiredFiles
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import time
from datetime import datetime

class GitHubRepoParser:
    """GitHubリポジトリ情報の取得を担当するクラス"""
    def __init__(self, model_name: str = "gpt-4o-mini"):
        self.model_name = model_name

    def __call__(self, state: WorkflowState):

        # 開始時間の記録
        start_time = time.time()
        # GitHubパーサーの実行制御
        if not state.run_github_parser:
            log("info", "GitHubパーサーはスキップされました")
            return {}
        
        log("info", "これからリポジトリ情報を取得します")
        github = GitHubTool()
        llm = LLMTool()
        rag = RAGTool()
        # TODO: 生成以外のLLMの処理はgpt-4o-miniの軽量モデルにする場合は引数の指定なしにする
        parser = ParserTool(model_name=state.model_name)
        

        # リポジトリ情報の取得
        repo_info_result = github.get_repository_info(state.repo_url)
        if repo_info_result.status != "success":
            log("error", "リポジトリ情報の取得に失敗したのでプログラムを終了します")
            return {
                "finish_is": True,
                "final_status": "failed to get repo info"
                }
        repo_info = repo_info_result.info

        # リポジトリのクローン
        clone_result = github.clone_repository(state.repo_url)
        if clone_result.status != "success":
            log("error", "リポジトリのクローンに失敗したのでプログラムを終了します")
            return {
                "finish_is": True,
                "final_status": "failed to clone repo"
            }
        local_path = clone_result.local_path
        
        # ブランチの作成
        create_branch_result = github.create_working_branch(
                local_path=local_path,
                branch_name=state.work_ref
            )
        if create_branch_result.status != "success":
            log("error", "作業用ブランチの作成に失敗したのでプログラムを終了します")
            return {
                "finish_is": True,
                "final_status": "failed to create branch"
            }

        #.githubフォルダの削除(存在する場合)
        folder_exists_result = github.folder_exists_in_repo(local_path=local_path, folder_name=".github")
        if folder_exists_result.status == "success":
            delete_github_folder_result = github.delete_folder(
                local_path=local_path,
                relative_path=".github"
            )
            if delete_github_folder_result.status != "success":
                log("error", ".githubフォルダの削除に失敗したのでプログラムを終了します")
                return {
                    "finish_is": True,
                    "final_status": "failed to delete .github folder"
                }
            # コミット+プッシュ
            time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            push_result = github.commit_and_push(
                local_path=local_path,
                message=time_str+"による自動コミット(.githubフォルダの削除)",
            )
            if push_result.status != "success":
                log("error", "コミットorプッシュに失敗したのでプログラムを終了します")
                return {
                    "finish_is": True,
                    "final_status": "failed to push changes"}

        # ファイルツリーの取得
        # os.walkを使った場合
        # file_tree_result = github.get_file_tree(local_path)
        # if file_tree_result.status != "success":
        #     log("error", "ファイルツリーの取得に失敗したのでプログラムを終了します")
        #     return {
        #         "finish_is": True,
        #         "final_status": "failed to get file tree"
        #     }
        # file_tree = file_tree_result.info
        # log("info", f"ファイルツリーのトークン数:{state.count_tokens(str(file_tree))}")

        # treeコマンドを使った場合、この方がトークン数が少なくなるのでこちらを利用
        file_tree_result_sub = github.get_file_tree_sub(local_path)
        if file_tree_result_sub.status != "success":
            log("error", "ファイルツリーの取得subに失敗したのでプログラムを終了します")
            return {
                "finish_is": True,
                "final_status": "failed to get file tree"
            }
        file_tree = file_tree_result_sub.info["tree"]
        log("info", f"ファイルツリーのトークン数:{state.count_tokens(file_tree)}")
        
        # トークン数が多すぎる場合は終了
        if state.count_tokens(file_tree) > 100000:
            log("error", "ファイルツリーのトークン数が100000を超えたため、実験ではトークン制限にかかる可能性があるため、プログラムを終了します")
            return {
                "finish_is": True,
                "final_status": "file tree tokens exceed 100000"
            }

        if state.generate_workflow_required_files:
            log("info", "主要ファイルの選定を開始します")
            # LLMによる主要ファイル選定のプロンプトの作成
            prompt = ChatPromptTemplate.from_messages([
                ("system", "あなたは日本のソフトウェア開発の専門家です。"),
                ("human", 
                "以下の{language}プロジェクトのGitHub Actionsワークフローのビルド、テストジョブ生成に必要な主要ファイルを最大{max_required_files}個教えてください。"
                "ファイル名は必ずファイル構造に存在するものにしてください。また.githubフォルダ内のファイルは除外してください。"
                "【プロジェクト情報】"
                "- プロジェクトのローカルパス: {local_path}"
                "- ファイル構造（ツリー形式）:"
                "{file_tree}"
                "各RequiredFileには以下の情報を含めてください。"
                " - name: ファイル名"
                " - description: ファイルの簡単な説明"
                " - path: ファイルのパス(プロジェクトのルートからの相対パス)"
                "ファイルの内容(content)は含めなくてよいです"
                )
            ])

            # チェーンの作成、TODO:必要に応じてコスト削減のためモデルを変更
            chain = prompt | llm.create_model(model_name=self.model_name, output_model=WorkflowRequiredFiles)

            # チェーンの実行
            workflow_required_files_result = chain.invoke({
                "language": repo_info["language"],
                "max_required_files": state.max_required_files,
                "local_path": local_path,
                "file_tree": file_tree,
            })
            # 主要ファイル選定の結果の確認
            if workflow_required_files_result is None or workflow_required_files_result.workflow_required_files is None:
                log("error", "主要ファイルの選定に失敗したため、プログラムを終了します")
                return {
                    "finish_is": True,
                    "final_status": "failed to generate workflow required files"
                }
                
            # 主要ファイルの内容の取得
            for required_file in workflow_required_files_result.workflow_required_files:
                log("info", f"主要ファイル: {required_file.name} - {required_file.path} - {required_file.description}")
                get_content_result = github.read_file(local_path, required_file.path)
                if get_content_result.status != "success":
                    log("error", f"主要ファイルの取得に失敗しました: {required_file.name}")
                else:
                    required_file.content = get_content_result.info["content"]
                    
                    # トークン制限対策: 50000トークンを超える場合は内容を削減
                    while state.count_tokens(required_file.content) > 50000:
                        log("warning", f"{required_file.name}の内容が50000トークンを超えているため、内容の10%を削減します")
                        required_file.content = required_file.content[:int(len(required_file.content)*0.9)]
                    
                    # 主要ファイルの内容のパース
                    file_content_parse_result = parser.file_content_parse(required_file.content)
                    if file_content_parse_result is None:
                        log("warning", f"{required_file.name}の内容のパースに失敗したため、パースする前の内容を利用します")
                        required_file.parse_content = required_file.content
                    else:
                        required_file.parse_content = file_content_parse_result
                        log("info", f"{required_file.name}の内容のパースに成功しました")
                        count = len(required_file.content) - len(required_file.parse_content)
                        required_file.reduced_length = count
                        log("info", f"パースによって削減できた文字数: {len(required_file.content) - len(required_file.parse_content)}")
                        if count >= 0:
                            log("info", f"{required_file.name}の内容が{count}文字削減されました")
                        else:
                            log("info", f"{required_file.name}の内容がパースの結果増加したので、元の内容を利用します")
                            required_file.parse_content = required_file.content

            workflow_required_files = workflow_required_files_result.workflow_required_files
        else:
            # 主要ファイルの生成をスキップ
            log("info", "主要ファイルの生成はスキップされました")
            workflow_required_files = []
        
        # RAGを利用してTavilyから情報を取得し要約
        retriever = rag.rag_tavily(max_results=3)
        query = f"GitHub Actions上で{repo_info['language']}プロジェクト'{state.repo_url}'をビルドするための手順"
        search_docs = retriever.invoke(query)
        # 検索結果をまとめてLLMで要約
        build_info = "\n\n".join([doc.page_content for doc in search_docs])
        build_prompt = ChatPromptTemplate.from_messages([
            ("system", "あなたはGitHub Actionsのエキスパートです。"),
            ("human",
                "以下の情報をもとに、GitHub Actions上でのビルド手順を5000文字以下で要約してください。Webページにそのような情報が含まれていない場合は、Noneを出力してください。\n"
                "【検索結果】\n"
                "{build_info}"
            )
        ])
        build_chain = build_prompt | llm.create_model(model_name=self.model_name) | StrOutputParser()
        build_summary = build_chain.invoke({"build_info": build_info})

        if build_summary is None or build_summary.strip() == "":
            build_summary = "なし"
            log("warning", "GitHub Actions上でのビルド手順の要約に失敗しました。")
        else:
            log("info", f"LLM{self.model_name}を利用し、GitHub Actions上でのビルド手順を要約しました")

        # 終了時間の記録とログ出力
        elapsed = time.time() - start_time
        log("info", f"GitHubRepoParser実行時間: {elapsed:.2f}秒")
        
        return {
            "execution_time": state.execution_time + elapsed,
            "local_path": local_path,
            "file_tree": file_tree,
            "repo_info": repo_info,
            "language": repo_info["language"],
            "workflow_required_files": workflow_required_files,
            "prev_node": "github_repo_parser",
            "node_history": ["github_repo_parser"],
            "final_status": "github_parse_success",
        }
