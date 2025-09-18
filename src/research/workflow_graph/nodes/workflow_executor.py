# executor.py
from research.tools.github import GitHubTool
from research.tools.parser import ParserTool
from research.workflow_graph.state import WorkflowState, WorkflowRunResult
from research.log_output.log import log
import sys
from typing import Any
"""
このモジュールはワークフローの実行を担当します。
"""


class WorkflowExecutor:
    """ワークフローの実行を担当するクラス"""

    def __call__(self, state: WorkflowState) -> dict[str, Any]:

        local_path = state.local_path
        github = GitHubTool()
        parser = ParserTool()
    

        # コミット+プッシュ
        push_result = github.commit_and_push(
            local_path=local_path,
            message="ymlファイルを追加しました"
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
        
            result = WorkflowRunResult(
                status=get_workflow_log_result.conclusion,
                raw_error=get_workflow_log_result.failure_reason,
                parsed_error=parser_result.parse_details,
            )
        else:
            log("info", "Workflow Executorはスキップされました")
            result = WorkflowRunResult(
                status="success",
                raw_error=None,
                parsed_error=None,
            )
        return {
            "workflow_run_results": [result],
            "prev_node": "workflow_executor",
            "node_history": ["workflow_executor"]
        }
