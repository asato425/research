from research.tools.github import GitHubTool


def test_github():
    github = GitHubTool()
    # テスト用のリポジトリURLを用意
    repo_url = "https://github.com/asato425/test"
    relative_path = "test.txt"
    
    # リポジトリをクローン
    result = github.clone_repository(repo_url)
    local_path = result.local_path
    assert hasattr(result, "status")
    assert hasattr(result, "message")
    assert result.status == "success"
    assert local_path is not None
    assert result.repo_url is not None

    # リポジトリ情報を取得
    result = github.get_repository_info(repo_url)
    assert hasattr(result, "status")
    assert hasattr(result, "info")
    assert hasattr(result, "message")
    assert result.status == "success"
    assert isinstance(result.info, dict)

    # ファイルを作成
    result = github.create_file(local_path, relative_path)
    assert hasattr(result, "status")
    assert hasattr(result, "message")
    assert result.status == "success"

    # ファイルに書き込む
    result = github.write_to_file(local_path, relative_path, "test")
    assert hasattr(result, "status")
    assert hasattr(result, "message")
    assert result.status == "success"

    # ファイルを読み込む
    result = github.read_file(local_path, relative_path)
    assert hasattr(result, "status")
    assert hasattr(result, "info")
    assert hasattr(result, "message")
    assert result.status == "success"

    # コミットしてプッシュ
    result = github.commit_and_push(local_path, "test commit(create and write)")
    assert hasattr(result, "status")
    assert hasattr(result, "message")
    assert hasattr(result, "commit_sha")
    assert result.status == "success"
    assert result.commit_sha is not None
    commit_sha = result.commit_sha

    # ワークフローのログを取得
    result = github.get_latest_workflow_logs(repo_url, commit_sha)
    assert hasattr(result, "status")
    assert hasattr(result, "message")
    assert hasattr(result, "conclusion")
    assert hasattr(result, "failure_reason")

    # ファイルを削除してコミット・プッシュ
    result = github.delete_file(local_path, relative_path)
    assert hasattr(result, "status")
    assert hasattr(result, "message")
    assert result.status == "success"
    result = github.commit_and_push(local_path, "test commit(delete)")
    assert hasattr(result, "status")
    assert hasattr(result, "message")
    assert hasattr(result, "commit_sha")
    assert result.status == "success"
    assert result.commit_sha is not None

    # ワーキングブランチを作成
    result = github.create_working_branch(local_path, "test-branch")
    assert hasattr(result, "status")
    assert hasattr(result, "message")
    assert result.status == "success"

    # ファイルツリーを取得
    result = github.get_file_tree(local_path)
    assert hasattr(result, "status")
    assert hasattr(result, "message")
    assert hasattr(result, "info")
    assert result.status == "success"

    # クローンしたリポジトリを削除
    result = github.delete_cloned_repository(local_path)
    assert hasattr(result, "status")
    assert hasattr(result, "message")
    assert result.status == "success"
