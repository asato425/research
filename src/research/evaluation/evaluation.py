from research.log_output.log import set_log_is,log
from research.workflow_graph.builder import WorkflowBuilder
from research.workflow_graph.state import WorkflowState
from research.tools.github import GitHubTool
from datetime import datetime
import time
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
MODEL_NAMEには"gemini-2.5-flash"、"gemini-2.5-pro"、"gpt-4o-mini"、"gpt-5-mini"、"gpt-5"、"claude"を指定できます。
"""
MODEL_NAME = "gemini-2.5-pro"
TEMPERATURE = 0.0

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
def evaluate(repo_url: str, message_file_name: str) -> WorkflowState | None:
    """単一リポジトリを評価する。失敗時はリトライを行う。"""

    try:
        # ワークフローエージェントを初期化
        agent = WorkflowBuilder(model_name=MODEL_NAME)

        # エージェントを実行して最終的な出力を取得
        final_state = agent.run(
            repo_url=repo_url,
            message_file_name=message_file_name,
            model_name=MODEL_NAME,
            temperature=TEMPERATURE,
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
        return final_state

    except Exception as e:
        log("error", f"{repo_url} でエラー発生したため、このリポジトリでの評価を終了します: {e}")
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
            log("info","[COOLDOWN] 1秒待機中...")
            time.sleep(1)
    return states

# 複数のWorkflowStateをエクセルに保存する関数
def save_states_to_excel(states: list[WorkflowState], language: str = "unknown"):
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
        row == "workflow_run_results" or row == "before_generated_text":
            return True
        return False
    rows = []
    output_dir = f"src/research/evaluation/details/{language + datetime.now().strftime('%m%d')}"
    os.makedirs(output_dir, exist_ok=True)
    for idx, state in enumerate(states, 1):
        row = {}
        details = {} 
        if state is None:
            print(f"⚠️ 保存しようとした state {idx} が None だったためスキップします")
            row["final_status"] = f"{language}{idx}state is None"
            rows.append(row)
            continue
        state_dict = state.model_dump()    
        repo_name = state.repo_url.rstrip("/").split("/")[-1]
        detail_filename = f"{repo_name}.txt"
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
    excel_filename = f"src/research/evaluation/{language +  datetime.now().strftime('%m%d')}.xlsx"
    df.to_excel(excel_filename, index=False, engine="openpyxl")
    print(f"✅ {excel_filename} に {len(states)} 件の state を保存しました（詳細は {output_dir} に保存）")

def delete_remote_repo(language_repo_dict: dict[str, dict[int, str]]):
    github = GitHubTool()
    for language, repos in language_repo_dict.items():
        for i, repo_url in repos.items():
            github.delete_remote_repository(repo_url)

def main():
    # 開始時間の記録
    start_time = time.time()
    set_log_is(SET_LOG_IS)
    # ここに評価したいリポジトリのURL(フォーク済み)を追加してください(今書いてあるのは例です)
    language_repo_dict = {
        # "python": {
        #     1: "https://github.com/asato425/test_python"
        # },
        "python": {
            1: "https://github.com/asato425/public-apis",
            2: "https://github.com/asato425/Python-1",
            3: "https://github.com/asato425/stable-diffusion-webui",
            4: "https://github.com/asato425/transformers",
            5: "https://github.com/asato425/youtube-dl",
            6: "https://github.com/asato425/yt-dlp",
            7: "https://github.com/asato425/langchain-1",
            8: "https://github.com/asato425/ComfyUI",
            9: "https://github.com/asato425/fastapi",
            10: "https://github.com/asato425/whisper",
        },
        "java": {
            1: "https://github.com/asato425/java-design-patterns",
            2: "https://github.com/asato425/mall",
            3: "https://github.com/asato425/Java-1",
            4: "https://github.com/asato425/guava",
            5: "https://github.com/asato425/RxJava",
            6: "https://github.com/asato425/termux-app",
            7: "https://github.com/asato425/jadx",
            8: "https://github.com/asato425/JeecgBoot",
            9: "https://github.com/asato425/MPAndroidChart",
            10: "https://github.com/asato425/NewPipe",
        },
        "javascript": {
            1: "https://github.com/asato425/javascript-algorithms",
            2: "https://github.com/asato425/javascript",
            3: "https://github.com/asato425/axios",
            4: "https://github.com/asato425/create-react-app",
            5: "https://github.com/asato425/github-readme-stats",
            6: "https://github.com/asato425/express",
            7: "https://github.com/asato425/bruno",
            8: "https://github.com/asato425/anime",
            9: "https://github.com/asato425/lodash",
            10: "https://github.com/asato425/jquery",
        },
        # "c++": {
        # },
        # "c#": {
  
        # },
        # "go": {

        # },
        # "ruby": {
        # },
        
    }
    for language, repos in language_repo_dict.items():
        print(f"\n\n########## {language} のリポジトリの評価を開始 ##########")
        repositories_to_evaluate = {i: url for i, url in repos.items()}
        states = evaluate_multiple(repositories_to_evaluate)
        save_states_to_excel(states, language)
        print(f"########## {language} のリポジトリの評価が完了 ##########\n\n")

    #delete_remote_repo(language_repo_dict) # フォークしたリポジトリを削除する場合はコメントアウトを外す
    
    # 終了時間の記録とログ出力
    elapsed = time.time() - start_time
    log("info", f"実験実行時間: {elapsed:.2f}秒")
# 実行方法:
# poetry run python src/research/evaluation/evaluation.py
if __name__ == "__main__":
    main()
    