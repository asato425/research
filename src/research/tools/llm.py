from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import Tool
from langchain.tools.retriever import create_retriever_tool
from langchain.agents import create_openai_functions_agent, AgentExecutor
from research.log_output.log import log
from dotenv import load_dotenv
load_dotenv()

class LLMTool:
    """
    LLM（大規模言語モデル）のインスタンス生成をクラス化し、
    異なる種類のLLMでも同じインターフェースで呼び出せるようにするためのファイル。
    """
    def __init__(self):
        pass

    def create_model(self, model_name: str = "gemini", temperature: float = 0.0, output_model: any = None) -> any:
        """
        Returns:
            モデルインスタンス (ChatGoogleGenerativeAI, ChatOpenAI, ChatAnthropic など)
        """
        models = {
            "gemini-1.5-flash": lambda: ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=temperature).with_structured_output(output_model) if output_model else ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=temperature),
            "gemini-1.5-pro": lambda: ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=temperature).with_structured_output(output_model) if output_model else ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=temperature),
            "gemini-2.5-flash": lambda: ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=temperature).with_structured_output(output_model) if output_model else ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=temperature),
            "gemini-2.5-pro": lambda: ChatGoogleGenerativeAI(model="gemini-2.5-pro", temperature=temperature).with_structured_output(output_model) if output_model else ChatGoogleGenerativeAI(model="gemini-2.5-pro", temperature=temperature),
            "gpt-4": lambda: ChatOpenAI(model="gpt-4o-mini", temperature=temperature).with_structured_output(output_model) if output_model else ChatOpenAI(model="gpt-4o-mini", temperature=temperature),
            "gpt-5": lambda: ChatOpenAI(model="gpt-5-mini", temperature=temperature).with_structured_output(output_model) if output_model else ChatOpenAI(model="gpt-5-mini", temperature=temperature),
            "claude": lambda: ChatAnthropic(model="claude-3-haiku-20240307", temperature=temperature).with_structured_output(output_model) if output_model else ChatAnthropic(model="claude-3-haiku-20240307", temperature=temperature),
            # ここに新しいモデルを追加可能
        }
        try:
            log("info", f"LLMモデル '{model_name}' を作成します。")
            return models[model_name]()
        except KeyError:
            log("error", f"モデル '{model_name}' はサポートされていません。")
            raise ValueError(f"model_nameは {list(models.keys())} のみ指定可能です")

    def create_agent(
        self, 
        model_name: str = "gpt-4", 
        temperature: float = 0.0, 
        output_model: any = None, 
        tools: list[Tool] = [], 
        prompt: ChatPromptTemplate = None,
        max_iterations: int = 5
    ) -> AgentExecutor:
        """
        Returns:
            AgentExecutor: LangChainのエージェント実行インスタンス
        gpt系以外はエラー。
        """
        if not model_name.startswith("gpt"):
            log("error", f"model_name='{model_name}' ではエージェントは作成できません。gpt系のみ対応です。")
            raise ValueError("create_agentはgpt系モデルのみ対応です")
        log("info", f"LLMエージェントを作成します。利用可能なツールは {tools} です。出力形式は {output_model} です。")
        llm = self.create_model(model_name=model_name, temperature=temperature, output_model=output_model)
        agent = create_openai_functions_agent(
            llm=llm,
            tools=tools,
            prompt=prompt
        )
        agent_executor = AgentExecutor(
            agent=agent, 
            tools=tools, 
            max_iterations=max_iterations,
            verbose=True
        )
        return agent_executor

    def retriever_to_tool(self, retriever: any, retriever_name: str, description: str) -> Tool:
        """
        Returns:
            Tool: LangChainのretriever toolインスタンス
        """
        retriever_tool = create_retriever_tool(
            retriever,
            name=retriever_name,
            description=description
        )
        log("info", f"retriever_tool '{retriever_name}' を作成しました。")
        return retriever_tool
