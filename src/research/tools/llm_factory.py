"""
LLM（大規模言語モデル）のインスタンス生成をモジュール化し、
異なる種類のLLMでも同じインターフェースで呼び出せるようにするためのファイル。
"""
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from dotenv import load_dotenv
load_dotenv()

class LLMFactory:
    """
    LLM（大規模言語モデル）を統一インターフェースで扱うためのファクトリークラス。
    インスタンス生成時にモデル名・温度などを指定し、invokeで推論を実行できる。
    """
    def __init__(self, model_name: str, temperature: float = 0, output_parser=None):
        self.model_name = model_name
        self.temperature = temperature
        self.llm = self._create_llm_instance(model_name, temperature)
        self.output_parser = output_parser

    def _create_llm_instance(self, model_name: str, temperature: float):
        models = {
            "gemini": lambda: ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=temperature),
            "gpt-4": lambda: ChatOpenAI(model="gpt-4o-mini", temperature=temperature),
            "gpt-5": lambda: ChatOpenAI(model="gpt-5-nano"),
            "claude": lambda: ChatAnthropic(model="claude-3-haiku-20240307", temperature=temperature),
            # ここに新しいモデルを追加可能
        }
        try:
            return models[model_name]()
        except KeyError:
            raise ValueError(f"model_nameは {list(models.keys())} のみ指定可能です")

    @staticmethod
    def available_models() -> list[str]:
        return ["gemini", "gpt-4", "gpt-5", "claude"]
    
    def get_config(self) -> dict:
        return {"model_name": self.model_name, "temperature": self.temperature}

    def set_model(self, model_name: str, temperature: float = None):
        self.model_name = model_name
        if temperature is not None:
            self.temperature = temperature
        self.llm = self._create_llm_instance(model_name, self.temperature)

    def set_output_parser(self, parser):
        """
        出力パーサーをセットする
        """
        self.output_parser = parser

    def invoke(self, prompt: str, **kwargs):
        """
        LLMにプロンプトを投げて応答を返す。
        output_parserが設定されていればそれを使う。
        kwargsはモデルごとの追加パラメータ用。
        """
        result = self.llm(prompt, **kwargs)
        if self.output_parser is not None:
            return self.output_parser.parse(result)
        # LangChainのChatモデルは __call__ で推論できる
        return result.content
