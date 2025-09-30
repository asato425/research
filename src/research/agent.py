"""
エージェントの設定と実行 (修正版)
"""
from research.log_output.log import log
from research.tools.llm import LLMTool
from research.tools.github import GitHubTool
from research.tools.rag import RAGTool
from research.tools.linter import LinterTool
from langchain.tools import Tool
from research.prompts.yml_rule import get_yml_rules
from research.prompts.yml_best_practices import get_yml_best_practices
from langchain_core.prompts import ChatPromptTemplate


def agent(repo_url: str):
    # --- ツール初期化 ---
    rag = RAGTool()
    llm = LLMTool()
    github = GitHubTool()
    linter = LinterTool()

    # --- ツール登録 ---
    tools = [
        Tool.from_function(github.clone_repository, name="clone_repository", description="リポジトリをクローンする"),
        Tool.from_function(github.get_repository_info, name="get_repository_info", description="リポジトリの情報を取得する"),
        Tool.from_function(github.commit_and_push, name="commit_and_push", description="変更をコミットしてプッシュする"),
        Tool.from_function(github.create_working_branch, name="create_working_branch", description="新しいブランチを作成する"),
        Tool.from_function(github.create_file, name="create_file", description="新しいファイルを作成する"),
        Tool.from_function(github.get_file_tree, name="get_file_tree", description="リポジトリのファイルツリーを取得する"),
        Tool.from_function(github.create_pull_request, name="create_pull_request", description="プルリクエストを作成する"),
        Tool.from_function(github.delete_file, name="delete_file", description="ファイルを削除する"),
        Tool.from_function(github.delete_folder, name="delete_folder", description="フォルダを削除する"),
        Tool.from_function(github.dispatch_workflow, name="dispatch_workflow", description="ワークフローを実行する"),
        Tool.from_function(github.read_file, name="read_file", description="リポジトリの特定のファイルの内容を取得する"),
        Tool.from_function(github.delete_cloned_repository, name="delete_cloned_repository", description="クローンしたリポジトリを削除する"),
        Tool.from_function(github.get_latest_workflow_logs, name="get_latest_workflow_logs", description="最新のワークフローのログを取得する"),
        Tool.from_function(github.write_to_file, name="write_to_file", description="ファイルに書き込む"),

        Tool.from_function(linter.actionlint, name="run_actionlint", description="GitHub ActionsのYAMLファイルに対してactionlintを実行し、Lintエラーを検出する"),
        Tool.from_function(linter.pinact, name="run_pinact", description="YAMLファイルに対してpinactを実行し、コミットSHAに変換する"),
        Tool.from_function(linter.ghalint, name="run_ghalint", description="YAMLファイルに対してghalintを実行し、Lintエラーを検出する"),

        llm.retriever_to_tool(
            retriever=rag.rag_tavily,
            retriever_name="RAG_tavily",
            description="Tavilyのドキュメントを検索する。質問に対して最も関連性の高いドキュメントを返す。"
        ),

        Tool.from_function(get_yml_rules, name="get_yml_rules", description="GitHub Actionsのyml記述ルールを取得する", return_direct=True),
        Tool.from_function(get_yml_best_practices, name="get_yml_best_practices", description="GitHub Actionsのプログラミング言語別のymlベストプラクティスを取得する"),
    ]

    # --- プロンプト ---
    prompt = ChatPromptTemplate.from_messages([
        ("system",
            "あなたは日本のソフトウェア開発の専門家です。GitHub Actionsのワークフロー設計・運用に精通しています。"),
        ("human", 
            "以下のリポジトリの情報をもとに、最適なGitHub Actionsワークフローを設計・生成し、リポジトリに追加してください。\n"
            "必要に応じて登録されたツールを活用してください。最終的にはプルリクエストを作成してください。\n"
            "リポジトリURL: {repo_url}\n"
            "【注意事項】\n"
            "- get_yml_rules、get_yml_best_practicesツールを利用してYAML記述ルール・ベストプラクティスを取得してください。\n"
            "- 作業用ブランチを作成してから変更を追加し、プルリクエストを作成してください。\n"
            "- 生成したワークフローでLintエラーが出た場合は修正してください。\n"
            "- プルリクエストの説明文は内容が分かるようにしてください。\n"
            "{agent_scratchpad}\n"
        )])

    # --- エージェント作成 ---
    agent = llm.create_agent(
        tools=tools,
        prompt=prompt,
        model_name="gpt-4",
        max_iterations=15
    )

    # --- 作業用ブランチ名を指定して入力 ---
    input_data = {
        "repo_url": repo_url,
        "branch_name": "add-github-actions-workflow"  # 明示的に作業ブランチを指定
    }

    # --- エージェント実行 ---
    output = agent.invoke(input_data)
    log("info", f"エージェントの実行が完了しました。出力: {str(output)}")


if __name__ == "__main__":
    repo_url = "https://github.com/asato425/test_python"
    agent(repo_url=repo_url)
