from pypdf import PdfReader
import warnings
from pypdf.errors import PdfReadWarning

def parse_pdf(file_path: str) -> str:
    try:
        # 경고 억제 (예: Multiple definitions in dictionary ... /Info)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", PdfReadWarning)
            reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text
    except Exception as e:
        # 암호화된 파일, 권한 문제, 손상된 파일 등 모든 예외 처리
        return ""