from pydantic import BaseModel, Field
import operator
from typing import Annotated, Optional


"""
ワークフロー全体の状態（State）を管理するためのPydanticモデル。
LangGraphのグラフ構築時に各ノード間で受け渡すデータ構造として利用。
"""
class RequiredFile(BaseModel):
    """ワークフローで必要なファイル"""
    name: str = Field(..., description="ワークフローで必要なファイルのファイル名")
    description: str = Field(..., description="ワークフローで必要なファイルの説明")
    path: str = Field(..., description="ワークフローで必要なファイルのパス(プロジェクトのルートからの相対パス)")
    content: str | None = Field(None, description="ワークフローで必要なファイルの内容")

    def summary(self) -> str:
        lines = [
            f"ファイル名: {self.name}",
            f"説明: {self.description}",
            f"パス: {self.path}",
            f"内容: {'あり' if self.content else 'なし'}"
        ]
        return "\n".join(lines)

class WorkflowRequiredFiles(BaseModel):
    workflow_required_files: list[RequiredFile] = Field(
        default_factory=list, 
        description="ワークフローで必要なファイルのリスト"
    )
    def summary(self) -> str:
        return "\n".join(file.summary() for file in self.workflow_required_files)

class GenerateWorkflow(BaseModel):
    """
    ワークフロー生成のためのPydanticモデル。
    """
    status: str = Field(..., description="ワークフローの生成結果の状態、生成に成功したらsuccess、失敗したらfail")
    generated_text: Optional[str] = Field(None, description="生成されたテキスト")
    tokens_used: Optional[int] = Field(None, description="使用されたトークン数")

    def summary(self) -> str:
        return f"ステータス: {self.status}\n生成されたテキスト: 省略\n使用されたトークン数: {self.tokens_used}"

class LintResult(BaseModel):
    """
    Lint結果を表すPydanticモデル。
    Lint結果とそのパース結果を保持する。
    """
    status: str = Field(..., description="Lint結果の状態")
    raw_error: Optional[str] = Field(None, description="Lintエラーの原文（ツール出力そのまま）")
    parsed_error: Optional[str] = Field(None, description="LLM等で要約したLintエラー")

    def summary(self) -> str:
        return f"ステータス: {self.status}\n原文: 省略\n要約: 省略"

class WorkflowRunResult(BaseModel):
    """
    ワークフローの実行結果を表すPydanticモデル。
    実行結果とそのパース結果を保持する。
    """
    status: str = Field(..., description="ワークフロー実行結果の状態")
    raw_error: Optional[str] = Field(None, description="ワークフロー実行エラーの原文（ツール出力そのまま）")
    parsed_error: Optional[str] = Field(None, description="LLM等で要約したワークフロー実行エラー")
    
    def summary(self) -> str:
        return f"ステータス: {self.status}\n原文: 省略\n要約: 省略"

        
class WorkflowState(BaseModel):
    """
    ワークフローの進行状況や各ノード間で共有する情報を保持するPydanticモデル。
    必要に応じて属性を追加・修正してください。
    """
    
    # ノードの実行制御フラグ
    run_github_parser: bool = Field(False, description="github_repo_parserノードを実行するか")
    run_workflow_generator: bool = Field(False, description="workflow_generatorノードを実行するか")
    run_linter: bool = Field(False, description="lintノードを実行するか")
    run_workflow_executer: bool = Field(False, description="workflow_executerノードを実行するか")
    run_explanation_generator: bool = Field(False, description="explanation_generatorノードを実行するか")
    
    # 細かい処理の実行制御フラグ
    run_actionlint: bool = Field(True, description="actionlintを実行するか")
    run_ghalint: bool = Field(True, description="ghalintを実行するか")
    generate_workflow_required_files: bool = Field(True, description="workflow_required_filesを生成するか")
    generate_best_practices: bool = Field(True, description="best_practicesを生成するか")
    
    # インスタンス化時に必須のフィールド(実行時はrepo_urlのみコマンドライン引数で必ず指定)
    repo_url: str = Field(..., description="リポジトリのURL")
    work_ref: str = Field(..., description="作業用のブランチの名前")
    yml_file_name: str = Field(..., description="生成されたYAMLファイルの名前")


    loop_count: int = Field(0, description="ワークフローのループ回数")
    loop_count_max: int = Field(..., description="ワークフローのループ回数の上限")
    lint_loop_count_max: int = Field(..., description="生成とLintのループ回数の上限")
    max_required_files: int = Field(..., description="ワークフロー生成に必要な主要ファイルの最大数")
    best_practice_num: int = Field(..., description="言語固有のベストプラクティスの数")
    
    prev_node: Optional[str] = Field(None, description="前のノードの名前")
    node_history: Annotated[list[str], operator.add] = Field(
        default_factory=list, description="グラフ上の通った順番のノードのリスト"
    )
    
    # github_repo_parserで設定されるフィールド
    local_path: Optional[str] = Field(None, description="リポジトリのクローン先のローカルパス")
    repo_info: dict = Field(None, description="リポジトリ情報")
    file_tree: dict = Field(None, description="リポジトリのファイルツリー")
    language: Optional[str] = Field(None, description="対象のプロジェクトに使用されている主要プログラミング言語")
    workflow_required_files: Annotated[list[RequiredFile], operator.add] = Field(
        default_factory=list, description="生成されたワークフローで必要なファイルのリスト"
    )

    # workflow_generatorで設定されるフィールド
    best_practices: Optional[str] = Field(None, description="言語固有のベストプラクティス")
    generate_workflows: Annotated[list[GenerateWorkflow], operator.add] = Field(
        default_factory=list, description="生成ワークフローのリスト"
    )

    # workflow_linterで設定されるフィールド
    actionlint_results: Annotated[list[LintResult], operator.add] = Field(
        default_factory=list, description="actionlint結果のリスト"
    )
    ghalint_results: Annotated[list[LintResult], operator.add] = Field(
        default_factory=list, description="ghalint結果のリスト"
    )

    # workflow_executorで設定されるフィールド
    workflow_run_results: Annotated[list[WorkflowRunResult], operator.add] = Field(
        default_factory=list, description="ワークフロー実行結果のリスト"
    )

    # explanation_generatorで設定されるフィールド
    generate_explanation: Optional[str] = Field(None, description="生成されたGitHubActionsワークフローの解説文")

    def __str__(self):
        return self.summary()

    def __repr__(self):
        return self.summary()
    
    def summary(self) -> str:
        result = "ノードの実行状況:\n" + \
                 f"GitHubパーサー: {'実行' if self.run_github_parser else 'スキップ'}\n" + \
                 f"ワークフロー生成: {'実行' if self.run_workflow_generator else 'スキップ'}\n" + \
                 f"Lint: {'実行' if self.run_linter else 'スキップ'}\n" + \
                 f"ワークフロー実行: {'実行' if self.run_workflow_executer else 'スキップ'}\n" + \
                 f"解説生成: {'実行' if self.run_explanation_generator else 'スキップ'}\n\n" + \
                 "細かい処理の実行状況:\n" + \
                 f"actionlint: {'実行' if self.run_actionlint else 'スキップ'}\n" + \
                 f"ghalint: {'実行' if self.run_ghalint else 'スキップ'}\n" + \
                 f"主要ファイル生成: {'実行' if self.generate_workflow_required_files else 'スキップ'}\n" + \
                 f"ベストプラクティス生成: {'実行' if self.generate_best_practices else 'スキップ'}\n" + \
                 "\n" + \
                 f"リポジトリURL: {self.repo_url}\n" + \
                 f"作業用ブランチ: {self.work_ref}\n" + \
                 f"YAMLファイル名: {self.yml_file_name}\n" + \
                 f"ループ回数: {self.loop_count}/{self.loop_count_max}\n" + \
                 f"ノード履歴: {' -> '.join(self.node_history)}\n" + \
                 f"ローカルパス: {self.local_path}\n" + \
                 f"言語: {self.language}\n" + \
                 f"ベストプラクティス: {self.best_practices}\n\n"

        if self.workflow_required_files:
            result += "主要ファイル:\n"
            for file in self.workflow_required_files:
                result += file.summary() + "\n\n"
        if self.generate_workflows:
            result += "生成されたワークフロー:\n"
            for workflow in self.generate_workflows:
                result += workflow.summary() + "\n\n"
        if self.actionlint_results:
            result += "actionlint結果:\n"
            for lint in self.actionlint_results:
                result += lint.summary() + "\n\n"
        if self.ghalint_results:
            result += "ghalint結果:\n"
            for lint in self.ghalint_results:
                result += lint.summary() + "\n\n"
        if self.workflow_run_results:
            result += "ワークフロー実行結果:\n"
            for run in self.workflow_run_results:
                result += run.summary() + "\n\n"
        return result
