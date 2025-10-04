from pydantic import BaseModel, Field
import operator
from typing import Annotated, Optional
from typing import Any
from langchain_core.messages import BaseMessage


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
    
    def __str__(self):
        return self.summary()

    def __repr__(self):
        return f"RequiredFile={{name={self.name}, description={self.description}, path={self.path}, content={self.content}}}"


class WorkflowRequiredFiles(BaseModel):
    workflow_required_files: list[RequiredFile] = Field(
        default_factory=list, 
        description="ワークフローで必要なファイルのリスト"
    )
    def summary(self) -> str:
        return "\n".join(file.summary() for file in self.workflow_required_files)

    def __repr__(self):
        return f"WorkflowRequiredFiles={{workflow_required_files={self.workflow_required_files}}}"

class GenerateWorkflow(BaseModel):
    """
    ワークフロー生成のためのPydanticモデル。
    """
    status: str = Field(..., description="ワークフローの生成結果の状態、生成に成功したらsuccess、失敗したらfail")
    generated_text: Optional[str] = Field(None, description="生成されたテキスト")
    tokens_used: Optional[int] = Field(None, description="使用されたトークン数")

    def summary(self) -> str:
        return f"ステータス: {self.status}\n生成されたテキスト: 省略\n使用されたトークン数: {self.tokens_used}"

    def __repr__(self):
        return f"GenerateWorkflow={{status={self.status}, generated_text={self.generated_text}, tokens_used={self.tokens_used}}}"

class LintResult(BaseModel):
    """
    Lint結果を表すPydanticモデル。
    Lint結果とそのパース結果を保持する。
    """
    status: str = Field(..., description="Lint結果の状態")
    lint_name: Optional[str] = Field(None, description="使用したLinterの名前（例: actionlint, ghalint）")
    raw_error: Any = Field(None, description="Lintエラーの原文（ツール出力そのまま）")
    parsed_error: Optional[str] = Field(None, description="LLM等で要約したLintエラー")

    def summary(self) -> str:
        return f"ステータス: {self.status}\n原文: 省略\n要約: {self.parsed_error or 'なし'}"

    def __repr__(self):
        return f"LintResult={{status={self.status}, raw_error={self.raw_error}, parsed_error={self.parsed_error}}}"

class WorkflowRunResultCategory(BaseModel):
    """
    ワークフロー実行失敗のカテゴリを表すPydanticモデル。
    'yml_error' または 'project_error' のいずれかを保持する。
    """
    category: Optional[str] = Field(None, description="ワークフロー実行失敗のカテゴリ（'yml_error' または 'project_error' または 'unknown_error'）")
    reason: Optional[str] = Field(None, description="そのカテゴリに分類した理由や説明")
    
    def summary(self) -> str:
        return f"カテゴリ: {self.category or 'なし'}\n理由: {self.reason or 'なし'}"

    def __repr__(self):
        return f"WorkflowRunResultCategory={{category={self.category}, reason={self.reason}}}"
class WorkflowRunResult(BaseModel):
    """
    ワークフローの実行結果を表すPydanticモデル。
    実行結果とそのパース結果を保持する。
    """
    status: str = Field(..., description="ワークフロー実行結果の状態")
    raw_error: Optional[str] = Field(None, description="ワークフロー実行エラーの原文（ツール出力そのまま）")
    parsed_error: Optional[str] = Field(None, description="LLM等で要約したワークフロー実行エラー")
    failure_category: WorkflowRunResultCategory | None = Field(None, description="ワークフロー実行失敗のカテゴリとその理由")
    
    def summary(self) -> str:
        return f"ステータス: {self.status}\n原文: 省略\n要約: 省略\n{self.failure_category.summary() if self.failure_category else '失敗カテゴリ: なし'}"

    def __repr__(self):
        return f"WorkflowRunResult={{status={self.status}, raw_error={self.raw_error}, parsed_error={self.parsed_error}, failure_category={self.failure_category.__repr__()}}}"

        
class WorkflowState(BaseModel):
    """
    ワークフローの進行状況や各ノード間で共有する情報を保持するPydanticモデル。
    必要に応じて属性を追加・修正してください。
    """
    final_status: str | None = Field(None, description="最終的なワークフローの状態")
    model_name : str = Field("gemini", description="使用するLLMのモデル名")
    
    messages: Annotated[list[BaseMessage], operator.add] = Field(
        default_factory=list, description="LLMとの対話履歴メッセージのリスト")
    # ノードの実行制御フラグ
    run_github_parser: bool = Field(False, description="github_repo_parserノードを実行するか")
    run_workflow_generator: bool = Field(False, description="workflow_generatorノードを実行するか")
    run_linter: bool = Field(False, description="lintノードを実行するか")
    run_workflow_executer: bool = Field(False, description="workflow_executerノードを実行するか")
    run_explanation_generator: bool = Field(False, description="explanation_generatorノードを実行するか")
    
    # 細かい処理の実行制御フラグ
    run_actionlint: bool = Field(True, description="actionlintを実行するか")
    run_ghalint: bool = Field(True, description="ghalintを実行するか")
    run_pinact: bool = Field(True, description="pinactを実行するか")
    generate_workflow_required_files: bool = Field(True, description="workflow_required_filesを生成するか")
    generate_best_practices: bool = Field(True, description="best_practicesを生成するか")
    best_practices_enable_reuse: bool = Field(True, description="ベストプラクティスを使い回すか")
    # インスタンス化時に必須のフィールド(実行時はrepo_urlのみコマンドライン引数で必ず指定)
    repo_url: str = Field(..., description="リポジトリのURL")
    work_ref: str = Field(..., description="作業用のブランチの名前")
    yml_file_name: str = Field(..., description="生成されたYAMLファイルの名前")
    
    # 実験で履歴を保存するためのファイル名(本来はstateには不要だが、実験用に追加)
    message_file_name: str = Field("messages.txt", description="LLMとの対話履歴メッセージを保存するファイルの名前")
    finish_is: bool = Field(False, description="ワークフローの評価を終了するかどうかのフラグ")
    
    loop_count: int = Field(0, description="ワークフローのループ回数")
    loop_count_max: int = Field(..., description="ワークフローのループ回数の上限")
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
    generate_workflows: Annotated[list[GenerateWorkflow], operator.add] = Field(
        default_factory=list, description="生成ワークフローのリスト"
    )

    # workflow_linterで設定されるフィールド
    lint_results: Annotated[list[LintResult], operator.add] = Field(
        default_factory=list, description="Lint結果のリスト"
    )

    # workflow_executorで設定されるフィールド
    workflow_run_results: Annotated[list[WorkflowRunResult], operator.add] = Field(
        default_factory=list, description="ワークフロー実行結果のリスト"
    )

    # explanation_generatorで設定されるフィールド
    generate_explanation: Optional[str] = Field(None, description="生成されたGitHubActionsワークフローの解説文")

    def save_messages_to_file(self, filepath: str):
        with open(filepath, "w", encoding="utf-8") as f:
            for msg in self.messages:
                f.write(f"{msg.type}: {msg.content}\n")
    def __str__(self):
        return self.summary()

    def __repr__(self):
        return (
            f"WorkflowState={{model_name={self.model_name}, run_github_parser={self.run_github_parser}, run_workflow_generator={self.run_workflow_generator}, "
            f"run_linter={self.run_linter}, run_workflow_executer={self.run_workflow_executer}, run_explanation_generator={self.run_explanation_generator}, "
            f"repo_url={self.repo_url}, work_ref={self.work_ref}, yml_file_name={self.yml_file_name}, loop_count={self.loop_count}, "
            f"local_path={self.local_path}, language={self.language}, best_practices={self.best_practices}, "
            f"generate_workflows={self.generate_workflows}, lint_results={self.lint_results}, workflow_run_results={self.workflow_run_results}, "
            f"generate_explanation={self.generate_explanation}}}"
        )
    
    def summary(self) -> str:
        BLUE = "\033[34m"
        RESET = "\033[0m"
        result = (
            f"{BLUE}リポジトリURL:{RESET} {self.repo_url}\n\n"
            f"{BLUE}ループ回数:{RESET} {self.loop_count}/{self.loop_count_max}\n"
            f"{BLUE}ノード履歴:{RESET} {' -> '.join(self.node_history)}\n"
            f"{BLUE}ローカルパス:{RESET} {self.local_path}\n"
            f"{BLUE}言語:{RESET} {self.language}\n\n\n"
            #f"{BLUE}ベストプラクティス:{RESET} {self.best_practices}\n\n"
        )
        if self.generate_workflows:
            result += f"{BLUE}生成ワークフロー:{RESET}\n"
            for i, gw in enumerate(self.generate_workflows, 1):
                result += f"  ワークフロー {i}:\n    {gw.summary().replace('\n', '\n    ')}\n"
            result += "\n"
        if self.lint_results:
            result += f"{BLUE}Lint結果:{RESET}\n"
            for i, lr in enumerate(self.lint_results, 1):
                result += f"  Lint結果 {i}:\n    {lr.summary().replace('\n', '\n    ')}\n"
            result += "\n"
        if self.workflow_run_results:
            result += f"{BLUE}ワークフロー実行結果:{RESET}\n"
            for i, wrr in enumerate(self.workflow_run_results, 1):
                result += f"  ワークフロー実行結果 {i}:\n    {wrr.summary().replace('\n', '\n    ')}\n"
            result += "\n"
        return result
