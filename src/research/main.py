from research.log_output.log import set_log_is
from research.workflow_graph.builder import WorkflowBuilder
import argparse

# ノードの実行制御フラグ
RUN_GITHUB_REPO_PARSER = True # ここだけはテストでもTrueにする(generatorでFalseでもコミットプッシュなどするため)
RUN_WORKFLOW_GENERATOR = True
RUN_LINTER = False
RUN_WORKFLOW_EXECUTER = False
RUN_EXPLANATION_GENERATOR = False

# 細かい実行制御フラグ
RUN_ACTIONLINT = True
RUN_GHALINT = True
GENERATE_WORKFLOW_REQUIRED_FILES = True
GENERATE_BEST_PRACTICES = True

# モデルとエージェントの設定
"""
MODEL_NAMEには"gemini-1.5-flash"、"gemini-1.5-pro"、"gemini-2.5-flash"、"gemini-2.5-pro"、"gpt-4"、"gpt-5"、"claude"を指定できます。
AGENT_ISにはTrueまたはFalseを指定できます。MODEL_NAMEが"gpt"のみTrueを指定できます。基本的にはFalse、今後実験的にTrueにする可能性があります。
"""
MODEL_NAME = "gpt-5"
AGENT_IS = False and MODEL_NAME.startswith("gpt")

# コマンドライン引数のデフォルト値
WORK_REF = "work_"+MODEL_NAME  # 作業用ブランチ名
YML_FILE_NAME = "ci.yml" # 生成されるYAMLファイル名
MAX_REQUIRED_FILES = 5 # ワークフロー生成に必要な主要ファイルの最大数
LOOP_COUNT_MAX = 5 # ワークフローのループ回数の上限
LINT_LOOP_COUNT_MAX = 3 # Lintのループ回数の上限
BEST_PRACTICE_NUM = 10 # 言語固有のベストプラクティスの数

# ログ出力の設定、TrueかFalseを指定できます
SET_LOG_IS = True

def main():  
    set_log_is(SET_LOG_IS)
    # コマンドライン引数のパーサーを作成
    parser = argparse.ArgumentParser(
        description="ユーザー要求に基づいてYAMLファイルを生成します"
    )
    # "repo_url"引数を追加
    parser.add_argument(
        "--repo_url",
        type=str,
        help="リポジトリのURLを指定してください",
    )
    # "work_ref"引数を追加
    parser.add_argument(
        "--work_ref",
        type=str,
        default=WORK_REF,
        help="作業用のブランチの名前を設定してください（デフォルト:test）",
    )
    # "yml_file_name"引数を追加
    parser.add_argument(
        "--yml_file_name",
        type=str,
        default=YML_FILE_NAME,
        help="生成されるYAMLファイルの名前を設定してください（デフォルト:ci.yml）",
    )
    # "max_required_files"引数を追加
    parser.add_argument(
        "--max_required_files",
        type=int,
        default=MAX_REQUIRED_FILES,
        help="ワークフロー生成に必要な主要ファイルの最大数を設定してください（デフォルト:5）",
    )
    # "loop_count_max"引数を追加
    parser.add_argument(
        "--loop_count_max",
        type=int,
        default=LOOP_COUNT_MAX,
        help="ワークフローのループ回数の上限を設定してください（デフォルト:5）",
    )
    # "lint_loop_count_max"引数を追加
    parser.add_argument(
        "--lint_loop_count_max",
        type=int,
        default=LINT_LOOP_COUNT_MAX,
        help="生成とLintのループ回数の上限を設定してください（デフォルト:3）",
    )
    # "best_practice_num"引数を追加
    parser.add_argument(
        "--best_practice_num",
        type=int,
        default=BEST_PRACTICE_NUM,
        help="言語固有のベストプラクティスの数を設定してください（デフォルト:10）",
    )
    # コマンドライン引数を解析
    args = parser.parse_args()

    # ワークフローエージェントを初期化
    agent = WorkflowBuilder(model_name=MODEL_NAME, agent_is=AGENT_IS)
    # エージェントを実行して最終的な出力を取得
    final_state = agent.run(
        # リポジトリのURLは必須引数
        repo_url=args.repo_url,
        # LLMの設定
        model_name=MODEL_NAME,
        agent_is=AGENT_IS,
        # ノードの実行制御フラグ
        run_github_parser=RUN_GITHUB_REPO_PARSER,
        run_workflow_generator=RUN_WORKFLOW_GENERATOR and RUN_GITHUB_REPO_PARSER,
        run_linter=RUN_LINTER and RUN_WORKFLOW_GENERATOR,
        run_workflow_executer=RUN_WORKFLOW_EXECUTER and RUN_WORKFLOW_GENERATOR,
        run_explanation_generator=RUN_EXPLANATION_GENERATOR and RUN_WORKFLOW_GENERATOR,
        # 細かい処理の実行制御フラグ
        run_actionlint=RUN_ACTIONLINT and RUN_LINTER and RUN_WORKFLOW_GENERATOR,
        run_ghalint=RUN_GHALINT and RUN_LINTER and RUN_WORKFLOW_GENERATOR,
        generate_workflow_required_files=GENERATE_WORKFLOW_REQUIRED_FILES and RUN_GITHUB_REPO_PARSER,
        generate_best_practices=GENERATE_BEST_PRACTICES and RUN_GITHUB_REPO_PARSER,
        # その他のパラメータ
        work_ref=args.work_ref,
        yml_file_name=args.yml_file_name,
        max_required_files=args.max_required_files,
        loop_count_max=args.loop_count_max,
        lint_loop_count_max=args.lint_loop_count_max,
        best_practice_num=args.best_practice_num
    )

    # 最終的な出力を表示
    print(final_state)
    

# 実行方法:
# poetry run python src/research/main.py --repo_url "リポジトリのURL" --work_ref "作業用のブランチ名" --yml_file_name "生成されるYAMLファイル名" --max_required_files 5 --loop_count_max 5 --lint_loop_count_max 3 --best_practice_num 10
# --repo_urlのみ必須、他は任意
# 実行例）
# poetry run python  src/research/main.py --repo_url "https://github.com/asato425/test"
if __name__ == "__main__":
    main()

