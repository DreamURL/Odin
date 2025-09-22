def parse_txt(file_path: str) -> str:
    try:
        # 다양한 인코딩으로 시도
        encodings = ['utf-8', 'cp949', 'euc-kr', 'latin-1']
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
        # 모든 인코딩 시도 실패 시 바이너리로 읽어서 무시
        with open(file_path, 'rb') as f:
            content = f.read()
            return content.decode('utf-8', errors='ignore')
    except Exception as e:
        # 권한 문제, 파일 손상 등 모든 예외 처리
        return ""