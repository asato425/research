# workflow_generator.py
"""
このモジュールはワークフローの生成を担当します。
Lintや実行結果に基づく修正はそれまでの全てのエラー内容を引き継いで行った方がいいかも？
"""
from research.workflow_graph.state import GenerateWorkflow, WorkflowState
from research.log_output.log import log
from research.tools.llm import LLMTool
from research.tools.github import GitHubTool
from research.prompts.yml_rule import get_yml_rules
from research.prompts.yml_best_practices import get_yml_best_practices
from langchain_core.prompts import ChatPromptTemplate
from typing import Any
import time
from langchain_core.messages import HumanMessage, AIMessage

class WorkflowGenerator:
    """
    ワークフローの生成・修正を担当するクラス。
    このクラス自体はグラフのノードとしてLangGraph等で利用されることを想定。
    """
    def __init__(self, model_name: str = "gemini"):
        self.model_name = model_name

    def __call__(self, state: WorkflowState)-> dict[str, Any]:
        
        # 開始時間の記録
        start_time = time.time()
        finish_is = False
        # Workflow Generatorの実行制御
        if state.run_workflow_generator:
            if "github_repo_parser" == state.prev_node:
                result, human_prompt, finish_is =  self._generate_workflow(state)
            elif "workflow_linter" == state.prev_node:
                result, human_prompt, finish_is = self._modify_after_lint(state)
            elif "workflow_executor" == state.prev_node:
                result, human_prompt, finish_is = self._modify_after_execute(state)
            else:
                raise ValueError("不正な入力です")    
        else:
            log("info", "Workflow Generatorはスキップされました")
            result = GenerateWorkflow(
                status="success",
                generated_text="",
                tokens_used=0
            )
            human_prompt = HumanMessage(content="Workflow Generatorはスキップされました")

        if finish_is:
            log("info", "Workflow Generatorでfinish_isがTrueになったのでプログラムを終了します")
            return {
                "finish_is": True,
                "final_status": "failed to generate workflow",
                "messages": [human_prompt, AIMessage(content="生成されたGitHub Actionsワークフローの内容：\n"+result.generated_text)],
                "generate_workflows": [result],
                "prev_node": "workflow_generator",
                "node_history": ["workflow_generator"],
                "loop_count": state.loop_count+1
                }
        
        github = GitHubTool()
        # ymlファイルの内容生成後、ブランチの作成、ファイルの作成、書き込みを行う
        
        # ファイルの作成
        create_file_result = github.create_file(
            local_path=state.local_path,
            relative_path=f".github/workflows/{state.yml_file_name}",
        )
        if create_file_result.status != "success":
            log("error", "YAMLファイルの作成に失敗したのでプログラムを終了します")
            return {
                "finish_is": True,
                "final_status": "failed to create workflow file",
                "messages": [human_prompt, AIMessage(content="生成されたGitHub Actionsワークフローの内容：\n"+result.generated_text)],
                "generate_workflows": [result],
                "prev_node": "workflow_generator",
                "node_history": ["workflow_generator"],
                "loop_count": state.loop_count+1
            }
        write_to_file_result = github.write_to_file(
            local_path=state.local_path,
            relative_path=f".github/workflows/{state.yml_file_name}",
            content=result.generated_text
        )
        if write_to_file_result.status != "success":
            log("error", "YAMLファイルへの書き込みに失敗したのでプログラムを終了します")
            return {
                "finish_is": True,
                "final_status": "failed to write workflow file",
                "messages": [human_prompt, AIMessage(content="生成されたGitHub Actionsワークフローの内容：\n"+result.generated_text)],
                "generate_workflows": [result],
                "prev_node": "workflow_generator",
                "node_history": ["workflow_generator"],
                "loop_count": state.loop_count+1
            }

        # 終了時間の記録とログ出力
        elapsed = time.time() - start_time
        log("info", f"WorkflowGenerator実行時間: {elapsed:.2f}秒")
        
        return {
            "execution_time": state.execution_time + elapsed,
            "messages": [human_prompt, AIMessage(content="生成されたGitHub Actionsワークフローの内容：\n"+result.generated_text)],
            "generate_workflows": [result],
            "prev_node": "workflow_generator",
            "node_history": ["workflow_generator"],
            "loop_count": state.loop_count+1
        }

    def _generate_workflow(self, state:WorkflowState)-> GenerateWorkflow:
        """
        リポジトリ情報からワークフロー情報を生成
        """
        # repo_infoをもとにワークフロー情報を生成する処理
        llm = LLMTool()
        finish_is = False

        if state.generate_best_practices:
            log("info", "ベストプラクティスの取得を開始します")
            best_practices = get_yml_best_practices(state)
        else:
            log("info", "ベストプラクティスの取得はスキップされました")
            best_practices = ""
        
        model = llm.create_model(
            model_name=self.model_name, 
            output_model=GenerateWorkflow
        )
        # TODO: ファイル構造が必要かどうかは要検討
        human_prompt = HumanMessage(
            content=f"以下の条件・情報をもとに、{state.language}プロジェクト向けのGitHub Actionsワークフロー（YAML）を生成してください。\n"
                    "【プロジェクト情報】\n"
                    f"- プロジェクトのローカルパス: {state.local_path}\n"
                    # "- ファイル構造（ツリー形式）:\n"
                    # f"{state.file_tree}\n"
                    "- 主要ファイル:\n"
                    f"{"\n".join([f"ファイル名：{file.name}\nパス：{file.path}\n内容：{file.parse_content}\n" for file in state.workflow_required_files])}\n"
                    "- リポジトリの情報:\n"
                    f"{state.repo_info}\n"
                    "【YAML記述ルール】\n"
                    f"{get_yml_rules(state.work_ref)}\n"
                    f"【{state.language}向けベストプラクティス】\n"
                    f"{best_practices}"
        )
        prompt = ChatPromptTemplate.from_messages(state.messages + [human_prompt])
        chain = prompt | model
        result = chain.invoke({})
        
        if result is None or result.generated_text is None:
            log("error", "ワークフローの生成結果がNoneなのでプログラムを終了します")
            finish_is = True
        elif result.status != "success":
            log("info", "ワークフローの生成に失敗したのでプログラムを終了します")
            finish_is = True
        else:
            log(result.status, f"LLM{self.model_name}を利用し、ワークフローを生成しました")

        return result, human_prompt, finish_is

    def _modify_after_lint(self, state: WorkflowState) -> GenerateWorkflow:
        """
        linter後の指摘をもとにワークフロー情報を修正
        lint_resultにはファイルの内容とlint結果を含む
        """
        finish_is = False
        # lint_resultをもとにworkflowを修正する処理
        lint_result = state.lint_results[-1]
        if lint_result is None:
            log("error", "lint_resultがNoneでWorkflowGeneratorに修正しに来ているため、プログラムを終了します")
            finish_is = True
            return None, None, finish_is
        elif lint_result.status == "success":
            log("info", "lint_result.statusがsuccessでWorkflowGeneratorに来るのはおかしいため、プログラムを終了します")
            finish_is = True
            return None, None, finish_is
        elif lint_result.status == "linter_error":
            log("error", "lint_result.statusがlinter_errorでWorkflowGeneratorに来るのはおかしいため、プログラムを終了します")
            finish_is = True
            return None, None, finish_is

        llm = LLMTool()
        
        model = llm.create_model(
            model_name=self.model_name, 
            output_model=GenerateWorkflow
        )
        
        human_prompt = HumanMessage(
            content="以下の条件・情報をもとに、GitHub Actionsワークフロー（YAML）を修正してください。"
                    "これまでのワークフロー生成、エラーの内容の履歴も踏まえ、同様のエラーが複数回確認できるかつビルドやテストに直接関連しない場合(Lintや最適化など)はコメントアウトすることによって対応してください。その際にコメントアウトする理由をコメントとして残してください。\n"
                    "- Lintエラーの内容:\n"
                    f"{lint_result.parsed_error}\n"
                    "注意点：今までに生成されたワークフローと全く同じ内容は生成しないでください\n"
        )
        prompt = ChatPromptTemplate.from_messages(state.messages + [human_prompt])
        chain = prompt | model
        result = chain.invoke({})

        if result is None:
            log("error", "ワークフローのLintエラー修正結果がNoneなのでプログラムを終了します")
            finish_is = True
        elif result.status != "success":
            log("info", "ワークフローの修正に失敗したのでプログラムを終了します")
            finish_is = True
        else:
            log(result.status, f"LLM{self.model_name}を利用し、Lint結果に基づいてワークフローを修正しました")
        return result, human_prompt, finish_is

    def _modify_after_execute(self, state: WorkflowState) -> GenerateWorkflow:
        """
        executor後の実行結果をもとにワークフロー情報を修正
        exec_resultにはファイルの内容と実行結果を含む
        """
        finish_is = False
        # exec_resultをもとにworkflowを修正する処理
        exec_result = state.workflow_run_results[-1]
        if exec_result is None:
            log("error", "exec_resultがNoneでWorkflowGeneratorに修正しに来ているため、プログラムを終了します")
            finish_is = True
            return None, None, finish_is
        elif exec_result.status == "success":
            log("info", "workflow_run_result.statusがsuccessでWorkflowGeneratorに来るのはおかしいため、プログラムを終了します")
            finish_is = True
            return None, None, finish_is
        elif exec_result.parsed_error.yml_errors is None:
            log("error", "workflow_run_result.parsed_error.yml_errorsがNoneでWorkflowGeneratorに来るのはおかしいため、プログラムを終了します")
            finish_is = True
            return None, None, finish_is

        llm = LLMTool()
        
        model = llm.create_model(
            model_name=self.model_name, 
            output_model=GenerateWorkflow
        )

        human_prompt = HumanMessage(
            content="以下の条件・情報をもとに、GitHub Actionsワークフロー（YAML）を修正してください。"
                    "これまでのワークフロー生成、エラーの内容の履歴も踏まえ、同様のエラーが複数回確認できるかつビルドやテストに直接関連しない場合(Lintや最適化など)はコメントアウトすることによって対応してください。その際にコメントアウトする理由をコメントとして残してください。\n"
                    "- 実行エラーの内容:\n"
                    f"{exec_result.parsed_error.yml_errors}\n"
                    "注意点：今までの生成されたワークフローと全く同じ内容は生成しないでください\n"
        )
        prompt = ChatPromptTemplate.from_messages(state.messages + [human_prompt])
        chain = prompt | model
        result = chain.invoke({})
        if result is None:
            log("error", "ワークフローの実行エラー修正結果がNoneなのでプログラムを終了します")
            finish_is = True
        elif result.status != "success":
            log("info", "ワークフローの修正に失敗したのでプログラムを終了します")
            finish_is = True
        else:
            log(result.status, f"LLM{self.model_name}を利用し、ワークフローの実行結果に基づいてワークフローを修正しました")
        return result, human_prompt, finish_is

