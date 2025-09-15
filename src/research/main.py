from research.tools.github import GitHubTool
from research.tools.llm import LLMTool
from research.tools.rag import RAGTool
from research.log_output.log import set_log_is

def main():
    set_log_is(True)
    github = GitHubTool()
    # llm = LLMTool()
    # rag = RAGTool()
    repo_url = "https://github.com/asato425/test"
    github.dispatch_workflow(repo_url, "main", "python-package.yml")
if __name__ == "__main__":
    main()
