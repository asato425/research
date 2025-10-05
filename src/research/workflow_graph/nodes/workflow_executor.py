# executor.py
from research.tools.github import GitHubTool
from research.tools.llm import LLMTool
from research.tools.parser import ParserTool
from research.workflow_graph.state import WorkflowState, WorkflowRunResult, WorkflowRunResultCategory
from research.log_output.log import log
from langchain_core.prompts import ChatPromptTemplate
from typing import Any
from datetime import datetime
import time

"""
このモジュールはワークフローの実行を担当します。
"""


class WorkflowExecutor:
    """ワークフローの実行を担当するクラス"""

    def __call__(self, state: WorkflowState) -> dict[str, Any]:

        # 開始時間の記録
        start_time = time.time()
        
        local_path = state.local_path
        github = GitHubTool()
        parser = ParserTool(model_name=state.model_name)
    

        # コミット+プッシュ
        time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        push_result = github.commit_and_push(
            local_path=local_path,
            message=time_str+"による自動コミット(ymlファイルの追加)",
        )
        if push_result.status != "success":
            log("error", "コミットorプッシュに失敗したのでプログラムを終了します")
            return {
                "finish_is": True,
                "final_status": "failed to push changes"}
        # コミットSHAの取得
        commit_sha = push_result.commit_sha

        # ワークフローの実行制御
        if state.run_workflow_executer:
            # ワークフローの実行
            if len(state.generate_workflows) > 0:
                pass
                # workflow_execute_result = github.dispatch_workflow(
                #     repo_url=state.repo_url,
                #     ref=state.work_ref,
                #     workflow_id=state.yml_file_name
                #)
            else:
                log("error", "生成されたワークフローが存在しないためプログラムを終了します")
                return {
                    "finish_is": True,
                    "final_status": "no generated workflow to execute"}

            # if workflow_execute_result.status != "success":
            #     log("error", "ワークフローの実行に失敗したのでプログラムを終了します")
            #     log("error", f"詳細: {workflow_execute_result}、repo_url: {state.repo_url}, ref: {state.work_ref}, workflow_id: {state.yml_file_name}")
            #     return {"finish_is": True}
            
            get_workflow_log_result = github.get_latest_workflow_logs(
                repo_url=state.repo_url,
                commit_sha=commit_sha
            )
            if get_workflow_log_result.status != "completed":
                log("error", "ワークフローのログの取得に失敗したのでプログラムを終了します")
                log("error", f"詳細: {get_workflow_log_result}")
                return {
                    "finish_is": True,
                    "final_status": "failed to get workflow logs"}
            
            parser_result = parser.workflow_log_parse(get_workflow_log_result)
        
            category_result = None
            if get_workflow_log_result.conclusion != "success":
                llm = LLMTool()
            
                model = llm.create_model(
                    model_name=state.model_name,
                    output_model=WorkflowRunResultCategory
                )
            
                input = {
                    "workflow_content": state.generate_workflows[-1].generated_text,
                    "parse_details": parser_result.parse_details,
                }
                
                prompt = ChatPromptTemplate.from_messages([
                    ("system", "あなたは日本のソフトウェア開発の専門家です。GitHub Actionsのワークフロー設計・運用に精通しています。"),
                    ("human",
                        "以下のGitHub Actionsのワークフロー内容と実行ログの要約をもとに、"
                        "ワークフローの失敗原因を次の3つのいずれかに分類してください。失敗の原因が複数ある場合は、yml_errorとなるものを優先してください。\n"
                        "- 'yml_error': YAMLファイルの記述ミスや構文エラー、"
                        "またはワークフローで必要な依存ツールやコマンドがインストールされておらず、"
                        "そのジョブやステップの記述自体が不適切な場合。\n"
                        "- 'project_error': YAML自体は正しいが、テストやビルドなどプロジェクト本体の処理が失敗した場合。"
                        "（例: テストが落ちるなど、YAMLを修正しても解決できない場合）\n"
                        "- 'unknown_error': 上記以外や判別不能な場合。\n\n"
                        "分類は必ず1つだけ選び、分類理由や根拠を日本語で簡潔に説明してください。\n"
                        "特に、コマンドが見つからない／依存ツールが未インストールの場合は 'yml_error' とし、"
                        "その場合はインストールを追加するのではなく、"
                        "そのステップやジョブを削除するか、他の処理で代替するように修正すべきであることを明示してください。\n\n"
                        "【ワークフローの内容】\n"
                        "{workflow_content}\n"
                        "【実行ログの要約】\n"
                        "{parse_details}\n"
                    )
                ])
                chain = prompt | model
                category_result = chain.invoke(input)
                log("info", f"LLM {state.model_name}を利用し、ワークフロー実行失敗の原因を{category_result.category}として分類しました。その理由: {category_result.reason}")
                
            result = WorkflowRunResult(
                status=get_workflow_log_result.conclusion,
                raw_error=get_workflow_log_result.failure_reason,
                parsed_error=parser_result.parse_details,
                failure_category=category_result
            )
        else:
            log("info", "Workflow Executorはスキップされました")
            result = WorkflowRunResult(
                status="success",
                raw_error=None,
                parsed_error=None,
                failure_category=None
            )
        if result.failure_category:
            if result.failure_category.category == "project_error":
                final_status = "project_error"
            elif result.failure_category.category == "yml_error":
                final_status = "yml_error"
        else:
            final_status = "success"
        
        # 終了時間の記録とログ出力
        elapsed = time.time() - start_time
        log("info", f"WorkflowExecutor実行時間: {elapsed:.2f}秒")
        
        return {
            "execution_time": state.execution_time + elapsed,
            "workflow_run_results": [result],
            "prev_node": "workflow_executor",
            "node_history": ["workflow_executor"],
            "final_status": final_status
        }
