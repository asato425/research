from langgraph.graph import END, StateGraph
from research.workflow_graph.state import WorkflowState
from research.workflow_graph.nodes.github_repo_parser import GitHubRepoParser
from research.workflow_graph.nodes.workflow_generator import WorkflowGenerator
from research.workflow_graph.nodes.workflow_linter import WorkflowLinter
from research.workflow_graph.nodes.workflow_executor import WorkflowExecutor
from research.workflow_graph.nodes.explanation_generator import ExplanationGenerator
from research.log_output.log import log
from langchain_core.messages import SystemMessage
import time

class WorkflowBuilder:
    def __init__(self, 
        model_name:str = "gemini",
        ):
        self.model_name = model_name
        
        def pass_func(state: WorkflowState):
            pass
        # 各種ジェネレータの初期化
        self.github_repo_parser = GitHubRepoParser(model_name=self.model_name)
        self.workflow_generator = WorkflowGenerator(model_name=self.model_name)
        self.workflow_linter = WorkflowLinter(model_name=self.model_name)
        self.workflow_executor = WorkflowExecutor()
        self.explanation_generator = ExplanationGenerator(model_name=self.model_name)
        self.pass_func = pass_func
        # グラフの作成
        self.graph = self._build()

    def _build(self) -> StateGraph:
        # グラフの初期化
        workflow = StateGraph(WorkflowState)
        # ワークフローノードの追加
        workflow.add_node("github_repo_parser", self.github_repo_parser)
        workflow.add_node("workflow_generator", self.workflow_generator)
        workflow.add_node("workflow_linter", self.workflow_linter)
        workflow.add_node("workflow_lint_success_check", self.pass_func)  # 仮の中間ノード
        workflow.add_node("workflow_executor", self.workflow_executor)
        workflow.add_node("workflow_execute_success_check", self.pass_func)  # 仮の中間ノード
        workflow.add_node("explanation_generator", self.explanation_generator)
        workflow.add_node("END", self.pass_func)  # 終了ノード

        # エントリーポイントの設定
        workflow.set_entry_point("github_repo_parser")
        
        # 条件付きエッジの追加
        workflow.add_conditional_edges(
            "github_repo_parser",
            lambda state: state.finish_is,
            {True: "END", False: "workflow_generator"},
        )
        workflow.add_conditional_edges(
            "workflow_generator",
            lambda state: state.finish_is,
            {True: "END", False: "workflow_linter"},
        )
        # workflow_linter → finish_is チェック
        workflow.add_conditional_edges(
            "workflow_linter",
            lambda state: state.finish_is,
            {True: "END", False: "workflow_lint_success_check"}  # 仮の中間ノード
        )

        # 中間ノード workflow_lint_success_check で _lint_success を判定
        workflow.add_conditional_edges(
            "workflow_lint_success_check",
            self._lint_success,
            {True: "workflow_executor", False: "workflow_generator"}
        )
        # workflow_executor → finish_is チェック
        workflow.add_conditional_edges(
            "workflow_executor",
            lambda state: state.finish_is,
            {True: "END", False: "workflow_execute_success_check"}  # 仮の中間ノード
        )
        # 中間ノード workflow_execute_success_check で _execute_success を判定
        workflow.add_conditional_edges(
            "workflow_execute_success_check",
            self._execute_success,
            {True: "explanation_generator", False: "workflow_generator"}
        )
 
        workflow.add_edge("explanation_generator", "END")
        
        workflow.add_edge("END", END)

        # グラフのコンパイル
        return workflow.compile()

    def _lint_success(self, state: WorkflowState) -> bool:
        """
            Lint成功時の処理を行うメソッド
        """
        # Lint結果が空=Lint実行をスキップしているならTrue
        if len(state.lint_results) == 0:
            log("info", "グラフの分岐：Lint実行をスキップしています")
            return True
        
        # 最新のLint結果がsuccessならTrue
        if state.lint_results[-1].status == "success":
            log("info", "グラフの分岐：Lintは成功したのでワークフローの修正は不要です")
            return True
        
        if state.lint_results[-1].status == "linter_error":
            log("warning", "グラフの分岐：Linter自体の実行に失敗しており、ワークフローの修正はできないため進みます")
            return True
        # ループ回数が上限に達しているならTrue
        if state.loop_count >= state.loop_count_max:
            log("warning", "グラフの分岐：ループ回数が上限に達したため、ワークフローの修正は行いません")
            return True

        # それ以外はFalse
        return False

    def _execute_success(self, state: WorkflowState) -> bool:
        """
            ワークフロー実行成功時の処理を行うメソッド
        """
        # ワークフロー実行結果が空=実行をスキップしているならTrue
        if len(state.workflow_run_results) == 0:
            return True

        # 最新のワークフロー実行結果がsuccessならTrue
        if state.final_status == "success":
            log("info", "グラフの分岐：ワークフローは成功したので修正は不要です")
            return True 
        if state.workflow_run_results[-1].status == "success":
            log("info", "グラフの分岐：ワークフローの実行は成功したので修正は不要です")
            return True
        
        if state.final_status == "project_errors":
            log("info", "グラフの分岐：ワークフローの実行は失敗したが、プロジェクト側の問題なのでワークフローの修正はできないため進みます")
            return True
        if state.final_status == "linter_errors":
            log("info", "グラフの分岐：ワークフローの実行は失敗したが、Linter自体の実行に失敗しており、ワークフローの修正はできないため進みます")
            return True
        if state.final_status == "unknown_errors":
            log("warning", "グラフの分岐：ワークフローの実行は失敗したが、原因が特定できず、ワークフローの修正はできないため進みます")
            return True
        
        # ループ回数が上限に達しているならTrue
        if state.loop_count >= state.loop_count_max:
            log("warning", "グラフの分岐：ループ回数が上限に達したため、ワークフローの修正は行いません")
            return True

        # それ以外はFalse
        return False


    def run(self, repo_url: str, 
            run_github_parser: bool,
            run_workflow_generator: bool,
            run_linter: bool,
            run_workflow_executer: bool,
            run_explanation_generator: bool,
            run_actionlint: bool,
            run_ghalint: bool,
            run_pinact: bool,
            generate_workflow_required_files: bool,
            generate_best_practices: bool,
            best_practices_enable_reuse: bool,
            message_file_name: str = "messages.txt",
            model_name: str = "gemini",
            temperature: float = 0.0,
            work_ref: str = "test", yml_file_name: str = "ci.yml", 
            max_required_files: int = 5, loop_count_max: int = 5, 
            best_practice_num: int = 10) -> WorkflowState:

        """ワークフローの実行を開始するメソッド
        Inputs:
            repo_url (str): リポジトリのURL

            **ノードの実行制御フラグ**
            run_github_parser (bool): github_repo_parserノードを実行するか
            run_workflow_generator (bool): workflow_generatorノードを実行するか
            run_linter (bool): lintノードを実行するか
            run_workflow_executer (bool): workflow_executerノードを実行するか
            run_explanation_generator (bool): explanation_generatorノードを実行するか

            **細かい処理の実行制御フラグ**
            run_actionlint (bool): actionlintを実行するか
            run_ghalint (bool): ghalintを実行するか
            run_pinact (bool): pinactを実行するか
            generate_workflow_required_files (bool): workflow_required_filesを生成するか
            generate_best_practices (bool): best_practicesを生成するか
            best_practices_enable_reuse (bool): ベストプラクティスを使い回すか

            **その他のパラメータ**
            work_ref (str): 作業用のブランチの名前(初期値: "test")
            yml_file_name (str): 生成されたYAMLファイルの名前(初期値: "ci.yml")
            max_required_files (int): ワークフロー生成に必要な主要ファイルの最大数(初期値: 5)
            loop_count_max (int): ワークフローのループ回数の上限(初期値: 5)
            best_practice_num (int): 言語固有のベストプラクティスの数(初期値: 10)
        Returns:
            WorkflowState: 最終的なワークフローの状態
        """
        # 初期状態の設定
        initial_state = WorkflowState(
            model_name=model_name,
            temperature=temperature,
            message_file_name=message_file_name,
            messages=[SystemMessage(content="あなたは日本のソフトウェア開発の専門家です。GitHub Actionsのワークフロー設計・運用に精通しています。")],
            repo_url=repo_url,
            run_github_parser=run_github_parser,
            run_workflow_generator=run_workflow_generator,
            run_linter=run_linter,
            run_workflow_executer=run_workflow_executer,
            run_explanation_generator=run_explanation_generator,
            run_actionlint=run_actionlint,
            run_ghalint=run_ghalint,
            run_pinact=run_pinact,
            generate_workflow_required_files=generate_workflow_required_files,
            generate_best_practices=generate_best_practices,
            best_practices_enable_reuse=best_practices_enable_reuse,
            work_ref=work_ref,
            yml_file_name=yml_file_name,
            max_required_files=max_required_files,
            loop_count_max=loop_count_max,
            best_practice_num=best_practice_num
        )
        # 開始時間の記録
        start_time = time.time()
        # グラフの実行
        final_state = self.graph.invoke(initial_state, config={
                          "recursion_limit": 100,
                      })

        # 終了時間の記録
        end_time = time.time()
        elapsed_time = end_time - start_time
        log("info", f"ワークフローの実行が完了しました。総実行時間: {elapsed_time:.2f}秒")

        # ここにLinterやExecutorの結果、ループ回数などの記録を出力することにするかも(main.pyで書いている)


        return WorkflowState(**final_state)