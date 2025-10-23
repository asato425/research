# executor.py
from research.tools.github import GitHubTool
from research.tools.parser import ParserTool
from research.workflow_graph.state import WorkflowState, WorkflowRunResult, LogParseResult
from research.log_output.log import log
from datetime import datetime
import time

"""
このモジュールはワークフローの実行を担当します。
"""

EXECUTE_LIMIT = 6 # ワークフローの実行待機の最大回数(5分*6回=30分)
class WorkflowExecutor:
    """ワークフローの実行を担当するクラス"""

    def __call__(self, state: WorkflowState):

        # 開始時間の記録
        start_time = time.time()
        
        local_path = state.local_path
        github = GitHubTool()
        # パースは軽量モデルで十分なのでstate.model_nameは使わない
        # TODO: パースの精度が悪かったらLLMのモデルをワークフロー生成のモデルと同じにする
        parser = ParserTool(model_name=state.model_name)
        
        # pushするymlファイルの読み込み
        read_yml_file_result = github.read_file(
            local_path=local_path,
            relative_path=".github/workflows/" + state.yml_file_name
        )
        generated_text = state.generate_workflows[-1].generated_text if len(state.generate_workflows) > 0 else None
        if read_yml_file_result is None:
            log("error", "pushするymlファイルの読み込みに失敗しました(read_file関数がNoneを返しました)")
        elif read_yml_file_result.status != "success":
            log("error", "pushするymlファイルの読み込みに失敗しました(read_file関数のstatusがsuccessではありません)")
        else:
            log("info", "pushするymlファイルの読み込みに成功しました")
            generated_text = read_yml_file_result.info["content"]

        # 前のワークフローと全く同じ内容をLLMが生成し、コミットができないことがあるのでその場合は終了する
        if len(state.generate_workflows) >= 2:
            if state.before_generated_text == generated_text:
                log("warning", "LLMが前回コミットしたワークフローと全く同じ内容を生成しており、コミットができないため、プログラムを終了します")
                return {
                    "finish_is": True,
                    "final_status": "cannot commit because the generated workflow is the same as the previous one"
                }
            else:
                log("info", "LLMが前のワークフローと異なる内容を生成しているため、コミットを続行します")

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
            # ワークフローのログ取得
            get_workflow_log_result = github.get_latest_workflow_logs(
                repo_url=state.repo_url,
                commit_sha=commit_sha
            )
            # ワークフローの完了を5分*EXECUTE_LIMIT回まで待機
            limit = 0
            while (get_workflow_log_result.status == "in_progress" 
                   or get_workflow_log_result.status == "queued" 
                   or get_workflow_log_result.status == "pending") and limit <= EXECUTE_LIMIT:
                log("warning", f"ワークフローの実行結果が{get_workflow_log_result.status}のため、ログの取得を10秒後に再試行します")
                time.sleep(10)
                get_workflow_log_result = github.get_latest_workflow_logs(
                    repo_url=state.repo_url,
                    commit_sha=commit_sha
                )
                limit += 1
                
            if get_workflow_log_result.status != "completed":
                log("error", "ワークフローのログの取得に失敗したのでプログラムを終了します")
                log("error", f"詳細: {get_workflow_log_result}")
                result = WorkflowRunResult(
                    status=get_workflow_log_result.status,
                    raw_error=None,
                    parsed_error=None,
                )
                return {
                    "finish_is": True,
                    "final_status": "failed to get workflow logs"
                }

            parser_result = parser.workflow_log_parse(get_workflow_log_result)
        
            if parser_result.yml_errors is not None:
                log("info", "yml_errorsに分類されたため、修正します")
                final_status = "yml_errors"
            elif parser_result.project_errors is not None:
                log("info", "project_errorsに分類されたため、修正しません")
                final_status = "project_errors"
            elif parser_result.linter_errors is not None:
                log("info", "linter_errorsに分類されたため、修正しません")
                final_status = "linter_errors"
            elif parser_result.unknown_errors is not None:
                log("info", "unknown_errorsに分類されたため、修正しません")
                final_status = "unknown_errors"
            else:
                log("info", "エラーが検出されなかったため、成功とみなします")
                final_status = "success"
            result = WorkflowRunResult(
                status=get_workflow_log_result.conclusion,
                raw_error=get_workflow_log_result.failure_reason,
                parsed_error=LogParseResult(
                    yml_errors=parser_result.yml_errors,
                    project_errors=parser_result.project_errors,
                    linter_errors=parser_result.linter_errors,
                    unknown_errors=parser_result.unknown_errors
                )
            )
        else:
            log("info", "Workflow Executorはスキップされました")
            result = WorkflowRunResult(
                status="success",
                raw_error=None,
                parsed_error=None,
            )
            final_status = "execution_skipped"
        
        # 終了時間の記録とログ出力
        elapsed = time.time() - start_time
        log("info", f"WorkflowExecutor実行時間: {elapsed:.2f}秒")
        
        return {
            "execution_time": state.execution_time + elapsed,
            "workflow_run_results": [result],
            "prev_node": "workflow_executor",
            "node_history": ["workflow_executor"],
            "final_status": final_status,
            "before_generated_text": generated_text
        }
