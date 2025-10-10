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
            log("info","[COOLDOWN] 60秒待機中...")
            time.sleep(60)
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
        row == "workflow_run_results":
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
    set_log_is(SET_LOG_IS)
    # ここに評価したいリポジトリのURL(フォーク済み)を追加してください(今書いてあるのは例です)
    language_repo_dict = {
        # "python": {
        #     1: "https://github.com/asato425/test_python"
        # },
        # "python": {
        #     1: "https://github.com/asato425/free-programming-books",
        #     2: "https://github.com/asato425/public-apis",
        #     3: "https://github.com/asato425/system-design-primer",
        #     4: "https://github.com/asato425/awesome-python",
        #     5: "https://github.com/asato425/youtube-dl",
        #     6: "https://github.com/asato425/HelloGitHub",
        #     7: "https://github.com/asato425/DeepSeek-V3",
        #     8: "https://github.com/asato425/ComfyUI",
        #     9: "https://github.com/asato425/whisper",
        #     10: "https://github.com/asato425/manim",
        #     11: "https://github.com/asato425/markitdown",
        #     12: "https://github.com/asato425/Deep-Live-Cam",
        #     13: "https://github.com/asato425/browser-use",
        #     14: "https://github.com/asato425/flask",
        #     15: "https://github.com/asato425/awesome-machine-learning",
        #     16: "https://github.com/asato425/sherlock",
        #     17: "https://github.com/asato425/new-pac",
        #     18: "https://github.com/asato425/gpt4free",
        #     19: "https://github.com/asato425/keras",
        #     20: "https://github.com/asato425/open-interpreter",
        # },
        "java": {
            1: "https://github.com/asato425/JavaGuide",
            2: "https://github.com/asato425/GitHub-Chinese-Top-Charts",
            3: "https://github.com/asato425/mall",
            4: "https://github.com/asato425/advanced-java",
            5: "https://github.com/asato425/interviews",
            6: "https://github.com/asato425/termux-app",
            7: "https://github.com/asato425/MPAndroidChart",
            8: "https://github.com/asato425/easyexcel",
            9: "https://github.com/asato425/xxl-job",
            10: "https://github.com/asato425/spring-cloud-alibaba",
            # 11: "https://github.com/asato425/vhr",
            # 12: "https://github.com/asato425/SmartRefreshLayout",
            # 13: "https://github.com/asato425/gson",
            # 14: "https://github.com/asato425/Apktool",
            # 15: "https://github.com/asato425/source-code-hunter",
            # 16: "https://github.com/asato425/GSYVideoPlayer",
            # 17: "https://github.com/asato425/HikariCP",
            # 18: "https://github.com/asato425/RxAndroid",
            # 19: "https://github.com/asato425/Algorithms",
            # 20: "https://github.com/asato425/APIJSON",
        },
        "javascript": {
            1: "https://github.com/asato425/javascript-algorithms",
            2: "https://github.com/asato425/javascript",
            3: "https://github.com/asato425/create-react-app",
            4: "https://github.com/asato425/awesome-mac",
            5: "https://github.com/asato425/github-readme-stats",
            6: "https://github.com/asato425/json-server",
            7: "https://github.com/asato425/express",
            8: "https://github.com/asato425/33-js-concepts",
            9: "https://github.com/asato425/lodash",
            10: "https://github.com/asato425/jquery",
            # 11: "https://github.com/asato425/drawio-desktop",
            # 12: "https://github.com/asato425/hiring-without-whiteboards",
            # 13: "https://github.com/asato425/dayjs",
            # 14: "https://github.com/asato425/serverless",
            # 15: "https://github.com/asato425/react",
            # 16: "https://github.com/asato425/htmx",
            # 17: "https://github.com/asato425/30-Days-Of-JavaScript",
            # 18: "https://github.com/asato425/swiper",
            # 20: "https://github.com/asato425/preact",
        },
        "c": {
            1: "https://github.com/asato425/stb",
            2: "https://github.com/asato425/nginx",
            3: "https://github.com/asato425/GoodbyeDPI",
            4: "https://github.com/asato425/libuv",
            5: "https://github.com/asato425/masscan",
            6: "https://github.com/asato425/mimikatz",
            7: "https://github.com/asato425/BlackHole",
            8: "https://github.com/asato425/sway",
            9: "https://github.com/asato425/rofi",
            10: "https://github.com/asato425/ecapture",
            # 11: "https://github.com/asato425/glfw",
            # 12: "https://github.com/asato425/nginx-rtmp-module",
            # 13: "https://github.com/asato425/coturn",
            # 14: "https://github.com/asato425/libsodium",
            # 15: "https://github.com/asato425/openvpn",
            # 16: "https://github.com/asato425/lua-nginx-module",
            # 17: "https://github.com/asato425/thc-hydra",
            # 18: "https://github.com/asato425/Nuklear",
            # 19: "https://github.com/asato425/xxHash",
            # 20: "https://github.com/asato425/proxychains-ng",
        },
        "c++": {
            1: "https://github.com/asato425/tesseract",
            2: "https://github.com/asato425/TrafficMonitor",
            3: "https://github.com/asato425/leveldb",
            4: "https://github.com/asato425/interview",
            5: "https://github.com/asato425/C-Plus-Plus",
            6: "https://github.com/asato425/Hyprland",
            7: "https://github.com/asato425/spdlog",
            8: "https://github.com/asato425/shadPS4",
            9: "https://github.com/asato425/fmt",
            10: "https://github.com/asato425/tinyrenderer",
            # 11: "https://github.com/asato425/simdjson",
            # 12: "https://github.com/asato425/deskflow",
            # 13: "https://github.com/asato425/Catch2",
            # 14: "https://github.com/asato425/uWebSockets",
            # 15: "https://github.com/asato425/TranslucentTB",
            # 16: "https://github.com/asato425/cutter",
            # 17: "https://github.com/asato425/dxvk",
            # 18: "https://github.com/asato425/muduo",
            # 19: "https://github.com/asato425/Waifu2x-Extension-GUI",
            # 20: "https://github.com/asato425/subconverter",
        },
        "c#": {
            1: "https://github.com/asato425/v2rayN",
            2: "https://github.com/asato425/shadowsocks-windows",
            3: "https://github.com/asato425/RevokeMsgPatcher",
            4: "https://github.com/asato425/ScreenToGif",
            5: "https://github.com/asato425/WaveFunctionCollapse",
            6: "https://github.com/asato425/awesome-dotnet-core",
            7: "https://github.com/asato425/UniGetUI",
            8: "https://github.com/asato425/CMWTAT_Digital_Edition",
            9: "https://github.com/asato425/Dapper",
            10: "https://github.com/asato425/CleanArchitecture",
            # 11: "https://github.com/asato425/Jackett",
            # 12: "https://github.com/asato425/QuestPDF",
            # 13: "https://github.com/asato425/YoutubeDownloader",
            # 14: "https://github.com/asato425/BBDown",
            # 15: "https://github.com/asato425/ArchiSteamFarm",
            # 16: "https://github.com/asato425/csharplang",
            # 17: "https://github.com/asato425/MediatR",
            # 18: "https://github.com/asato425/FileConverter",
            # 19: "https://github.com/asato425/g-helper",
            # 20: "https://github.com/asato425/AutoMapper",
        },
        "go": {
            1: "https://github.com/asato425/awesome-go",
            2: "https://github.com/asato425/ollama",
            3: "https://github.com/asato425/frp",
            4: "https://github.com/asato425/gin",
            5: "https://github.com/asato425/caddy",
            6: "https://github.com/asato425/dive",
            7: "https://github.com/asato425/alist",
            8: "https://github.com/asato425/v2ray-core",
            9: "https://github.com/asato425/cobra",
            10: "https://github.com/asato425/gorm",
            # 11: "https://github.com/asato425/fiber",
            # 12: "https://github.com/asato425/compose",
            # 13: "https://github.com/asato425/bubbletea",
            # 14: "https://github.com/asato425/beego",
            # 15: "https://github.com/asato425/CasaOS",
            # 16: "https://github.com/asato425/echo",
            # 17: "https://github.com/asato425/headscale",
            # 18: "https://github.com/asato425/Xray-core",
            # 19: "https://github.com/asato425/viper",
            # 20: "https://github.com/asato425/sing-box",
        },
        "ruby": {
            1: "https://github.com/asato425/awesome-swift",
            2: "https://github.com/asato425/devise",
            3: "https://github.com/asato425/quine-relay",
            4: "https://github.com/asato425/fluentd",
            5: "https://github.com/asato425/kamal",
            6: "https://github.com/asato425/tmuxinator",
            7: "https://github.com/asato425/capistrano",
            8: "https://github.com/asato425/sinatra",
            9: "https://github.com/asato425/remote-working",
            10: "https://github.com/asato425/capybara",
        },
        
    }
    # for language, repos in language_repo_dict.items():
    #     print(f"\n\n########## {language} のリポジトリの評価を開始 ##########")
    #     repositories_to_evaluate = {i: url for i, url in repos.items()}
    #     states = evaluate_multiple(repositories_to_evaluate)
    #     save_states_to_excel(states, language)
    #     print(f"########## {language} のリポジトリの評価が完了 ##########\n\n")

    delete_remote_repo(language_repo_dict) # フォークしたリポジトリを削除する場合はコメントアウトを外す
# 実行方法:
# poetry run python src/research/evaluation/evaluation.py
if __name__ == "__main__":
    main()
    