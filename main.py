import os
from LLMscript import create_agent_executor
from Langchain.InteractiveSearch import run_interactive_flow

def setup_search_path() -> str:
    """
    프로그램 시작 시 사용자로부터 기본 검색 경로를 입력받고 유효성을 검사합니다.
    """
    while True:
        user_path_input = input("\n검색을 시작할 경로를 입력해주세요 (예: E:/projects): ").strip()
        if user_path_input and os.path.isdir(user_path_input):
            print(f"검색 경로가 '{user_path_input}'(으)로 설정되었습니다.")
            return user_path_input
        print(f"오류: '{user_path_input}'는 존재하지 않거나 디렉토리가 아닙니다. 다시 입력해주세요.")


def main():
    print("--- Odin 파일 검색기를 시작합니다 ---")
    
    # 1. 사용자로부터 검색 경로 설정받기
    base_search_path = setup_search_path()
    
    # 2. 선택한 경로 인덱싱(사전 준비)
    try:
        from Langchain.Searchtool import preindex_path
        info = preindex_path(base_search_path)
        parseable_info = f", 파싱가능: {info.get('parseable_count', 0)}개" if 'parseable_count' in info else ""
        print(f"인덱스 상태 - 경로: {info['base_path']}, 항목 수: {info['count']}{parseable_info}, 소스: {info['source']}")
    except Exception as e:
        print(f"인덱스 준비 중 경고: {e}")

    # 3. 인터랙티브 검색 플로우 시작 (LLM은 키워드 추출과 문서 질의에만 사용)
    run_interactive_flow(base_search_path)

    # (구) ReAct 에이전트 루프는 인터랙티브 플로우로 대체되었습니다.

if __name__ == "__main__":
    main()