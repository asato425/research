# explanation_generator.py
from research.workflow_graph.state import WorkflowState
from research.log_output.log import log
from research.tools.github import GitHubTool
from research.tools.llm import LLMTool
#from research.tools.rag import RAGTool
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import time
"""
このモジュールは説明文の生成を担当します。
"""

class ExplanationGenerator:
    """説明文の生成を担当するクラス"""

    def __init__(self, model_name: str = "gemini"):
        self.model_name = model_name

        
    def __call__(self, state: WorkflowState):
        """解説文を生成するメソッド"""
        
        # 開始時間の記録
        start_time = time.time()
        
        github = GitHubTool()
        llm = LLMTool()
        #rag = RAGTool()
        if state.run_explanation_generator:
            # 1. ワークフロー解説文の生成
            model = llm.create_model(
                model_name=self.model_name,
            )

            # エラーの取得
            workflow_run_results = state.workflow_run_results[-1]
            if workflow_run_results.parsed_error.project_errors is None:
                project_errors = "プロジェクトのエラーはありません"
            else:
                project_errors = workflow_run_results.parsed_error.project_errors
            if workflow_run_results.parsed_error.yml_errors is None:
                yml_errors = "ワークフローのエラーはありません"
            else:
                yml_errors = workflow_run_results.parsed_error.yml_errors
            if workflow_run_results.parsed_error.linter_errors is None:
                linter_errors = "リントエラーはありません"
            else:
                linter_errors = workflow_run_results.parsed_error.linter_errors
            if workflow_run_results.parsed_error.unknown_errors is None:
                unknown_errors = "不明なエラーはありません"
            else:
                unknown_errors = workflow_run_results.parsed_error.unknown_errors
            prompt = ChatPromptTemplate.from_messages(
            [
                ("system", "あなたは日本のソフトウェア開発の専門家です。GitHub Actionsのワークフロー設計・運用に精通しています。"),
                ("human",
                    "以下のYAMLファイルの内容を初心者でもわかりやすく日本語で解説してください。\n"
                    "この解説はプルリクエストの説明文にそのまま使える内容にしてください。\n"
                    "説明の際には、対象となるコード部分も引用して示しながら解説してください（読者がコードと解説を行き来しなくても理解できるようにするため）。\n"
                    "エラーがある場合は最後にその内容についても解説してください。\n"
                    "出力フォーマットは以下の通りにしてください：\n"
                    "1. ワークフロー全体の目的や概要を簡潔に説明\n"
                    "2. 各ジョブ・ステップごとに以下の形式で整理\n"
                    "   - 対象コード（引用）\n"
                    "   - そのコードの役割・ポイント（箇条書き）\n"
                    "   - 使用されているアクションやコマンドの補足説明\n"
                    "3. 注意点やよくあるミスがあれば補足\n"
                    "4. エラーがある場合はその内容と対処法の解説\n"
                    "専門用語はできるだけ噛み砕いて説明してください。\n"
                    "【YAMLファイル】\n"
                    "{workflow_text}"
                    "【プロジェクト固有のエラー】\n"
                    "{project_errors}"
                    "【ymlファイルの変更で解消できると思われるエラー】\n"
                    "{yml_errors}"
                    "【Linterによるエラー】\n"
                    "{linter_errors}"
                    "【不明なエラー】\n"
                    "{unknown_errors}"
                )
            ]
)
            chain = prompt | model | StrOutputParser()
            
            input = {
                "workflow_text": state.generate_workflows[-1].generated_text, 
                "project_errors":project_errors,
                "yml_errors":yml_errors,
                "linter_errors":linter_errors,
                "unknown_errors":unknown_errors
            }
            explanation = chain.invoke(input)
            if explanation is None or explanation.strip() == "":
                explanation = "ワークフロー解説文の生成に失敗しました。"
                log("warning", "ワークフロー解説文の生成に失敗しました。")
            else:
                log("info", f"LLM{self.model_name}を利用し、ワークフローの説明文を生成しました")
            
            # 2. Dependabot security updatesの設定方法をTavilyで検索し要約
            # retriever = rag.rag_tavily(max_results=3)
            # query = "GitHub Dependabot security updates 設定方法"
            # search_docs = retriever.invoke(query)
            # # 検索結果をまとめてLLMで要約
            # dependabot_info = "\n\n".join([doc.page_content for doc in search_docs])
            # dependabot_prompt = ChatPromptTemplate.from_messages([
            #     ("system", "あなたはGitHubのセキュリティ自動化に詳しいエンジニアです。"),
            #     ("human",
            #         "以下の情報をもとに、GitHubのDependabot security updatesの設定方法とその意義を初心者にも分かりやすく日本語で簡潔にまとめてください。\n"
            #         "【検索結果】\n"
            #         "{dependabot_info}"
            #     )
            # ])
            # dependabot_chain = dependabot_prompt | model | StrOutputParser()
            # dependabot_summary = dependabot_chain.invoke({"dependabot_info": dependabot_info})

            # if dependabot_summary is None or dependabot_summary.strip() == "":
            #     dependabot_summary = "Dependabot security updatesの設定方法と意義の要約に失敗しました。"
            #     log("warning", "Dependabot security updatesの設定方法と意義の要約に失敗しました。")
            # else:
            #     log("info", f"LLM{self.model_name}を利用し、Dependabot security updatesの設定方法と意義を要約しました")

            # # ワークフロー解説文の末尾に付加
            # final_explanation = f"【GitHub Actionsワークフローの解説】\n{explanation}\n\n---\n\n【GitHub Dependabot security updatesの設定方法と意義】\n{dependabot_summary}"
            final_explanation = f"【GitHub Actionsワークフローの解説】\n{explanation}"
        else:
            log("info", "Explanation Generatorはスキップされました")
            final_explanation = "解説文は生成されませんでした"
            
        # プルリクエストの作成
        github.create_pull_request(repo_url=state.repo_url, head=state.work_ref, base=state.repo_info["default_branch"], title="GitHubワークフローファイルの作成", body=final_explanation)
        # リポジトリの削除
        github.delete_cloned_repository(state.local_path)
            
        # 終了時間の記録とログ出力
        elapsed = time.time() - start_time
        log("info", f"ExplanationGenerator実行時間: {elapsed:.2f}秒")
        return {
            "execution_time": state.execution_time + elapsed,
            "generate_explanation": final_explanation,
            "prev_node": "explanation_generator",
            "node_history": ["explanation_generator"]
        }
