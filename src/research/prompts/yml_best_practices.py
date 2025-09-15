'''
LLMを使用して、特定のプログラミング言語におけるGitHub Actionsのymlベストプラクティスを取得します。
'''
from ..tools.llm import LLMTool
from ..log_output.log import log
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

llm = LLMTool().create_model(model_name="gemini", temperature=0.0)

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
            "{programming_language}でGitHub Actionsのワークフローを作成する際のベストプラクティス・推奨事項・パッケージ管理ツール、ビルドツール、テストツール、その他コマンドなどのツールやコマンドの違い・よくある失敗例・推奨されるyml構造・セキュリティや保守性の観点も含めて、箇条書きで{num}個詳しく教えてください。"
        )
    ]
)
def get_yml_best_practices(programming_language:str, num:int = 10):
    '''
    Return
        GitHub Actionsのymlベストプラクティス
    '''
    chain = prompt | llm | StrOutputParser()
    result = chain.invoke({"programming_language": programming_language, "num": num})
    log("info", f"{programming_language}プロジェクトのGitHub Actionsのymlベストプラクティスを{num}個取得しました。")
    return result
