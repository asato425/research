from research.log_output.log import set_log_is
from research.langgraph.nodes.workflow_generator import WorkflowGenerator
from research.langgraph.nodes.github_repo_parser import GitHubRepoParser
from research.langgraph.state import WorkflowState

def main():
    set_log_is(True)

    repo_url = "https://github.com/asato425/test"
    repo_parser = GitHubRepoParser()
    workflow_generator = WorkflowGenerator()

    state = WorkflowState(repo_url = repo_url)

if __name__ == "__main__":
    main()
