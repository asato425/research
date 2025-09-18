from langgraph.graph import END, StateGraph
from research.workflow_graph.state import WorkflowState
from research.workflow_graph.nodes.github_repo_parser import GitHubRepoParser
from research.workflow_graph.nodes.workflow_generator import WorkflowGenerator
from research.workflow_graph.nodes.workflow_linter import WorkflowLinter
from research.workflow_graph.nodes.workflow_executor import WorkflowExecutor
from research.workflow_graph.nodes.explanation_generator import ExplanationGenerator

class WorkflowBuilder:
    def __init__(self, 
                 model_name:str = "gemini",
                 agent_is:bool = False,
                 ):
        self.model_name = model_name
        self.agent_is = agent_is
        
        # 各種ジェネレータの初期化
        self.github_repo_parser = GitHubRepoParser(model_name=self.model_name)
        self.workflow_generator = WorkflowGenerator(model_name=self.model_name, agent_is=self.agent_is)
        self.workflow_linter = WorkflowLinter(model_name=self.model_name)
        self.workflow_executor = WorkflowExecutor()
        self.explanation_generator = ExplanationGenerator(model_name=self.model_name, agent_is=self.agent_is)
        
        # グラフの作成
        self.graph = self._build()

    def _build(self) -> StateGraph:
        # グラフの初期化
        workflow = StateGraph(WorkflowState)
        # ワークフローノードの追加
        workflow.add_node("github_repo_parser", self.github_repo_parser)
        workflow.add_node("workflow_generator", self.workflow_generator)
        workflow.add_node("workflow_linter", self.workflow_linter)
        workflow.add_node("workflow_executor", self.workflow_executor)
        workflow.add_node("explanation_generator", self.explanation_generator)
        
        # エントリーポイントの設定
        workflow.set_entry_point("github_repo_parser")
        
        # ノード間のエッジの追加
        workflow.add_edge("github_repo_parser", "workflow_generator")
        workflow.add_edge("workflow_generator", "workflow_linter")
        
        # 条件付きエッジの追加
        workflow.add_conditional_edges(
            "workflow_linter",
            self._lint_success,
            {True: "workflow_executor", False: "workflow_generator"},
        )
        workflow.add_conditional_edges(
            "workflow_executor",
            self._execute_success,
            {True: "explanation_generator", False: "workflow_generator"},
        )

        # 最終ノードへのエッジの追加
        workflow.add_edge("explanation_generator", END)

        # グラフのコンパイル
        return workflow.compile()

    def _lint_success(self, state: WorkflowState) -> bool:
        """
            Lint成功時の処理を行うメソッド
        """
        return (state.actionlint_results[-1].status == "success" and state.ghalint_results[-1].status == "success") or state.loop_count >= state.lint_loop_count_max
    
    def _execute_success(self, state: WorkflowState) -> bool:
        """
            ワークフロー実行成功時の処理を行うメソッド
        """
        return state.workflow_run_results[-1].status == "success" or state.loop_count >= state.loop_count_max


    def run(self, repo_url: str, 
            run_github_parser: bool = True,
            run_workflow_generator: bool = False,
            run_linter: bool = False,
            run_workflow_executer: bool = False,
            run_explanation_generator: bool = False,
            work_ref: str = "test", yml_file_name: str = "ci.yml", 
            max_required_files: int = 5, loop_count_max: int = 5, 
            lint_loop_count_max: int = 3, best_practice_num: int = 10) -> WorkflowState:

        """ワークフローの実行を開始するメソッド
        Inputs:
            repo_url (str): リポジトリのURL
            run_github_parser (bool): github_repo_parserノードを実行するか
            run_workflow_generator (bool): workflow_generatorノードを実行するか
            run_linter (bool): lintノードを実行するか
            run_workflow_executer (bool): workflow_executerノードを実行するか
            run_explanation_generator (bool): explanation_generatorノードを実行するか
            work_ref (str): 作業用のブランチの名前(初期値: "test")
            yml_file_name (str): 生成されたYAMLファイルの名前(初期値: "ci.yml")
            max_required_files (int): ワークフロー生成に必要な主要ファイルの最大数(初期値: 5)
            loop_count_max (int): ワークフローのループ回数の上限(初期値: 5)
            lint_loop_count_max (int): 生成とLintのループ回数の上限、loop_count_maxより小さい(初期値: 3)
            best_practice_num (int): 言語固有のベストプラクティスの数(初期値: 10)
        Returns:
            WorkflowState: 最終的なワークフローの状態
        """
        # 初期状態の設定
        initial_state = WorkflowState(
            repo_url=repo_url,
            run_github_parser=run_github_parser,
            run_workflow_generator=run_workflow_generator,
            run_linter=run_linter,
            run_workflow_executer=run_workflow_executer,
            run_explanation_generator=run_explanation_generator,
            work_ref=work_ref,
            yml_file_name=yml_file_name,
            max_required_files=max_required_files,
            loop_count_max=loop_count_max,
            lint_loop_count_max=lint_loop_count_max,
            best_practice_num=best_practice_num
        )
        # グラフの実行
        final_state = self.graph.invoke(initial_state)
        
        # ここにLinterやExecutorの結果、ループ回数などの記録を出力することにするかも(main.pyで書くかも)


        return WorkflowState(**final_state)