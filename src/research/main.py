from research.tools.github import GitHubTool
from research.tools.llm import LLMTool
from research.tools.rag import RAGTool
from research.log_output.log import set_log_is

def main():
    set_log_is(False)
    github = GitHubTool()
    llm = LLMTool()
    rag = RAGTool()
    repo_url = "https://github.com/asato425/test"
    github.get_repository_info(repo_url)
if __name__ == "__main__":
    main()
