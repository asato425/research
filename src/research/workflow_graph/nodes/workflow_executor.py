# executor.py
from research.tools.github import GitHubTool
from research.tools.llm import LLMTool
from research.tools.parser import ParserTool
from research.workflow_graph.state import WorkflowState, WorkflowRunResult, WorkflowRunResultCategory
from research.log_output.log import log
from langchain_core.prompts import ChatPromptTemplate
import sys
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
            sys.exit()
        # コミットSHAの取得
        commit_sha = push_result.commit_sha

        # ワークフローの実行制御
        if state.run_workflow_executer:
            # ワークフローの実行
            if len(state.generate_workflows) > 0:
                workflow_execute_result = github.dispatch_workflow(
                    repo_url=state.repo_url,
                    ref=state.work_ref,
                    workflow_id=state.generate_workflows[-1].file_name
                )
            else:
                log("error", "生成されたワークフローが存在しないためプログラムを終了します")
                sys.exit()

            if workflow_execute_result.status != "success":
                log("error", "ワークフローの実行に失敗したのでプログラムを終了します")
                sys.exit()
            
            get_workflow_log_result = github.get_latest_workflow_logs(
                repo_url=state.repo_url,
                commit_sha=commit_sha
            )
            if get_workflow_log_result.status != "success":
                log("error", "ワークフローのログの取得に失敗したのでプログラムを終了します")
                sys.exit()
            
            parser_result = parser.workflow_log_parse(get_workflow_log_result)
        
            category_result = None
            if get_workflow_log_result.conclusion != "success":
                llm = LLMTool()
            
                model = llm.create_model(
                    model_name=self.model_name,
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
                        "ワークフローの失敗原因を次の3つのいずれかに分類してください。\n"
                        "- 'yml_error': YAMLファイルの記述ミスや構文エラーなど、ワークフロー定義自体の問題(YAMLファイルの内容を修正すれば解決可能な場合)\n"
                        "- 'project_error': YAML自体は正しいが、テストやビルドなどプロジェクト本体の処理が失敗した場合(YAMLファイルの内容を修正しても解決できない場合)\n"
                        "- 'unknown_error': 上記以外や判別不能な場合\n"
                        "分類は必ず1つだけ選び、分類理由や根拠も日本語で簡潔に説明してください。\n"
                        "【ワークフローの内容】\n"
                        "{workflow_content}\n"
                        "【実行ログの要約】\n"
                        "{parse_details}\n"
                    )
                ])
                chain = prompt | model
                category_result = chain.invoke(input)

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
        # 終了時間の記録とログ出力
        elapsed = time.time() - start_time
        log("info", f"WorkflowExecutor実行時間: {elapsed:.2f}秒")
        
        return {
            "workflow_run_results": [result],
            "prev_node": "workflow_executor",
            "node_history": ["workflow_executor"]
        }
