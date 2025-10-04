'''
LLMを使用して、特定のプログラミング言語におけるGitHub Actionsのymlベストプラクティスを取得します。
'''
from research.tools.llm import LLMTool
from research.log_output.log import log
from research.workflow_graph.state import WorkflowState
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser


prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "あなたは日本のソフトウェア開発の専門家です。"
            "GitHub Actionsのワークフロー設計・運用に精通しています。"
            "これから{programming_language}プロジェクト向けのベストプラクティスをまとめてください。"
            "出力は日本語で、実践的な例や注意点も含めてください。"
            "特定のツールを前提にせず、複数の選択肢（例: pip, poetry, pipenvなど）がある場合は比較して示してください。"
            "存在しないファイルやツールを前提とした内容は避け、条件付きでの利用方法を説明してください。"
        ),
        (
            "human",
            "{programming_language}でGitHub Actionsのワークフローを作成する際の"
            "ベストプラクティス・推奨事項・パッケージ管理ツール・ビルドツール・テストツールなどの違い、"
            "よくある失敗例・推奨されるyml構造・セキュリティや保守性の観点も含めて、"
            "箇条書きで{num}個詳しく教えてください。"
            "可能であればツールごとの使い分けや、状況に応じた推奨事項をまとめてください。"
        )
    ]
)
def get_yml_best_practices(state: WorkflowState) -> str:
    '''
    Return
        GitHub Actionsのymlベストプラクティス
    '''
    enable_reuse = state.best_practices_enable_reuse
     # Python, JavaScript, Java以外の言語や、再利用が無効な場合はLLMに生成させる
    if not enable_reuse or state.language.lower() not in ["python", "javascript","java"]:
        log("info", f"対象言語が{state.language}であり、ベストプラクティスの情報がbest_practices/にない、または再利用が無効なためLLMに生成させます。")
        llm = LLMTool().create_model(model_name=state.model_name)
        chain = prompt | llm | StrOutputParser()
        result = chain.invoke({"programming_language": state.language, "num": state.best_practice_num})
        log("info", f"{state.language}プロジェクトのGitHub Actionsのymlベストプラクティスを{state.best_practice_num}個取得しました。")
    else:
        # コスト削減のため、生成したものを保存しておいたものを使い回す
        log("info", f"対象言語が{state.language}であり、ベストプラクティスの情報がresearch/best_practices/にあるためファイルから取得します。")
        with open(f'src/research/best_practices/{state.language.lower()}.md', 'r', encoding='utf-8') as f:
            result = f.read()
        log("info", f"{state.language}プロジェクトのGitHub Actionsのymlベストプラクティスを10個取得しました。")
        
    return result

def main(language: str, best_practice_num: int = 10):
    state = WorkflowState(
            model_name="gpt-5",
            message_file_name="messages.yaml",
            messages=[],
            repo_url="http://example.com",
            run_github_parser=True,
            run_workflow_generator=True,
            run_linter=True,
            run_workflow_executer=True,
            run_explanation_generator=True,
            run_actionlint=True,
            run_ghalint=True,
            run_pinact=True,
            generate_workflow_required_files=True,
            generate_best_practices=True,
            best_practices_enable_reuse=False,
            work_ref="test",
            yml_file_name="main.yml",
            max_required_files=5,
            loop_count_max=3,
            best_practice_num=best_practice_num,
            language=language
        )
    return get_yml_best_practices(state)
    
    
# 言語ごとの使い回し用ベストプラクティスを生成させるために使用します
# 実行方法:
# poetry run python src/research/prompts/yml_best_practices.py
if __name__ == "__main__":
    language = "C"
    result = main(language, 10)
    # ファイルに保存
    with open(f'src/research/best_practices/{language.lower()}.md', 'w', encoding='utf-8') as f:
        f.write(result)