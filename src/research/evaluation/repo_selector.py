import requests
import os
from research.tools.github import GitHubTool
from collections import Counter
from dotenv import load_dotenv

load_dotenv()

# GitHub API トークンを環境変数から取得
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    raise ValueError("環境変数 GITHUB_TOKEN を設定してください")

HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"}
github = GitHubTool()

def fetch_language_distribution(
    github_token: str = GITHUB_TOKEN,
    year: int = 2025,
    min_stars: int = 10000,
    max_pages: int = 10,
    per_page: int = 100,
    start: int = 1
):
    """
    GitHub上で指定条件の人気リポジトリを検索し、言語ごとの件数を集計する関数。

    Parameters
    ----------
    github_token : str
        GitHubのPersonal Access Token。
    year : int
        取得対象の最終更新年（例：2025）。
    min_stars : int
        取得対象のスター数の下限。
    max_pages : int
        最大ページ数（100件/ページ、GitHub Search APIは最大1000件まで）。
    per_page : int
        1ページあたりの取得件数（最大100）。

    Returns
    -------
    dict
        {言語: 件数} の辞書。
    """

    query = f"stars:>{min_stars} pushed:{year}-01-01..{year}-12-31"
    url = "https://api.github.com/search/repositories"

    languages = []

    for page in range(start, max_pages + start):
        params = {
            "q": query,
            "sort": "stars",
            "order": "desc",
            "per_page": per_page,
            "page": page,
        }
        response = requests.get(url, headers=HEADERS, params=params)

        if response.status_code != 200:
            print(f"Error {response.status_code}: {response.text}")
            break

        data = response.json()
        items = data.get("items", [])
        if not items:
            break

        for repo in items:
            lang = repo.get("language") or "Unknown"
            languages.append(lang)

        print(f"Fetched page {page}, total {len(languages)} repos so far")

    counter = Counter(languages)
    return dict(counter)
def search_repositories(query: str, per_page: int = 10, page: int = 1):
    """GitHub API でリポジトリを検索する関数"""
    url = "https://api.github.com/search/repositories"
    params = {
        "q": query,
        "sort": "stars",
        "order": "desc",
        "per_page": per_page,
        "page": page
    }
    response = requests.get(url, headers=HEADERS, params=params)
    response.raise_for_status()
    return response.json()

def get_languages(repo_full_name: str):
    """リポジトリの言語ごとのコード量を取得"""
    url = f"https://api.github.com/repos/{repo_full_name}/languages"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error {response.status_code} for {repo_full_name}")
        return {}

def main_language_ratio(repo_full_name: str, threshold: float = 0.7):
    """主言語の割合を計算し、しきい値を超えているか判定"""
    langs = get_languages(repo_full_name)
    if not langs:
        return None, 0.0, False
    
    total = sum(langs.values())
    main_lang, main_size = max(langs.items(), key=lambda x: x[1])
    ratio = main_size / total if total > 0 else 0.0
    return main_lang, ratio, ratio >= threshold

def get_file_count(repo_full_name: str):
    """リポジトリのファイル数を取得"""
    url = f"https://api.github.com/repos/{repo_full_name}/git/trees/HEAD?recursive=1"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        tree = response.json().get("tree", [])
        return sum(1 for item in tree if item["type"] == "blob")
    else:
        print(f"Error {response.status_code} for {repo_full_name}")
        return None

def get_root_folder_count(repo_full_name: str):
    """ルートディレクトリのフォルダ数を取得"""
    url = f"https://api.github.com/repos/{repo_full_name}/git/trees/HEAD?recursive=1"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        tree = response.json().get("tree", [])
        root_folders = set()
        for item in tree:
            if item["type"] == "tree" and "/" not in item["path"]:
                root_folders.add(item["path"])
        return len(root_folders)
    else:
        print(f"Error {response.status_code} for {repo_full_name}")
        return None

def is_build_test_repo(repo_full_name: str):
    """
    リポジトリがビルド・テストジョブの自動生成に適しているかを判定する関数。

    以下の条件のいずれかを満たす場合に True を返す：
      - ビルド設定ファイルが存在する
      - テスト関連ファイルが存在する

    Parameters
    ----------
    repo_full_name : str
        "owner/repo" 形式のGitHubリポジトリ名

    Returns
    -------
    bool
        ビルド・テストジョブが作成可能なら True、そうでなければ False
    """

    url = f"https://api.github.com/repos/{repo_full_name}/git/trees/HEAD?recursive=1"
    response = requests.get(url, headers=HEADERS)
    if response.status_code != 200:
        print(f"Error {response.status_code} for {repo_full_name}")
        return False

    tree = response.json().get("tree", [])
    files = [item["path"] for item in tree if item["type"] == "blob"]

    # === 言語ごとのビルド設定ファイル ===
    build_files = {
        "Python": ["requirements.txt", "setup.py", "pyproject.toml", "tox.ini"],
        "JavaScript": ["package.json"],
        "Java": ["pom.xml", "build.gradle", "gradlew"],
        "Go": ["go.mod"],
        "C": ["Makefile", "CMakeLists.txt"],
        "Ruby": ["Gemfile", "Rakefile"],
        "Rust": ["Cargo.toml"]
    }

    # === テストディレクトリ・テストファイル ===
    test_dirs = ["test", "tests", "__tests__", "src/test", "spec"]

    # === GitHub Actionsのワークフローファイル ===
    github_workflows_dir = ".github/workflows"
    
    # === 判定ロジック ===
    # GitHub Actionsのワークフローファイルが存在しない場合は除外
    github_check = False
    for f in files:
        if f.startswith(github_workflows_dir + "/"):
            github_check = True
            break
    if not github_check:
        print(f"[NG] {repo_full_name}: .github/workflowsフォルダが存在しません。")
        return False

    has_build_file = any(
        os.path.basename(f) in sum(build_files.values(), []) for f in files
    )
    has_test_file = False
    """ビルド・テストジョブ作成可能性を判定する簡易関数"""
    for f in files:
        parts = f.lower().split("/")  # パスをディレクトリごとに分解
        # ディレクトリ名に test, tests, spec などが含まれるか
        if any(t in parts for t in test_dirs):
            has_test_file = True
            break
        # ファイル名規則でテストファイルを検出
        filename = os.path.basename(f).lower()
        if filename.endswith("_test.go") or filename.startswith("test_") or filename.endswith("_spec.rb"):
            has_test_file = True
            break

    if has_build_file and has_test_file:
        #print(f"[OK] {repo_full_name}: ビルド設定とテストが確認されました。")
        return True
    elif has_build_file:
        print(f"[INFO] {repo_full_name}: ビルド設定ファイルのみ確認されました。")
        return False
    elif has_test_file:
        print(f"[INFO] {repo_full_name}: テスト関連ファイルのみ確認されました。")
        return False 
    else:
        print(f"[NG] {repo_full_name}: ビルド設定・テスト関連ファイルが見つかりません。")
        return False


def main():
    #languages = ["Python", "Java", "JavaScript", "C", "Go", "Ruby"]
    #languages = ["Python", "Java", "JavaScript"]
    languages = ["JavaScript"]
    star_threshold = 10000
    pushed_after = "2024-10-01"
    main_lang_threshold = 0.8
    # max_file_count = 1000          # 最大ファイル数
    # max_root_folder_count = 50     # 最大ルートフォルダ数
    repo_num = 50                  # 各言語ごとに取得したいリポジトリ数
    repo_url_dict = {}
    for lang in languages:
        repo_count_all = 0 # 全検索件数
        repo_count_filtered = 0 # フィルタリング後の件数
        repo_url_dict[lang] = []
        print(f"\n=== Language: {lang} ===")
        query = f"language:{lang} stars:>{star_threshold} pushed:>{pushed_after}"
        for page in range(1, 11):  # 最大10ページまで
            result = search_repositories(query, per_page=100, page=page)
            repo_count_all += len(result["items"])
            for repo in result["items"]:
                name = repo["full_name"]
                stars = repo["stargazers_count"]
                url = repo["html_url"]
                pushed_at = repo["pushed_at"]

                # 主言語割合チェック
                main_lang, ratio, ok_lang = main_language_ratio(name, threshold=main_lang_threshold)
                if not ok_lang:
                    continue  # 条件外はスキップ

                # ファイル数チェック
                file_count = get_file_count(name)
                # if file_count is None or file_count > max_file_count:
                #     continue

                # ルートフォルダ数チェック
                root_folders = get_root_folder_count(name)
                # if root_folders is None or root_folders > max_root_folder_count:
                #     continue
                
                # ビルド・テストジョブ作成可能性チェック
                if not is_build_test_repo(name):
                    continue

                print(f"- {name} ({stars}★) {url} | 主言語={main_lang}, 割合={ratio:.2%}, "
                    f"ファイル数={file_count}, ルートフォルダ数={root_folders}, 最終更新日={pushed_at}")
                repo_url_dict[lang].append(url)
                repo_count_filtered += 1
                if repo_count_filtered >= repo_num:
                    break
            if repo_count_filtered >= repo_num:
                break
        print(f"\n=== 合計 {repo_count_all} 件のリポジトリを検索し、条件を満たしたリポジトリは {len(repo_url_dict.get(lang, []))} 件でした ===")
    # コピペしやすい形に整形してファイルに出力
    filename = "src/research/evaluation/repo_urls.txt"
    with open(filename, "w", encoding="utf-8") as f:
        for lang, repo_url_list in repo_url_dict.items():
            f.write(f"# {lang} リポジトリのコピー用リポジトリURLリスト\n")
            for i, repo_url in enumerate(repo_url_list, 1):
                result = github.fork_repository(repo_url)
                if result.status == "success":
                    f.write(f'{i}: "{result.fork_url}",\n')
                else:
                    print(f"{i}: フォークに失敗しました(url: {repo_url})")
            f.write("\n")
       
    print(f"\n=== リポジトリのコピー用リポジトリURLリストを {filename} に保存しました ===")


# 実行方法:
# poetry run python src/research/evaluation/repo_selector.py
if __name__ == "__main__":
    main()
    # count_result = {}
    # for i in range(10):
    #     result = fetch_language_distribution(min_stars=10000, start=10*i+1)
    #     for lang, count in result.items():
    #         count_result[lang] = count_result.get(lang, 0) + count
    # print("\n=== 合計結果 ===")
    # total = sum(count_result.values())
    # for lang, count in sorted(count_result.items(), key=lambda x: x[1], reverse=True):
    #     ratio = count / total * 100
    #     print(f"{lang:15}: {count:3} ({ratio:.1f}%)")