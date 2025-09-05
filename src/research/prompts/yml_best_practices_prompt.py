'''
LLMを使用して、特定のプログラミング言語におけるGitHub Actionsのymlベストプラクティスを取得します。
'''
from ..tools.llm import LLMTool
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

llm = LLMTool(log_is=False).create_model(model_name="gemini", temperature=0.0)

prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "あなたは日本のソフトウェア開発の専門家です。"
            "GitHub Actionsのワークフロー設計・運用に精通しています。"
            "これから{programming_language}プロジェクト向けのベストプラクティスをまとめてください。"
            "出力は日本語で、実践的な例や注意点も含めてください。"
        ),
        (
            "human",
            "{programming_language}でGitHub Actionsのワークフローを作成する際のベストプラクティス・推奨事項・yml記述上の注意点・よくある失敗例・推奨されるyml構造・セキュリティや保守性の観点も含めて、箇条書きで10個詳しく教えてください。"
        )
    ]
)
def get_yml_best_practices(programming_language:str):
    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"programming_language": programming_language})


