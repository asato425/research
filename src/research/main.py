from research.tools.github import GitHubTool
from research.tools.linter import LinterTool
from research.parsing.workflow_log_parser import workflow_log_parser

def main():
    github = GitHubTool()
    #linter = LinterTool()
    #file_name = "test.py"
    repo_url = "https://github.com/asato425/test"

    # clone_result = github.clone_repository(repo_url=repo_url)
    # if clone_result.status != "success":
    #     return

    local_path = "~/Desktop/research_clones/test"
    # local_path = clone_result.local_path
    
    push_result = github.commit_and_push(local_path=local_path, message="test commit")
    workflow_result = github.get_latest_workflow_logs(repo_url=repo_url, commit_sha=push_result.commit_sha)

    workflow_log_parse_result = workflow_log_parser(workflow_result)
    print("--------------------------------------------------")
    print(workflow_log_parse_result)
    # github.delete_cloned_repository(local_path=local_path)
if __name__ == "__main__":
    main()
