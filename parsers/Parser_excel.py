import pandas as pd

def parse_excel(file_path: str) -> str:
    try:
        df = pd.read_excel(file_path, sheet_name=None)
        content = ""
        for sheet_name, sheet_df in df.items():
            content += f"--- Sheet: {sheet_name} ---\n"
            content += sheet_df.to_string() + "\n\n"
        return content
    except Exception as e:
        # 암호화된 파일, 권한 문제, 손상된 파일 등 모든 예외 처리
        return ""