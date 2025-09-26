# Odin Desktop

*[한국어](#한국어) | [English](#english)*

---

## 한국어

Electron, React, LangChain으로 구축된 AI 기반 파일 검색 및 문서 분석 데스크톱 애플리케이션입니다.

## 개요

Odin Desktop은 빠른 파일 인덱싱과 AI 기반 자연어 쿼리를 결합한 강력한 로컬 파일 검색 애플리케이션입니다. 자연어를 사용하여 파일을 검색하고 로컬 LLM 모델을 활용하여 문서에서 지능적인 답변을 얻을 수 있습니다.

## 사용방법 참조: https://depilled.tistory.com/63

## 주요 기능

- **빠른 파일 인덱싱**: 대용량 디렉토리 구조를 빠르게 인덱싱하고 검색
- **AI 기반 검색**: LLM 키워드 추출을 통한 자연어 쿼리 사용
- **다중 형식 지원**: 다양한 파일 형식의 내용 파싱 및 검색 (PDF, Word, Excel, PowerPoint, HWP 등)
- **로컬 AI 처리**: 로컬 Ollama LLM 통합으로 완전한 프라이버시 보장
- **데스크톱 GUI**: 깔끔하고 직관적인 React 기반 사용자 인터페이스
- **문서 Q&A**: 문서에 대한 질문을 하고 AI가 생성한 답변 받기

## 기술 스택

- **프론트엔드**: Electron + React + Vite
- **백엔드**: FastAPI + Python
- **AI 프레임워크**: LangChain + Ollama
- **파일 처리**: 다양한 형식을 위한 여러 Python 라이브러리
- **빌드 시스템**: electron-builder + PyInstaller

## 프로젝트 구조

```
Odin/
├── electron/                 # Electron 데스크톱 애플리케이션
│   ├── main.js              # Electron 메인 프로세스
│   ├── renderer/             # React 프론트엔드
│   ├── scripts/              # 빌드 스크립트
│   └── package.json          # Electron 앱 설정
├── backend/                  # FastAPI 서버
│   ├── server.py             # 메인 서버 애플리케이션
│   └── requirements.txt      # Python 의존성
├── Langchain/                # AI 검색 엔진
│   ├── InteractiveSearch.py  # 검색 세션 관리
│   ├── Searchtool.py         # 고급 검색 파이프라인
│   └── structured_indexing.py # 파일 인덱싱 시스템
├── parsers/                  # 파일 형식 파서
│   ├── Parser_txt.py         # 텍스트 및 마크다운
│   ├── Parser_pdf.py         # PDF 문서
│   ├── Parser_word.py        # MS Word 파일
│   ├── Parser_excel.py       # Excel 스프레드시트
│   ├── Parser_pptx.py        # PowerPoint 프레젠테이션
│   ├── Parser_csv.py         # CSV 파일
│   └── Parser_hwp.py         # 한글 HWP 파일
└── .odin_index/              # 파일 인덱스 캐시 (자동 생성)
```

## 지원 파일 형식

| 카테고리 | 형식 | 파서 |
|----------|------|------|
| 텍스트 | `.txt`, `.md` | 평문 텍스트 |
| 문서 | `.pdf`, `.docx`, `.hwp` | PDF, Word, HWP |
| 스프레드시트 | `.xlsx`, `.xls`, `.csv` | Excel, CSV |
| 프레젠테이션 | `.pptx` | PowerPoint |

## 필수 요구사항

- **Python 3.9+**
- **Node.js 16+**
- **Ollama** (AI 기능용)

## 설치

### 1. 저장소 복제

```bash
git clone <repository-url>
cd Odin
```

### 2. Python 의존성 설치

```bash
# 가상환경 생성
python -m venv .venv_odin

# 가상환경 활성화
# Windows:
.venv_odin\Scripts\activate
# Linux/Mac:
source .venv_odin/bin/activate

# 의존성 설치
pip install -r backend/requirements.txt
```

### 3. Node.js 의존성 설치

```bash
cd electron
npm install
cd renderer
npm install
cd ../..
```

### 4. Ollama 설치 및 설정

```bash
# https://ollama.ai/ 에서 Ollama 설치
# 모델 다운로드 (예: llama3)
ollama pull llama3:8b
```

## 사용법

### 개발 모드

1. **Python 백엔드 시작**:
```bash
# 가상환경 활성화
.venv_odin\Scripts\activate  # Windows
# 또는
source .venv_odin/bin/activate  # Linux/Mac

# 백엔드 서버 실행
python backend/server.py
```

2. **Electron 앱 시작**:
```bash
cd electron
npm run dev:all
```

### 프로덕션 빌드

완전한 애플리케이션 빌드:

```bash
cd electron
npm run build
npm run pack:win    # 포터블 실행 파일용
npm run dist:win    # 설치 프로그램용
```

### 애플리케이션 사용

1. **검색 경로 설정**: 검색할 디렉토리 선택
2. **파일 인덱싱**: "인덱싱" 버튼을 클릭하여 파일 스캔 및 인덱싱
3. **모델 선택**: 드롭다운에서 Ollama 모델 선택
4. **검색**: 채팅 인터페이스에서 자연어 쿼리 입력
5. **결과 검토**: 검색 결과를 탐색하고 관련 파일 선택
6. **질문하기**: 선택한 문서의 내용에 대해 질문

## 설정

애플리케이션이 자동으로 관리하는 항목:
- `.odin_index/`의 파일 인덱스 캐싱
- 포트 8765의 백엔드 서버
- Ollama 모델 통합
- 파일 파싱 및 내용 추출

## 기술 세부사항

### 검색 파이프라인

1. **사용자 쿼리** → LLM 키워드 추출
2. **파일 검색** → 고급 필터링 (확장자, 연도, 키워드)
3. **내용 로딩** → 선택된 파일 파싱
4. **AI 분석** → 문서 내용에서 답변 생성

### 성능

- 스마트 캐싱을 통한 빠른 파일 인덱싱
- AND/OR 로직을 사용한 효율적 검색
- 완전한 프라이버시를 위한 로컬 처리
- 대용량 디렉토리 구조 처리

## 문제 해결

### 일반적인 문제

1. **Ollama를 찾을 수 없음**: Ollama가 설치되고 실행 중인지 확인
2. **Python 의존성**: 가상환경 활성화 확인
3. **포트 충돌**: 백엔드는 기본적으로 포트 8765 사용
4. **파일 파싱 오류**: 일부 파일이 손상되었거나 암호로 보호됨

### 로그

- 백엔드 로그: Python 프로세스의 콘솔 출력 확인
- 프론트엔드 로그: Electron 개발자 도구 사용 (Ctrl+Shift+I)

## 기여하기

1. 저장소 포크
2. 기능 브랜치 생성
3. 변경사항 추가
4. 철저한 테스트
5. 풀 리퀘스트 제출

### 새로운 파일 파서 추가

1. `parsers/` 디렉토리에 `Parser_[형식].py` 생성
2. `parse_[형식](file_path: str) -> str` 함수 구현
3. 파서 매핑에 등록
4. 샘플 파일로 테스트

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 지원

문제 및 질문사항:
- 버그는 GitHub Issues 생성
- 일반적인 질문은 Discussions 사용
- 자세한 가이드는 Wiki 확인

---

**Odin Desktop** - 당신의 지능형 파일 검색 동반자 🔍✨

---

## English

AI-powered file search and document analysis desktop application built with Electron, React, and LangChain.

## Overview

Odin Desktop is a powerful local file search application that combines fast file indexing with AI-powered natural language queries. It allows you to search through your files using natural language and get intelligent answers from your documents using local LLM models.

## Key Features

- **Fast File Indexing**: Quickly index and search through large directory structures
- **AI-Powered Search**: Use natural language queries to find files with LLM keyword extraction
- **Multi-Format Support**: Parse and search content from various file types (PDF, Word, Excel, PowerPoint, HWP, etc.)
- **Local AI Processing**: Complete privacy with local Ollama LLM integration
- **Desktop GUI**: Clean and intuitive React-based user interface
- **Document Q&A**: Ask questions about your documents and get AI-generated answers

## Technology Stack

- **Frontend**: Electron + React + Vite
- **Backend**: FastAPI + Python
- **AI Framework**: LangChain + Ollama
- **File Processing**: Multiple Python libraries for different formats
- **Build System**: electron-builder + PyInstaller

## Project Structure

```
Odin/
├── electron/                 # Electron desktop application
│   ├── main.js              # Electron main process
│   ├── renderer/             # React frontend
│   ├── scripts/              # Build scripts
│   └── package.json          # Electron app config
├── backend/                  # FastAPI server
│   ├── server.py             # Main server application
│   └── requirements.txt      # Python dependencies
├── Langchain/                # AI search engine
│   ├── InteractiveSearch.py  # Search session management
│   ├── Searchtool.py         # Advanced search pipeline
│   └── structured_indexing.py # File indexing system
├── parsers/                  # File format parsers
│   ├── Parser_txt.py         # Text and Markdown
│   ├── Parser_pdf.py         # PDF documents
│   ├── Parser_word.py        # MS Word files
│   ├── Parser_excel.py       # Excel spreadsheets
│   ├── Parser_pptx.py        # PowerPoint presentations
│   ├── Parser_csv.py         # CSV files
│   └── Parser_hwp.py         # Korean HWP files
└── .odin_index/              # File index cache (auto-generated)
```

## Supported File Types

| Category | Formats | Parser |
|----------|---------|---------|
| Text | `.txt`, `.md` | Plain text |
| Documents | `.pdf`, `.docx`, `.hwp` | PDF, Word, HWP |
| Spreadsheets | `.xlsx`, `.xls`, `.csv` | Excel, CSV |
| Presentations | `.pptx` | PowerPoint |

## Prerequisites

- **Python 3.9+**
- **Node.js 16+**
- **Ollama** (for AI functionality)

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd Odin
```

### 2. Install Python Dependencies

```bash
# Create virtual environment
python -m venv .venv_odin

# Activate virtual environment
# Windows:
.venv_odin\Scripts\activate
# Linux/Mac:
source .venv_odin/bin/activate

# Install dependencies
pip install -r backend/requirements.txt
```

### 3. Install Node.js Dependencies

```bash
cd electron
npm install
cd renderer
npm install
cd ../..
```

### 4. Install and Configure Ollama

```bash
# Install Ollama from https://ollama.ai/
# Download a model (e.g., llama3)
ollama pull llama3:8b
```

## Usage

### Development Mode

1. **Start the Python backend**:
```bash
# Activate virtual environment
.venv_odin\Scripts\activate  # Windows
# or
source .venv_odin/bin/activate  # Linux/Mac

# Run backend server
python backend/server.py
```

2. **Start the Electron app**:
```bash
cd electron
npm run dev:all
```

### Production Build

Build the complete application:

```bash
cd electron
npm run build
npm run pack:win    # For portable executable
npm run dist:win    # For installer
```

### Using the Application

1. **Set Search Path**: Choose the directory you want to search
2. **Index Files**: Click "인덱싱" to scan and index files
3. **Select Model**: Choose an Ollama model from the dropdown
4. **Search**: Type natural language queries in the chat interface
5. **Review Results**: Browse search results and select relevant files
6. **Ask Questions**: Query the content of selected documents

## Configuration

The application automatically manages:
- File index caching in `.odin_index/`
- Backend server on port 8765
- Ollama model integration
- File parsing and content extraction

## Technical Details

### Search Pipeline

1. **User Query** → LLM keyword extraction
2. **File Search** → Advanced filtering (extensions, years, keywords)
3. **Content Loading** → Parse selected files
4. **AI Analysis** → Generate answers from document content

### Performance

- Fast file indexing with smart caching
- Efficient search with AND/OR logic
- Local processing for complete privacy
- Handles large directory structures

## Troubleshooting

### Common Issues

1. **Ollama not found**: Ensure Ollama is installed and running
2. **Python dependencies**: Check virtual environment activation
3. **Port conflicts**: Backend uses port 8765 by default
4. **File parsing errors**: Some files may be corrupted or password-protected

### Logs

- Backend logs: Check console output from Python process
- Frontend logs: Use Electron Developer Tools (Ctrl+Shift+I)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add your changes
4. Test thoroughly
5. Submit a pull request

### Adding New File Parsers

1. Create `Parser_[format].py` in `parsers/` directory
2. Implement `parse_[format](file_path: str) -> str` function
3. Register in the parser mapping
4. Test with sample files

## License

This project is licensed under the MIT License.

## Support

For issues and questions:
- Create GitHub issues for bugs
- Use discussions for general questions
- Check the wiki for detailed guides

---

**Odin Desktop** - Your intelligent file search companion 🔍✨
