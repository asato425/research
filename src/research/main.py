from research.tools.github import GitHubTool
from research.tools.linter import Linter

def main():
    github = GitHubTool()
    linter = Linter()
    #file_name = "test.py"
    repo_url = "https://github.com/asato425/test"

    clone_result = github.clone_repository(repo_url=repo_url)
    if clone_result.status != "success":
        return

    local_path = clone_result.local_path

    linter.ghalint(local_path=local_path)
    github.delete_cloned_repository(local_path=local_path)

if __name__ == "__main__":
    main()
