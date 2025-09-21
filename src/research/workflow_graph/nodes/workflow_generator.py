# workflow_generator.py
"""
このモジュールはワークフローの生成を担当します。
"""
from research.workflow_graph.state import GenerateWorkflow, WorkflowState
from research.log_output.log import log
from research.tools.llm import LLMTool
from research.tools.github import GitHubTool
from research.tools.rag import RAGTool
from research.prompts.yml_rule import get_yml_rules
from research.prompts.yml_best_practices import get_yml_best_practices
from langchain_core.prompts import ChatPromptTemplate
from langchain.tools import Tool
from typing import Any
import json
import sys

# ワークフロー生成のためのプロンプトを取得
def get_workflow_prompt_base():
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

# 出力形式の指示を取得(エージェント利用の際、出力形式をwith_structured_outputで指定できないため)
def get_output_format_instruction():
    return (
        "次の形式で出力してください（説明文は不要）:\n"
        "{"
        "\"status\":\"success\","
        "\"generated_text\":\"print('Hello, world!')\","
        "\"tokens_used\":42"
        "}\n"
        "statusは生成に成功したらsuccess、失敗したらfailとしてください。"
        "generated_textは生成されたテキスト、tokens_usedは使用されたトークン数をそれぞれ記載してください。"
    )

# エージェントプロンプトを取得
def get_agent_prompt():
    return [
        ("user", "あなたは日本のソフトウェア開発の専門家です。GitHub Actionsのワークフロー設計・運用に精通しています。toolとして登録されている関数やAPIも必要に応じて活用できます。"),
        ("human", get_workflow_prompt_base() + get_output_format_instruction() + "\n{agent_scratchpad}")
    ]

# 非エージェントプロンプトを取得
def get_non_agent_prompt():
    return [
        ("user", "あなたは日本のソフトウェア開発の専門家です。GitHub Actionsのワークフロー設計・運用に精通しています。"),
        ("human", get_workflow_prompt_base())
    ]
class WorkflowGenerator:
    """
    ワークフローの生成・修正を担当するクラス。
    このクラス自体はグラフのノードとしてLangGraph等で利用されることを想定。
    """
    def __init__(self, model_name: str = "gemini", agent_is : bool = False):
        self.model_name = model_name
        self.agent_is = agent_is

    def __call__(self, state: WorkflowState)-> dict[str, Any]:
        
        # Workflow Generatorの実行制御
        if state.run_workflow_generator:
            if "github_repo_parser" == state.prev_node:
                result, best_practices =  self._generate_workflow(state, self.agent_is)
            elif "workflow_linter" == state.prev_node:
                result = self._modify_after_lint(state, self.agent_is)
                best_practices = state.best_practices
            elif "workflow_executor" == state.prev_node:
                result = self._modify_after_execute(state, self.agent_is)
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

        return {
            "generate_workflows": [result],
            "best_practices": best_practices,
            "prev_node": "workflow_generator",
            "node_history": ["workflow_generator"],
            "loop_count": state.loop_count+1
        }

    def _generate_workflow(self, state:WorkflowState, agent_is: bool = False)-> GenerateWorkflow:
        """
        リポジトリ情報からワークフロー情報を生成
        """
        # repo_infoをもとにワークフロー情報を生成する処理
        llm = LLMTool()
        github = GitHubTool()

        # 推奨されない書き方ですが、一旦stateにbest_practicesを追加
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
        
        if agent_is:
            rag = RAGTool()
            tools = [
                Tool.from_function(github.read_file, name="read file", description="リポジトリの特定のファイルの内容を取得する"),
                llm.retriever_to_tool(rag.rag_tavily)
            ]

            prompt = ChatPromptTemplate.from_messages(get_agent_prompt())
        
            agent = llm.create_agent(tools=tools, prompt=prompt)
            output = agent.invoke(input)
            data = json.loads(output)
            result = GenerateWorkflow(**data)
            log(result.status, "エージェントを利用し、ワークフローを生成しました")
        else:
            model = llm.create_model(
                model_name=self.model_name, 
                output_model=GenerateWorkflow
            )
            prompt = ChatPromptTemplate.from_messages(get_non_agent_prompt())
            chain = prompt | model
            result = chain.invoke(input)
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
        result = GenerateWorkflow(
            status="success",
            generated_text="",
            tokens_used=1
        )
        return result

    def _modify_after_execute(self, state: WorkflowState) -> GenerateWorkflow:
        """
        executor後の実行結果をもとにワークフロー情報を修正
        exec_resultにはファイルの内容と実行結果を含む
        """
        # exec_resultをもとにworkflowを修正する処理
        result = GenerateWorkflow(
            status="success",
            generated_text="",
            tokens_used=1
        )
        return result

