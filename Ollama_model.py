from langchain_ollama import OllamaLLM as Ollama # <-- 이렇게 수정합니다.

def get_ollama_llm(model_name: str = "llama3:8b") -> Ollama:
    """
    지정된 모델 이름으로 Ollama LLM 인스턴스를 생성하고 반환합니다.
    """
    print(f"Ollama 모델 '{model_name}'을 로드합니다.")
    return Ollama(model=model_name)