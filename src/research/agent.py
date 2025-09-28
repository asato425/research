"""
エージェントが使用するプロンプトを定義します。
"""

from research.workflow_graph.state import GenerateWorkflow
from research.log_output.log import log
from research.tools.llm import LLMTool
from research.tools.github import GitHubTool
from research.tools.rag import RAGTool
from langchain.tools import Tool
import json
from research.prompts.yml_rule import get_yml_rules
from research.prompts.yml_best_practices import get_yml_best_practices
from langchain_core.prompts import ChatPromptTemplate

rag = RAGTool()
llm = LLMTool()
github = GitHubTool()
tools = [
    Tool.from_function(github.read_file, name="read file", description="リポジトリの特定のファイルの内容を取得する"),
    Tool.from_function(get_yml_rules, name="get yml rules", description="GitHub Actionsのyml記述ルールを取得する"),
    Tool.from_function(get_yml_best_practices, name="get yml best practices", description="GitHub Actionsのymlベストプラクティスを取得する"),
    llm.retriever_to_tool(rag.rag_tavily)
]
prompt = ""

prompt = ChatPromptTemplate.from_messages(prompt)

agent = llm.create_agent(tools=tools, prompt=prompt)
output = agent.invoke(input)
data = json.loads(output)
result = GenerateWorkflow(**data)
log(result.status, "エージェントを利用し、ワークフローを生成しました")