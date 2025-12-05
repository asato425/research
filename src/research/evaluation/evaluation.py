from research.log_output.log import set_log_is,log
from research.workflow_graph.builder import WorkflowBuilder
from research.workflow_graph.state import WorkflowState
from research.tools.github import GitHubTool
#from datetime import datetime
import time
import tempfile
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
MODEL_NAMEには"gemini-2.5-flash"、"gemini-2.5-pro"、"gpt-4o-mini"、"gpt-5-mini"、"gpt-5"、"claude"を指定できます。
"""
MODEL_NAME = "gpt-5-mini"
TEMPERATURE = 0.0

#now_str = datetime.now().strftime("%m%d_%H%M")
# コマンドライン引数のデフォルト値
#WORK_REF = "work_" + now_str  # 作業用ブランチ名
WORK_REF = "work_gpt-5-mini"  # 作業用ブランチ名
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
        

def _unique_path(path: str) -> str:
    # ...existing code or reuse helper if already present...
    import os
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    i = 1
    while True:
        candidate = f"{base}_{i}{ext}"
        if not os.path.exists(candidate):
            return candidate
        i += 1
        
def save_state_to_excel(state: WorkflowState, language: str = "unknown"):
    """
    単一の WorkflowState を即時に Excel に追記して保存する。
    details 部分は従来通り details フォルダに1ファイルとして保存する。
    原子操作のため一時ファイルを書いてから置換します。
    """
    import pandas as pd
    import json
    import os

    def details_is(row: str) -> bool:
        return row in {
            "messages",
            "repo_info",
            "file_tree",
            "workflow_required_files",
            "generate_workflows",
            "generate_explanation",
            "lint_results",
            "workflow_run_results",
            "before_generated_text",
        }
    def condition_experiment() -> str:
        result = "_loop_20"
        if not RUN_LINTER:
            result += "_no_linter"
        if not RUN_WORKFLOW_EXECUTER:
            result += "_no_executer"
        if not GENERATE_WORKFLOW_REQUIRED_FILES:
            result += "_no_reqfiles"
        if not GENERATE_BEST_PRACTICES:
            result += "_no_bestpractices"
        return result

    safe_model = MODEL_NAME.replace(".", "_")
    safe_temp = str(TEMPERATURE).replace(".", "_")
    output_dir = f"src/research/evaluation/details/rq5_{language}{safe_model}{safe_temp}{condition_experiment()}/"
    os.makedirs(output_dir, exist_ok=True)

    # state が None の場合は何もしない
    if state is None:
        return

    state_dict = state.model_dump()
    repo_name = state.repo_url.rstrip("/").split("/")[-1]
    safe_repo = repo_name.replace(".", "_")
    detail_filename = f"{safe_repo}_{safe_model}_{safe_temp}.txt"

    # row と details を作る
    row = {}
    details = {}
    for key, value in state_dict.items():
        if details_is(key):
            details[key] = value
            row[key] = detail_filename
        else:
            row[key] = value

    # details を保存（重複避け）
    if details:
        detail_path = os.path.join(output_dir, detail_filename)
        detail_path = _unique_path(detail_path)
        with open(detail_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(details, ensure_ascii=False, indent=2))

    # Excel に追記（既存読み込み -> 結合 -> 一時ファイルに書いて置換）
    excel_filename = f"src/research/evaluation/rq5_{language + safe_model + safe_temp + condition_experiment()}.xlsx"
    new_df = pd.DataFrame([row])
    try:
        if os.path.exists(excel_filename):
            try:
                existing_df = pd.read_excel(excel_filename, engine="openpyxl")
                combined = pd.concat([existing_df, new_df], ignore_index=True)
            except Exception:
                combined = new_df
        else:
            combined = new_df
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".xlsx")
        os.close(tmp_fd)
        combined.to_excel(tmp_path, index=False, engine="openpyxl")
        os.replace(tmp_path, excel_filename)
    except Exception as ex:
        # 保存に失敗しても評価を止めない。ログに出力
        log("error", f"failed to save state for {state.repo_url}: {ex}")

def evaluate_multiple(repos: dict[int, str], language: str) -> list[WorkflowState]:
    states = []
    # 必要な評価結果数
    results_needed = 16
    for i, repo in repos.items():
        print(f"\n\n===== リポジトリ {i}/{len(repos)}: {repo} の評価を開始 =====")
        message_file_name = f"src/research/message_history/repo_{i}.txt"
        state = evaluate(repo, message_file_name)
        print(f"===== リポジトリ {i}/{len(repos)}: {repo} の評価が完了 =====\n\n")
        if state is not None:
            # ここで逐次保存する
            try:
                save_state_to_excel(state, language=language)  # 必要なら言語を渡す
            except Exception as e:
                log("error", f"save_state_to_excel でエラー: {e}")
            states.append(state)
            if state.final_status == "success" or state.final_status == "yml_errors" or state.final_status == "project_errors":
                results_needed -= 1
                if results_needed <= 0:
                    print("✅ 必要な評価結果数に達したため、評価を終了します")
                    break
            print(f"✅ 現在取得済みの評価結果数: {15-results_needed} 件、残り取得が必要な件数: {results_needed} 件")
        # クールダウン
        if i < len(repos):
            log("info","[COOLDOWN] 10秒待機中...")
            time.sleep(10)
    return states

def delete_remote_repo(language_repo_dict: dict[str, dict[int, str]]):
    github = GitHubTool()
    for language, repos in language_repo_dict.items():
        for i, repo_url in repos.items():
            github.delete_remote_repository(repo_url)

def yml_file_count_words(repo_url: str, ref_list: list[str]) -> list[int]:
    github = GitHubTool()
    clone_result = github.clone_repository(repo_url)
    if clone_result.status != "success":
        log("error", "リポジトリのクローンに失敗したのでプログラムを終了します")
        return 0
    local_path = clone_result.local_path
    
    result = []
    for ref in ref_list:
        # ブランチの作成
        create_branch_result = github.create_working_branch(
                local_path=local_path,
                branch_name=ref
            )
        if create_branch_result.status != "exists":
            continue
        word_count = github.count_words_in_file(
            local_path=local_path,
            relative_path=".github/workflows/ci.yml",
        ).info["word_count"]
        result.append(word_count)
    return result
def main():
    # 開始時間の記録
    start_time = time.time()
    set_log_is(SET_LOG_IS)
    # ここに評価したいリポジトリのURL(フォーク済み)を追加してください(今書いてあるのは例です)
    # TODO:実験の流れ
    # 1. repo_selector.pyでリポジトリを選定してフォーク
    # 2. フォークしたリポジトリのURLをここに追加
    # 3. 全てのモジュールをtrueにしてevaluation.pyを実行し、successまたはyml_errorsで終了したリポジトリを各言語15個ずつ集める
    language_repo_dict = {
        # "python": {
        #     1: "https://github.com/asato425/test_python"
        # },
        "python": {
            1: "https://github.com/asato425/public-apis",
            2: "https://github.com/asato425/Python-1",
            3: "https://github.com/asato425/stable-diffusion-webui", 
            #4: "https://github.com/asato425/transformers", ワークフロー実行の待機でタイムアウト
            5: "https://github.com/asato425/youtube-dl",
            6: "https://github.com/asato425/yt-dlp",
            7: "https://github.com/asato425/langchain-1",
            8: "https://github.com/asato425/ComfyUI",
            9: "https://github.com/asato425/fastapi",
            #10: "https://github.com/asato425/whisper", # ワークフロー実行の待機でタイムアウト
            #11: "https://github.com/asato425/django", #ファイル構造のトークン制限
            12: "https://github.com/asato425/markitdown",
            #13: "https://github.com/asato425/core",# ファイル構造のトークン制限
            14: "https://github.com/asato425/models",
            15: "https://github.com/asato425/browser-use",
            16: "https://github.com/asato425/flask",
            17: "https://github.com/asato425/sherlock",
            #18: "https://github.com/asato425/gpt_academic",# push　失敗
            19: "https://github.com/asato425/gpt4free",
            20: "https://github.com/asato425/scikit-learn",
        },
        "java": {
            1: "https://github.com/asato425/java-design-patterns",
            #2: "https://github.com/asato425/spring-boot", # ファイル構造のトークン制限
            #3: "https://github.com/asato425/elasticsearch", # ファイル構造のトークン制限
            4: "https://github.com/asato425/Java-1",
            #5: "https://github.com/asato425/spring-framework",# ファイル構造のトークン制限
            6: "https://github.com/asato425/guava",
            7: "https://github.com/asato425/RxJava",
            8: "https://github.com/asato425/termux-app",
            #9: "https://github.com/asato425/dbeaver", # ファイル構造のトークン制限
             10: "https://github.com/asato425/jadx",
            #11: "https://github.com/asato425/dubbo", # ファイル構造のトークン制限
            12: "https://github.com/asato425/NewPipe",
            13: "https://github.com/asato425/glide",
            14: "https://github.com/asato425/netty", # ログにoutofmemoryエラーが出るがこれはエラーではないが、今の実装ではエラーと認識してしまうため無理
            15: "https://github.com/asato425/easyexcel",
            #16: "https://github.com/asato425/zxing", # unknown errorsによる失敗
            17: "https://github.com/asato425/nacos",
            18: "https://github.com/asato425/WxJava",
            #19: "https://github.com/asato425/kafka", # ファイル構造のトークン制限
            #20: "https://github.com/asato425/keycloak", # ファイル構造のトークン制限
            21: "https://github.com/asato425/xxl-job",
            22: "https://github.com/asato425/canal",
            23: "https://github.com/asato425/spring-cloud-alibaba",
        },
        "javascript": {
            1: "https://github.com/asato425/javascript-algorithms",
            2: "https://github.com/asato425/javascript",
            3: "https://github.com/asato425/axios",
            #4: "https://github.com/asato425/create-react-app", # ワークフロー実行の待機でタイムアウト
            5: "https://github.com/asato425/github-readme-stats",
            6: "https://github.com/asato425/express",
            #8: "https://github.com/asato425/webpack", # ファイル構造のトークン制限
            9: "https://github.com/asato425/lodash",
            10: "https://github.com/asato425/uBlock",
            11: "https://github.com/asato425/jquery",
            12: "https://github.com/asato425/html5-boilerplate",
            #13: "https://github.com/asato425/prettier", # ファイル構造のトークン制限
            14: "https://github.com/asato425/anything-llm",
            15: "https://github.com/asato425/dayjs",
            16: "https://github.com/asato425/serverless", #これはプロジェクト側の問題なのでエラー回避不能
            17: "https://github.com/asato425/htmx",
            18: "https://github.com/asato425/meteor",
            #19: "https://github.com/asato425/parcel", # ファイル構造のトークン制限
            20: "https://github.com/asato425/Leaflet",
        },
        
    }
    result = {}
    for language, repos in language_repo_dict.items():
        # print(f"\n\n########## {language} のリポジトリの評価を開始 ##########")
        # repositories_to_evaluate = {i: url for i, url in repos.items()}
        # #states = evaluate_multiple(repositories_to_evaluate, language)
        # evaluate_multiple(repositories_to_evaluate, language)
        # print(f"########## {language} のリポジトリの評価が完了 ##########\n\n")
        result[language] = []
        repos_list = [url for i, url in repos.items()]
        branch_list = ["work_gpt-5-mini", "work_gpt-5-mini_t_0", "work_gpt-5-mini_t_05", "work_gpt-5-mini_t_5", "work_gpt-5-mini_t_1"]
        for repo_url in repos_list:
            word_count_list = yml_file_count_words(repo_url, branch_list)
            result[language].append(word_count_list)
    #delete_remote_repo(language_repo_dict) # フォークしたリポジトリを削除する場合はコメントアウトを外す
        for language, counts in result.items():
            log("info", f"{language} リポジトリの {YML_FILE_NAME} の単語数一覧: {counts}")
    # 終了時間の記録とログ出力
    elapsed = time.time() - start_time
    log("info", f"実験実行時間: {elapsed:.2f}秒")
# 実行方法:
# poetry run python src/research/evaluation/evaluation.py
if __name__ == "__main__":
    MODEL_NAME = "gpt-5-mini"
    TEMPERATURE = 0.5
    WORK_REF = "work_gpt-5-mini_loop_20"  # 作業用ブランチ名
    RUN_GITHUB_REPO_PARSER = True # ここだけはテストでもTrueにする(generatorでFalseでもコミットプッシュなどするため)
    RUN_WORKFLOW_GENERATOR = True
    RUN_LINTER = True # RQ4で変更する条件
    RUN_WORKFLOW_EXECUTER = True # RQ4で変更する条件
    RUN_EXPLANATION_GENERATOR = False # RQ4では時間やコストは見ないからこれfalseにする

    # 細かい実行制御フラグ
    RUN_ACTIONLINT = True
    RUN_GHALINT = True
    RUN_PINACT = True # LLMの推測でこの処理を実行することはできないため、ghalintを実行するなら確実にTrueにする
    GENERATE_WORKFLOW_REQUIRED_FILES = True # RQ4で変更する条件
    GENERATE_BEST_PRACTICES = True # RQ4で変更する条件
    BEST_PRACTICES_ENABLE_REUSE = True
    LOOP_COUNT_MAX = 20 # ワークフローのループ回数の上限
    #main()
    python_list = [[289, 200, 202], [270, 359, 292], [399, 437, 501], [350, 448, 292], [301, 253, 256], [383, 477, 317], [477, 0, 272], [423, 243, 452], [392, 387, 246], [614, 252, 770], [280, 250, 316], [312, 372, 197], [313, 215, 398], [491, 453, 399], [287, 396, 266]]
    java_list = [[214, 216, 485], [169, 185, 482], [180, 402, 221], [268, 428, 409], [368, 726, 887], [343, 334, 218], [175, 171, 284], [439, 299, 316], [380, 389, 257], [165, 180, 191], [567, 192, 309], [499, 433, 547], [208, 144, 264], [363, 398, 464], [215, 346, 629]]
    javascript_list = [[156, 115, 111], [142, 403, 264], [171, 194, 538], [108, 341, 166], [158, 131, 229], [267, 235, 418], [372, 400, 249], [633, 193, 374], [152, 135, 166], [348, 358, 182], [194, 186, 194], [703, 383, 630], [339, 311, 304], [285, 477, 734], [147, 144, 172]]
    
    print("python yml word counts:")
    num0 = 0
    sum0 = 0
    num5 = 0
    sum5 = 0
    num1 = 0
    sum1 = 0
    for t in python_list:
        if t[0] != 0:
            num0 += 1
            sum0 += t[0]
        if t[1] != 0:
            num5 += 1
            sum5 += t[1]
        if t[2] != 0:
            num1 += 1
            sum1 += t[2]
    print(f"temp0 Average: {sum0 / num0 if num0 > 0 else 0}")
    print(f"temp05 Average: {sum5 / num5 if num5 > 0 else 0}")
    print(f"temp1 Average: {sum1 / num1 if num1 > 0 else 0}")
    
    print("java yml word counts:")
    for t in java_list:
        if t[0] != 0:
            num0 += 1
            sum0 += t[0]
        if t[1] != 0:
            num5 += 1
            sum5 += t[1]
        if t[2] != 0:
            num1 += 1
            sum1 += t[2]
    print(f"temp0 Average: {sum0 / num0 if num0 > 0 else 0}")
    print(f"temp05 Average: {sum5 / num5 if num5 > 0 else 0}")
    print(f"temp1 Average: {sum1 / num1 if num1 > 0 else 0}")
    
    print("javascript yml word counts:")
    for t in javascript_list:
        if t[0] != 0:
            num0 += 1
            sum0 += t[0]
        if t[1] != 0:
            num5 += 1
            sum5 += t[1]
        if t[2] != 0:
            num1 += 1
            sum1 += t[2]
    print(f"temp0 Average: {sum0 / num0 if num0 > 0 else 0}")
    print(f"temp05 Average: {sum5 / num5 if num5 > 0 else 0}")
    print(f"temp1 Average: {sum1 / num1 if num1 > 0 else 0}")
# TODO: condition_experiment()を変えてからやるように