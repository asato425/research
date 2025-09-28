"""
エージェントの設定と実行
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
    rag = RAGTool()
    llm = LLMTool()
    github = GitHubTool()
    linter = LinterTool()
    tools = [
        # GitHub関連のツール
        Tool.from_function(github.clone_repository, name="clone repository", description="リポジトリをクローンする"),
        Tool.from_function(github.get_repository_info, name="get repository info", description="リポジトリの情報を取得する"),
        Tool.from_function(github.commit_and_push, name="commit and push", description="変更をコミットしてプッシュする"),
        Tool.from_function(github.create_working_branch, name="create branch", description="新しいブランチを作成する"),
        Tool.from_function(github.create_file, name="create file", description="新しいファイルを作成する"),
        Tool.from_function(github.get_file_tree, name="get file tree", description="リポジトリのファイルツリーを取得する"),
        Tool.from_function(github.create_pull_request, name="create pull request", description="プルリクエストを作成する"),
        Tool.from_function(github.delete_file, name="delete file", description="ファイルを削除する"),
        Tool.from_function(github.delete_folder, name="delete folder", description="フォルダを削除する"),
        Tool.from_function(github.dispatch_workflow, name="dispatch workflow", description="ワークフローを実行する(対象のワークフローのonキーにworkflow_dispatchが指定されている場合のみ利用可能)"),
        Tool.from_function(github.read_file, name="read file", description="リポジトリの特定のファイルの内容を取得する"),
        Tool.from_function(github.delete_cloned_repository, name="delete cloned repository", description="クローンしたリポジトリを削除する"),
        Tool.from_function(github.get_latest_workflow_logs, name="get latest workflow logs", description="最新のワークフローのログを取得する"),
        Tool.from_function(github.write_to_file, name="write to file", description="ファイルに書き込む"),
        # Lint関連のツール
        Tool.from_function(linter.actionlint, name="run actionlint", description="GitHub ActionsのYAMLファイルに対してactionlintを実行し、Lintエラーを検出する"),
        Tool.from_function(linter.pinact, name="run pinact", description="YAMLファイルに対してpinactを実行し、コミットSHAに変換する"),
        Tool.from_function(linter.ghalint, name="run ghalint", description="YAMLファイルに対してghalintを実行し、Lintエラーを検出する"),
        # RAG関連のツール
        llm.retriever_to_tool(rag.rag_tavily),
        # プロンプト関連のツール
        Tool.from_function(get_yml_rules, name="get yml rules", description="GitHub Actionsのyml記述ルールを取得する"),
        Tool.from_function(get_yml_best_practices, name="get yml best practices", description="GitHub Actionsのプログラミング言語別のymlベストプラクティスを取得する"),
    ]
    prompt = [
        ("system", "あなたは日本のソフトウェア開発の専門家です。GitHub Actionsのワークフロー設計・運用に精通しています。"),
        ("human", "以下のリポジトリの情報をもとに、最適なGitHub Actionsワークフローを設計・生成し、リポジトリに追加してください。"
                  "必要に応じて登録されたツールを活用してください。最終的にはプルリクエストを作成してください。\nリポジトリURL: {repo_url}\n"
                  "【注意事項】\n"
                  "- get yml rules、get yml best practicesツールを利用して、YAML記述ルール、ベストプラクティスを取得し、それに従ってください。\n"
                  "- 生成したワークフローはmainブランチに直接追加せず、作業用ブランチを作成してから追加し、その後プルリクエストを作成してください。\n"
                  "- 生成したワークフローでLintエラーが検出された場合は、エラーを修正してからプルリクエストを作成してください。\n"
                  "- 生成したワークフローは実際にGitHub上で正常に動作することを確認してください。動作確認し、エラーの原因がYAMLファイルにある場合は修正してからプルリクエストを作成してください。\n"
                  "{agent_scratchpad}\n"
        )
    ]
    prompt = ChatPromptTemplate.from_messages(prompt)

    agent = llm.create_agent(
        tools=tools,
        prompt=prompt,
        model_name="gpt-4",
        max_iterations=5
    )
    input = {"repo_url": repo_url}
    output = agent.invoke(input)
    log("info", f"エージェントの実行が完了しました。出力: {str(output)}")