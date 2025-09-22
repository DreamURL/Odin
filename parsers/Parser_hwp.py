try:
    import olefile
    import struct
    import zlib
except ImportError:
    olefile = None

def parse_hwp(file_path: str) -> str:
    """
    HWP 파일에서 텍스트를 추출합니다.
    olefile를 사용하여 기본적인 텍스트 추출을 시도합니다.
    """
    if olefile is None:
        return "HWP 파서 라이브러리(olefile)가 설치되지 않았습니다."
    
    try:
        # HWP 파일이 OLE 파일인지 확인
        if not olefile.isOleFile(file_path):
            return "HWP 파일이 올바른 OLE 형식이 아닙니다."
        
        with olefile.OleFileIO(file_path) as ole:
            # HWP 파일 내부 구조 탐색
            streams = ole.listdir()
            text_content = ""

            # 텍스트가 포함된 스트림 찾기 (BodyText 섹션만 대상)
            for stream_path in streams:
                stream_name = "/".join(stream_path)
                if "BodyText" not in stream_name and "bodytext" not in stream_name.lower():
                    continue
                try:
                    # olefile은 openstream API를 사용해야 함
                    if not ole.exists(stream_path):
                        continue
                    data = ole.openstream(stream_path).read()

                    # 간단한 텍스트 추출 시도 (UTF-16LE 우선)
                    text = data.decode('utf-16le', errors='ignore')
                    # 제어 문자 제거
                    text = ''.join(ch for ch in text if ch.isprintable() or ch.isspace())
                    if text.strip():
                        text_content += text + "\n"
                    else:
                        # 보조 시도: UTF-8
                        text = data.decode('utf-8', errors='ignore')
                        text = ''.join(ch for ch in text if ch.isprintable() or ch.isspace())
                        if text.strip():
                            text_content += text + "\n"
                except Exception:
                    # 과도한 로그를 피하기 위해 상세 메시지는 생략하고 건너뜀
                    continue
            
            if not text_content.strip():
                return "HWP 파일에서 텍스트를 추출할 수 없습니다. 이 파일은 복잡한 형식일 수 있습니다."
            
            return text_content.strip()
            
    except Exception as e:
        return ""