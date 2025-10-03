from research.log_output.log import set_log_is
from research.workflow_graph.builder import WorkflowBuilder
from research.workflow_graph.state import WorkflowState
from datetime import datetime
# ノードの実行制御フラグ
RUN_GITHUB_REPO_PARSER = True # ここだけはテストでもTrueにする(generatorでFalseでもコミットプッシュなどするため)
RUN_WORKFLOW_GENERATOR = True
RUN_LINTER = True
RUN_WORKFLOW_EXECUTER = True
RUN_EXPLANATION_GENERATOR = True

# 細かい実行制御フラグ
RUN_ACTIONLINT = True
RUN_GHALINT = True
RUN_PINACT = True # LLMの推測でこの処理を実行することはできないため、ghalintを実行するなら確実にTrueにする
GENERATE_WORKFLOW_REQUIRED_FILES = True
GENERATE_BEST_PRACTICES = True
BEST_PRACTICES_ENABLE_REUSE = True

# モデルとエージェントの設定
"""
MODEL_NAMEには"gemini-2.5-flash"、"gemini-2.5-pro"、"gpt-4"、"gpt-5"、"claude"を指定できます。
"""
MODEL_NAME = "gemini-2.5-flash"

now_str = datetime.now().strftime("%m%d_%H%M")
# コマンドライン引数のデフォルト値
WORK_REF = "work_" + now_str  # 作業用ブランチ名
YML_FILE_NAME = "ci.yml" # 生成されるYAMLファイル名
MAX_REQUIRED_FILES = 10 # ワークフロー生成に必要な主要ファイルの最大数
LOOP_COUNT_MAX = 5 # ワークフローのループ回数の上限
LINT_LOOP_COUNT_MAX = 3 # Lintのループ回数の上限
BEST_PRACTICE_NUM = 10 # 言語固有のベストプラクティスの数

# ログ出力の設定、TrueかFalseを指定できます
SET_LOG_IS = True

# 一つのリポジトリのみワークフローエージェントを実行する関数(フォークはrepo_selector.pyで実装する、フォークされていることが前提)
def evaluate(repo_url: str, message_file_name: str) -> WorkflowState:  
    set_log_is(SET_LOG_IS)

    # ワークフローエージェントを初期化
    agent = WorkflowBuilder(model_name=MODEL_NAME)
    # エージェントを実行して最終的な出力を取得
    final_state = agent.run(
        # リポジトリのURLは必須引数
        repo_url=repo_url,
        message_file_name=message_file_name,
        # LLMの設定
        model_name=MODEL_NAME,
        # ノードの実行制御フラグ
        run_github_parser=RUN_GITHUB_REPO_PARSER,
        run_workflow_generator=RUN_WORKFLOW_GENERATOR and RUN_GITHUB_REPO_PARSER,
        run_linter=RUN_LINTER and RUN_WORKFLOW_GENERATOR,
        run_workflow_executer=RUN_WORKFLOW_EXECUTER and RUN_WORKFLOW_GENERATOR,
        run_explanation_generator=RUN_EXPLANATION_GENERATOR and RUN_WORKFLOW_GENERATOR,
        # 細かい処理の実行制御フラグ
        run_actionlint=RUN_ACTIONLINT and RUN_LINTER and RUN_WORKFLOW_GENERATOR,
        run_ghalint=RUN_GHALINT and RUN_LINTER and RUN_WORKFLOW_GENERATOR,
        run_pinact=RUN_PINACT and RUN_LINTER and RUN_WORKFLOW_GENERATOR,
        generate_workflow_required_files=GENERATE_WORKFLOW_REQUIRED_FILES and RUN_GITHUB_REPO_PARSER,
        generate_best_practices=GENERATE_BEST_PRACTICES and RUN_GITHUB_REPO_PARSER,
        best_practices_enable_reuse=BEST_PRACTICES_ENABLE_REUSE,
        # その他のパラメータ
        work_ref=WORK_REF,
        yml_file_name=YML_FILE_NAME,
        max_required_files=MAX_REQUIRED_FILES,
        loop_count_max=LOOP_COUNT_MAX,
        lint_loop_count_max=LINT_LOOP_COUNT_MAX,
        best_practice_num=BEST_PRACTICE_NUM
    )

    # 最終的な出力を表示
    #print(final_state)
    
    return final_state
    
# 複数のリポジトリに対してワークフローエージェントを実行する関数
def evaluate_multiple(repos: dict[int, str]) -> list[WorkflowState]:
    states = []
    for i, repo in repos.items():
        print(f"\n\n===== リポジトリ {i}/{len(repos)}: {repo} の評価を開始 =====")
        message_file_name = f"src/research/message_history/repo_{i}.txt"
        state = evaluate(repo, message_file_name)
        states.append(state)
        print(f"===== リポジトリ {i}/{len(repos)}: {repo} の評価が完了 =====\n\n")
    return states

# 複数のWorkflowStateをエクセルに保存する関数
def save_states_to_excel(states: list[WorkflowState], filename: str):
    import pandas as pd
    import json
    """
    WorkflowState のリストを Excel に保存する関数
    - 複雑なフィールド（list, dict）は JSON 文字列に変換して保存
    """
    rows = []
    for state in states:
        state_dict = state.model_dump()
        row = {}
        for key, value in state_dict.items():
            # list や dict は JSON に変換
            if isinstance(value, (list, dict)):
                row[key] = json.dumps(value, ensure_ascii=False, indent=2)
            else:
                row[key] = value
        rows.append(row)
        #print(state)  # 各 state の summary を表示
    
    df = pd.DataFrame(rows)
    df.to_excel(filename, index=False, engine="openpyxl")
    print(f"✅ {filename} に {len(states)} 件の state を保存しました")
    
def main():
    # ここに評価したいリポジトリのURL(フォーク済み)を追加してください(今書いてあるのは例です)
    language_repo_dict = {
        "python": {
            1: "https://github.com/asato425/public-apis",
            2: "https://github.com/asato425/awesome-python",
            3: "https://github.com/asato425/DeepSeek-V3",
            4: "https://github.com/asato425/whisper",
            5: "https://github.com/asato425/Deep-Live-Cam"
        },
        # "python": {
        #     1: "https://github.com/asato425/test_python"
        # },
        # "javascript": {
        #     1:"https://github.com/axios/axios"
        # },
        # "java": {
        #     1:"https://github.com/asato425/test_java",
        # },
        # "c": {
        #     1:"https://github.com/catboost/catboost"
        # },
    }
    for language, repos in language_repo_dict.items():
        print(f"\n\n########## {language} のリポジトリの評価を開始 ##########")
        repositories_to_evaluate = {i: url for i, url in repos.items()}
        states = evaluate_multiple(repositories_to_evaluate)
        excel_filename = f"src/research/evaluation/{language}.xlsx"
        save_states_to_excel(states, excel_filename)
        print(f"########## {language} のリポジトリの評価が完了 ##########\n\n")

# 実行方法:
# poetry run python src/research/evaluation/evaluation.py
if __name__ == "__main__":
    main()