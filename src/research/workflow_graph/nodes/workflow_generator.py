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
import sys
import time
# ワークフロー生成のためのプロンプトを取得
def get_generate_workflow_prompt():
    return (
        "以下の条件・情報をもとに、{language}プロジェクト向けのGitHub Actionsワークフロー（YAML）を生成してください。"
        "【プロジェクト情報】"
        "- プロジェクトのローカルパス: {local_path}"
        "- ファイル構造（ツリー形式）:"
        "{file_tree}"
        "- リポジトリの情報:"
        "{repo_info}"
        "【YAML記述ルール】"
        "{yml_rules}"
        "【{language}向けベストプラクティス】"
        "{yml_best_practices}"
    )

def get_modify_after_lint_prompt():
    return (
        "以下の条件・情報をもとに、GitHub Actionsワークフロー（YAML）を修正してください。"
        "- GitHub Actionsワークフロー（YAML）の内容:"
        "{workflow_content}"
        "- Lintエラーの内容:"
        "{lint_errors}"
    )
def get_modify_after_execute_prompt():
    return (
        "以下の条件・情報をもとに、GitHub Actionsワークフロー（YAML）を修正してください。"
        "- GitHub Actionsワークフロー（YAML）の内容:"
        "{workflow_content}"
        "- 実行エラーの内容:"
        "{exec_errors}"
    )
def get_base_prompt(human_prompt: str):
    return [
        ("system", "あなたは日本のソフトウェア開発の専門家です。GitHub Actionsのワークフロー設計・運用に精通しています。"),
        ("human", human_prompt)
    ]
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
        
        # Workflow Generatorの実行制御
        if state.run_workflow_generator:
            if "github_repo_parser" == state.prev_node:
                result, best_practices =  self._generate_workflow(state)
            elif "workflow_linter" == state.prev_node:
                result = self._modify_after_lint(state)
                best_practices = state.best_practices
            elif "workflow_executor" == state.prev_node:
                result = self._modify_after_execute(state)
                best_practices = state.best_practices
            else:
                raise ValueError("不正な入力です")
        else:
            log("info", "Workflow Generatorはスキップされました")
            result = GenerateWorkflow(
                status="success",
                generated_text="",
                tokens_used=0
            )
            best_practices = state.best_practices

        github = GitHubTool()
        # ymlファイルの内容生成後、ブランチの作成、ファイルの作成、書き込みを行う
        
        # ファイルの作成
        create_file_result = github.create_file(
            local_path=state.local_path,
            relative_path=f".github/workflows/{state.yml_file_name}",
        )
        if create_file_result.status != "success":
            log("error", "YAMLファイルの作成に失敗したのでプログラムを終了します")
            sys.exit()
        
        write_to_file_result = github.write_to_file(
            local_path=state.local_path,
            relative_path=f".github/workflows/{state.yml_file_name}",
            content=result.generated_text
        )
        if write_to_file_result.status != "success":
            log("error", "YAMLファイルへの書き込みに失敗したのでプログラムを終了します")
            sys.exit()

        # 終了時間の記録とログ出力
        elapsed = time.time() - start_time
        log("info", f"WorkflowGenerator実行時間: {elapsed:.2f}秒")
        
        return {
            "generate_workflows": [result],
            "best_practices": best_practices,
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
        github = GitHubTool()

        if state.generate_best_practices:
            log("info", "ベストプラクティスの取得を開始します")
            best_practices = get_yml_best_practices(state)
        else:
            log("info", "ベストプラクティスの取得はスキップされました")
            best_practices = ""
        input = {
                "local_path": state.local_path,
                "file_tree": state.file_tree,
                "repo_info": state.repo_info,
                "language": state.language,
                "yml_rules": get_yml_rules(),
                "yml_best_practices": best_practices
            }
        
        model = llm.create_model(
            model_name=self.model_name, 
            output_model=GenerateWorkflow
        )
        prompt = ChatPromptTemplate.from_messages(get_base_prompt(get_generate_workflow_prompt()))
        chain = prompt | model
        result = chain.invoke(input)

        if result.status != "success":
            log("info", "ワークフローの生成に失敗したのでプログラムを終了します")
            sys.exit()
        log(result.status, f"LLM{self.model_name}を利用し、ワークフローを生成しました")

        create_branch_result = github.create_working_branch(
            local_path=state.local_path,
            branch_name=state.work_ref
        )
        if create_branch_result.status != "success":
            log("error", "作業用ブランチの作成に失敗したのでプログラムを終了します")
            sys.exit()

        return result, best_practices

    def _modify_after_lint(self, state: WorkflowState) -> GenerateWorkflow:
        """
        linter後の指摘をもとにワークフロー情報を修正
        lint_resultにはファイルの内容とlint結果を含む
        """
        # lint_resultをもとにworkflowを修正する処理
        lint_result = state.lint_results[-1]
        if lint_result.status == "success":
            log("info", "lint_result.statusがsuccessでWorkflowGeneratorに来るのはおかしいため、プログラムを終了します")
            sys.exit()
        
        if lint_result.status == "linter_error":
            log("error", "lint_result.statusがlinter_errorでWorkflowGeneratorに来るのはおかしいため、プログラムを終了します")
            sys.exit()

        llm = LLMTool()
        
        model = llm.create_model(
            model_name=self.model_name, 
            output_model=GenerateWorkflow
        )
        
        input = {
            "workflow_content": state.generate_workflows[-1].generated_text,
            "lint_errors": state.lint_results[-1].parsed_error
        }
        
        prompt = ChatPromptTemplate.from_messages(get_base_prompt(get_modify_after_lint_prompt()))
        chain = prompt | model
        result = chain.invoke(input)

        if result.status != "success":
            log("info", "ワークフローの修正に失敗したのでプログラムを終了します")
            sys.exit()
        log(result.status, f"LLM{self.model_name}を利用し、Lint結果に基づいてワークフローを修正しました")
        return result

    def _modify_after_execute(self, state: WorkflowState) -> GenerateWorkflow:
        """
        executor後の実行結果をもとにワークフロー情報を修正
        exec_resultにはファイルの内容と実行結果を含む
        """
        # exec_resultをもとにworkflowを修正する処理
        exec_result = state.workflow_run_results[-1]
        if exec_result.status == "success":
            log("info", "workflow_run_result.statusがsuccessでWorkflowGeneratorに来るのはおかしいため、プログラムを終了します")
            sys.exit()
        
        if exec_result.failure_category.category in ["project_error", "unknown_error"]:
            log("error", "workflow_run_result.statusがproject_errorまたはunknown_errorでWorkflowGeneratorに来るのはおかしいため、プログラムを終了します")
            sys.exit()

        llm = LLMTool()
        
        model = llm.create_model(
            model_name=self.model_name, 
            output_model=GenerateWorkflow
        )
    
        input = {
            "workflow_content": state.generate_workflows[-1].generated_text,
            "exec_errors": exec_result.parsed_error
        }

        prompt = ChatPromptTemplate.from_messages(get_base_prompt(get_modify_after_execute_prompt()))
        chain = prompt | model
        result = chain.invoke(input)

        if result.status != "success":
            log("info", "ワークフローの修正に失敗したのでプログラムを終了します")
            sys.exit()
        log(result.status, f"LLM{self.model_name}を利用し、ワークフローの実行結果に基づいてワークフローを修正しました")
        return result

