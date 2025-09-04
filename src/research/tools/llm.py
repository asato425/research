"""
LLM（大規模言語モデル）のインスタンス生成をクラス化し、
異なる種類のLLMでも同じインターフェースで呼び出せるようにするためのファイル。
"""
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain.tools.retriever import create_retriever_tool
from ..log_output.log import log
from dotenv import load_dotenv
load_dotenv()

class LLMTool:
    """
    LLMクラス。
    例:
        llm = LLMTool(model_name="gemini", temperature=0.2).create()
    """
    def __init__(self, model_name: str = "gemini", temperature: float = 0.0, output_model: any = None, tools: list = None, log_is: bool = True):
        self.model_name = model_name
        self.temperature = temperature
        self.output_model = output_model
        self.tools = tools if tools is not None else []
        self.log_is = log_is

    def create(self) -> any:
        models = {
            "gemini": lambda: ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=self.temperature).with_structured_output(self.output_model) if self.output_model else ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=self.temperature),
            "gpt-4": lambda: ChatOpenAI(model="gpt-4o-mini", temperature=self.temperature).with_structured_output(self.output_model) if self.output_model else ChatOpenAI(model="gpt-4o-mini", temperature=self.temperature),
            "gpt-5": lambda: ChatOpenAI(model="gpt-5-nano", temperature=self.temperature).with_structured_output(self.output_model) if self.output_model else ChatOpenAI(model="gpt-5-nano", temperature=self.temperature),
            "claude": lambda: ChatAnthropic(model="claude-3-haiku-20240307", temperature=self.temperature).with_structured_output(self.output_model) if self.output_model else ChatAnthropic(model="claude-3-haiku-20240307", temperature=self.temperature),
            # ここに新しいモデルを追加可能
        }
        try:
            log("info", f"LLMモデル '{self.model_name}' を作成します。", self.log_is)
            return models[self.model_name]()
        except KeyError:
            log("error", f"モデル '{self.model_name}' はサポートされていません。", self.log_is)
            raise ValueError(f"model_nameは {list(models.keys())} のみ指定可能です")

    def set_with_structured_output(self, output_model) -> None:
        self.output_model = output_model
        log("info", f"LLMの出力モデルを '{self.output_model}' に設定しました。", self.log_is)

    def add_tools(self, tool: any) -> None:
        self.tools.append(tool)
        log("info", f"ツール '{tool}' をLLMに追加しました。", self.log_is)

    def retriever_to_tool(self, retriever: any, retriever_name: str, description: str) -> any:
        retriever_tool = create_retriever_tool(
            retriever,
            name=retriever_name,
            description=description
        )
        log("info", f"retriever_tool '{retriever_name}' を作成しました。", self.log_is)
        return retriever_tool
