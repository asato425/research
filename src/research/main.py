from research.tools.github import GitHubTool
from research.tools.linter import LinterTool
from research.tools.parser import ParserTool
from research.tools.llm import LLMTool
from research.tools.rag import RAGTool

def main():
    log_is = True
    github = GitHubTool(log_is=log_is)
    linter = LinterTool(log_is=log_is)
    parser = ParserTool(log_is=log_is)
    llm = LLMTool(log_is=log_is)
    rag = RAGTool(log_is=log_is)

    file_name = "sample.yml"
    repo_url = "https://github.com/fastapi/fastapi"
    llm = llm.create_model()
    rag.rag_git()
    repo_info = github.get_repository_info(repo_url=repo_url)
    

if __name__ == "__main__":
    main()
