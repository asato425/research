from research.log_output.log import set_log_is
from research.workflow_graph.builder import WorkflowBuilder
from research.workflow_graph.state import WorkflowState
from research.tools.github import GitHubTool
from datetime import datetime
import time
import traceback
# ノードの実行制御フラグ
RUN_GITHUB_REPO_PARSER = True # ここだけはテストでもTrueにする(generatorでFalseでもコミットプッシュなどするため)
RUN_WORKFLOW_GENERATOR = True
RUN_LINTER = True
RUN_WORKFLOW_EXECUTER = True
RUN_EXPLANATION_GENERATOR = False

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
LOOP_COUNT_MAX = 10 # ワークフローのループ回数の上限
BEST_PRACTICE_NUM = 10 # 言語固有のベストプラクティスの数

# ログ出力の設定、TrueかFalseを指定できます
SET_LOG_IS = True

# 一つのリポジトリのみワークフローエージェントを実行する関数(フォークはrepo_selector.pyで実装する、フォークされていることが前提)
def evaluate(repo_url: str, message_file_name: str, retry: int = 3, wait_sec: int = 60) -> WorkflowState | None:
    """単一リポジトリを評価する。失敗時はリトライを行う。"""

    set_log_is(SET_LOG_IS)

    for attempt in range(1, retry + 1):
        try:
            print(f"[INFO] {repo_url} の処理を開始 (試行 {attempt}/{retry})")

            # ワークフローエージェントを初期化
            agent = WorkflowBuilder(model_name=MODEL_NAME)

            # エージェントを実行して最終的な出力を取得
            final_state = agent.run(
                repo_url=repo_url,
                message_file_name=message_file_name,
                model_name=MODEL_NAME,
                run_github_parser=RUN_GITHUB_REPO_PARSER,
                run_workflow_generator=RUN_WORKFLOW_GENERATOR and RUN_GITHUB_REPO_PARSER,
                run_linter=RUN_LINTER and RUN_WORKFLOW_GENERATOR,
                run_workflow_executer=RUN_WORKFLOW_EXECUTER and RUN_WORKFLOW_GENERATOR,
                run_explanation_generator=RUN_EXPLANATION_GENERATOR and RUN_WORKFLOW_GENERATOR,
                run_actionlint=RUN_ACTIONLINT and RUN_LINTER and RUN_WORKFLOW_GENERATOR,
                run_ghalint=RUN_GHALINT and RUN_LINTER and RUN_WORKFLOW_GENERATOR,
                run_pinact=RUN_PINACT and RUN_LINTER and RUN_WORKFLOW_GENERATOR,
                generate_workflow_required_files=GENERATE_WORKFLOW_REQUIRED_FILES and RUN_GITHUB_REPO_PARSER,
                generate_best_practices=GENERATE_BEST_PRACTICES and RUN_GITHUB_REPO_PARSER,
                best_practices_enable_reuse=BEST_PRACTICES_ENABLE_REUSE,
                work_ref=WORK_REF,
                yml_file_name=YML_FILE_NAME,
                max_required_files=MAX_REQUIRED_FILES,
                loop_count_max=LOOP_COUNT_MAX,
                best_practice_num=BEST_PRACTICE_NUM,
            )

            print(f"[SUCCESS] {repo_url} の処理が完了")
            return final_state

        except Exception as e:
            print(f"[ERROR] {repo_url} でエラー発生: {e}")
            traceback.print_exc()

            if attempt < retry:
                print(f"[WAIT] {wait_sec} 秒待ってから再試行します...")
                time.sleep(wait_sec)
            else:
                print(f"[FAIL] {repo_url} はすべてのリトライで失敗しました")
                return None
    
# 複数のリポジトリに対してワークフローエージェントを実行する関数
def evaluate_multiple(repos: dict[int, str]) -> list[WorkflowState]:
    states = []
    for i, repo in repos.items():
        print(f"\n\n===== リポジトリ {i}/{len(repos)}: {repo} の評価を開始 =====")
        message_file_name = f"src/research/message_history/repo_{i}.txt"
        state = evaluate(repo, message_file_name)
        states.append(state)
        print(f"===== リポジトリ {i}/{len(repos)}: {repo} の評価が完了 =====\n\n")
        # リポジトリごとにクールダウン
        if i < len(repos):
            print("[COOLDOWN] 60秒待機中...")
            time.sleep(60)
    return states

# 複数のWorkflowStateをエクセルに保存する関数
def save_states_to_excel(states: list[WorkflowState], filename: str, language: str = "unknown"):
    import pandas as pd
    import json
    import os
    """
    WorkflowState のリストを Excel に保存する関数
    - 各 state の複雑なフィールド（list, dict）は (言語名)_(インデックス).txt にまとめて保存し、Excelにはファイル名のみ記載
    """
    # detailsにまとめるべきフィールドかどうか
    def details_is(row:str)-> bool:
        if row == "messages" or row == "repo_info" or row == "file_tree" or \
        row == "workflow_required_files" or row == "generate_workflows" or \
        row == "generate_explanation" or row == "lint_results" or \
        row == "workflow_run_results":
            return True
        return False
    rows = []
    output_dir = f"src/research/evaluation/details/{language}"
    os.makedirs(output_dir, exist_ok=True)
    for idx, state in enumerate(states, 1):
        row = {}
        details = {} 
        if state is None:
            print(f"⚠️ {filename} に保存しようとした state {idx} が None だったためスキップします")
            row["final_status"] = f"{language}{idx}state is None"
            rows.append(row)
            continue
        state_dict = state.model_dump()    
        repo_name = state.repo_url.rstrip("/").split("/")[-1]
        detail_filename = f"{repo_name +  datetime.now().strftime('%m%d')}.txt"
        for key, value in state_dict.items():
            # list や dict は details にまとめる
            if details_is(key):
                details[key] = value
                row[key] = detail_filename
            else:
                row[key] = value
        # detailsがあれば1ファイルにまとめて保存
        if details:
            detail_path = os.path.join(output_dir, detail_filename)
            with open(detail_path, "w", encoding="utf-8") as f:
                f.write(json.dumps(details, ensure_ascii=False, indent=2))
        rows.append(row)
    df = pd.DataFrame(rows)
    df.to_excel(filename, index=False, engine="openpyxl")
    print(f"✅ {filename} に {len(states)} 件の state を保存しました（詳細は {output_dir} に保存）")

def delete_remote_repo(language_repo_dict: dict[str, dict[int, str]]):
    github = GitHubTool()
    for language, repos in language_repo_dict.items():
        for i, repo_url in repos.items():
            github.delete_remote_repository(repo_url)

def main():
    # ここに評価したいリポジトリのURL(フォーク済み)を追加してください(今書いてあるのは例です)
    language_repo_dict = {
        "python": {
            1: "https://github.com/asato425/test_python"
        }
        # "python": {
        #     1: "https://github.com/asato425/public-apis",
        #     2: "https://github.com/asato425/system-design-primer",
        #     3: "https://github.com/asato425/awesome-python",
        #     4: "https://github.com/asato425/DeepSeek-V3",
        #     5: "https://github.com/asato425/whisper",
        #     6: "https://github.com/asato425/manim",
        #     7: "https://github.com/asato425/markitdown",
        #     8: "https://github.com/asato425/Deep-Live-Cam",
        #     9: "https://github.com/asato425/awesome-machine-learning",
        #     10: "https://github.com/asato425/sherlock"
        # },
        # "javascript": {
        #     1: "https://github.com/asato425/javascript",
        #     2: "https://github.com/asato425/awesome-mac",
        #     3: "https://github.com/asato425/github-readme-stats",
        #     4: "https://github.com/asato425/json-server",
        #     5: "https://github.com/asato425/33-js-concepts",
        #     6: "https://github.com/asato425/lodash",
        #     7: "https://github.com/asato425/html5-boilerplate",
        #     8: "https://github.com/asato425/drawio-desktop",
        #     9: "https://github.com/asato425/hiring-without-whiteboards",
        #     10: "https://github.com/asato425/react"
        # },
        # "java": {
        #     1: "https://github.com/asato425/GitHub-Chinese-Top-Charts",
        #     2: "https://github.com/asato425/HikariCP",
        #     3: "https://github.com/asato425/RxAndroid",
        #     4: "https://github.com/asato425/APIJSON",
        #     5: "https://github.com/asato425/analysis-ik",
        #     6: "https://github.com/asato425/JustAuth",
        #     7: "https://github.com/asato425/uCrop",
        #     8: "https://github.com/asato425/xManager",
        #     9: "https://github.com/asato425/jvm",
        #     10: "https://github.com/asato425/javapoet"
        # },
    }
    for language, repos in language_repo_dict.items():
        print(f"\n\n########## {language} のリポジトリの評価を開始 ##########")
        repositories_to_evaluate = {i: url for i, url in repos.items()}
        states = evaluate_multiple(repositories_to_evaluate)
        excel_filename = f"src/research/evaluation/{language +  datetime.now().strftime('%m%d')}.xlsx"
        save_states_to_excel(states, excel_filename, language)
        print(f"########## {language} のリポジトリの評価が完了 ##########\n\n")

    # delete_remote_repo(language_repo_dict) # フォークしたリポジトリを削除する場合はコメントアウトを外す
# 実行方法:
# poetry run python src/research/evaluation/evaluation.py
if __name__ == "__main__":
    main()
    