from research.tools.github import GitHubTool
from research.tools.llm import LLMTool
from research.tools.rag import RAGTool

def main():
    log_is = True
    github = GitHubTool(log_is=log_is)
    llm = LLMTool(log_is=log_is)
    rag = RAGTool(log_is=log_is)

    gpt_agent = llm.create_agent(
        model_name = "gpt-4",
        tools = [
            llm.retriever_to_tool(rag.rag_tavily(max_results=3), "tavily", "ネット検索し、情報を提供します。")
        ],
    )

    print(gpt_agent.invoke({"input": "明日の東京の天気を教えてください"}))
if __name__ == "__main__":
    main()
