import pandas as pd

def parse_csv(file_path: str) -> str:
    try:
        df = pd.read_csv(file_path)
        return df.to_string()
    except Exception as e:
        # 인코딩 문제, 권한 문제, 손상된 파일 등 모든 예외 처리
        return ""