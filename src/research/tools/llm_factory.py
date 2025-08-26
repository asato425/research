"""
LLM（大規模言語モデル）のインスタンス生成をモジュール化し、
異なる種類のLLMでも同じインターフェースで呼び出せるようにするためのファイル。
"""
from dotenv import load_dotenv
load_dotenv()

def llm(model_name: str, temperature: float = 0):
    """
    指定したモデル名に応じてLLMインスタンスを返す。
    新しいモデルを追加する場合は、models辞書に追加するだけで対応可能。

    引数:
        model_name (str): 利用したいモデル名（例: "gemini", "gpt", "claude" など）

    戻り値:
        LLMインスタンス: 固定モデルのLLMインスタンス。
    """
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_openai import ChatOpenAI
    from langchain_anthropic import ChatAnthropic

    models = {
        "gemini": lambda: ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=temperature),
        "gpt-4": lambda: ChatOpenAI(model="gpt-4o-mini", temperature=temperature),
        "gpt-5": lambda: ChatOpenAI(model="gpt-5-nano"),
        "claude": lambda: ChatAnthropic(model="claude-3-haiku-20240307", temperature=temperature),
        # ここに新しいモデルを追加可能
        # "new_model": lambda: NewModelClass(model="new-model-name", temperature=temperature),
    }

    try:
        return models[model_name]()
    except KeyError:
        raise ValueError(f"model_nameは {list(models.keys())} のみ指定可能です")
    