from pydantic import BaseModel, Field
import operator
from typing import Annotated, Optional
from langchain_core.messages import BaseMessage
from research.log_output.log import log
import tiktoken



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
    parse_content: str | None = Field(None, description="ファイルの内容のワークフロー生成に必要な部分を抽出したもの")
    reduced_length: int = Field(0, description="パースして削減できた文字数")

    def summary(self) -> str:
        lines = [
            f"ファイル名: {self.name}",
            f"説明: {self.description}",
            f"パス: {self.path}",
            f"内容: {self.content if self.content else 'なし'}",
            f"パース内容: {self.parse_content if self.parse_content else 'なし'}"
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
    thought: Optional[str] = Field(None, description="LLMのワークフローを生成する際の思考過程")
    generated_text: Optional[str] = Field(None, description="生成されたテキスト")

    def summary(self) -> str:
        return f"ステータス: {self.status}\n生成されたテキスト: 省略"

    def __repr__(self):
        return f"GenerateWorkflow={{status={self.status}, generated_text={self.generated_text}}}"

class LintResult(BaseModel):
    """
    Lint結果を表すPydanticモデル。
    Lint結果とそのパース結果を保持する。
    """
    status: str = Field(..., description="Lint結果の状態")
    lint_name: Optional[str] = Field(None, description="使用したLinterの名前（例: actionlint, ghalint）")
    raw_error: Optional[str | list] = Field(None, description="Lintエラーの原文（ツール出力そのまま）")
    parsed_error: Optional[str | list] = Field(None, description="LLM等で要約したLintエラー")

    def summary(self) -> str:
        return f"ステータス: {self.status}\n原文: 省略\n要約: {self.parsed_error or 'なし'}"

    def __repr__(self):
        return f"LintResult={{status={self.status}, raw_error={self.raw_error}, parsed_error={self.parsed_error}}}"

class LogParseResult(BaseModel):
    linter_errors: str | None = Field(None, description="Linterによるエラーの説明、ない場合はNoneとしてください")
    yml_errors: str | None = Field(None, description="ymlファイルの変更で解消できるエラーの説明、ない場合はNoneとしてください")
    project_errors: str | None = Field(None, description="その他プロジェクト固有のエラーの説明、ない場合はNoneとしてください")
    unknown_errors: str | None = Field(None, description="不明なエラーの説明、ない場合はNoneとしてください")
    def summary(self) -> str:
        return f"Linterエラー: {self.linter_errors or 'なし'}\nYMLエラー: {self.yml_errors or 'なし'}\nプロジェクトエラー: {self.project_errors or 'なし'}\n不明なエラー: {self.unknown_errors or 'なし'}"

    def __repr__(self):
        return f"LogParseResult={{linter_errors={self.linter_errors}, yml_errors={self.yml_errors}, project_errors={self.project_errors}, unknown_errors={self.unknown_errors}}}"
class WorkflowRunResult(BaseModel):
    """
    ワークフローの実行結果を表すPydanticモデル。
    実行結果とそのパース結果を保持する。
    """
    status: str = Field(..., description="ワークフロー実行結果の状態")
    raw_error: Optional[str] = Field(None, description="ワークフロー実行エラーの原文（ツール出力そのまま）")
    parsed_error: LogParseResult | None = Field(None, description="ワークフロー実行ログをエラーの種類で分類した結果")

    def summary(self) -> str:
        return f"ステータス: {self.status}\n原文: 省略\n要約: 省略\n{self.parsed_error.summary() if self.parsed_error else '失敗カテゴリ: なし'}"

    def __repr__(self):
        return f"WorkflowRunResult={{status={self.status}, raw_error={self.raw_error}, parsed_error={self.parsed_error}}}"

class WorkflowState(BaseModel):
    """
    ワークフローの進行状況や各ノード間で共有する情報を保持するPydanticモデル。
    必要に応じて属性を追加・修正してください。
    """
    final_status: str | None = Field(None, description="最終的なワークフローの状態")
    execution_time: float = Field(0, description="実行にかかった時間（秒）")
    model_name : str = Field("gemini", description="使用するLLMのモデル名")
    temperature: float = Field(0.0, description="LLMの温度パラメータ")

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
    
    before_generated_text: Optional[str] = Field(None, description="生成され、コミット済みのテキスト")
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
    file_tree: dict | str = Field(None, description="リポジトリのファイルツリー")
    language: Optional[str] = Field(None, description="対象のプロジェクトに使用されている主要プログラミング言語")
    workflow_required_files: Annotated[list[RequiredFile], operator.add] = Field(
        default_factory=list, description="生成されたワークフローで必要なファイルのリスト"
    )
    web_summary: Optional[str] = Field(None, description="web検索によるプロジェクトのビルド、テスト手順の要約")

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

    # メッセージのトークン数が多すぎる場合に古いメッセージを削除するメソッド
    def messages_to_llm(self) -> list[BaseMessage]:
        total_tokens = self.message_token_count()
        while total_tokens > 100000:
            # 最も古い修正のHuman+AIメッセージのセットを削除して再計算
            if len(self.messages) < 5:
                log("error", f"メッセージのトークン数が10万トークンより{total_tokens}と多いのですが、これ以上削除できるメッセージがありません。処理を中断します。")
                # プロセスを中断
                raise Exception(f"メッセージのトークン数{total_tokens}が多すぎて処理を続行できません。")
            del self.messages[3:5]
            log("info", f"メッセージのトークン数が10万トークンを超えていたため、最も古い修正のHuman+AIメッセージのセットを削除しました。現在のトークン数: {total_tokens}")
            total_tokens = self.message_token_count()

        return self.messages
    def count_tokens(self,text: str) -> int:
        enc = tiktoken.encoding_for_model("gpt-5")
        return len(enc.encode(text, disallowed_special=()))
    
    def message_token_count(self) -> int:
        total_tokens = 0
        for msg in self.messages:
            total_tokens += self.count_tokens(msg.content)
        return total_tokens
    
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
