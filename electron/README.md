# Odin Electron + React (Vite) 개발/빌드 가이드

## 개발 모드 (Windows cmd)
1. 백엔드(FastAPI)는 Electron이 자동 실행합니다.
2. 프런트엔드(React+Vite) dev 서버 실행:

```
cd electron\renderer
npm install
npm run dev
```

3. 새 터미널에서 Electron 실행 (dev 서버 URL 사용):
```
cd electron
npm run dev
```

- 기본 dev 서버 주소: http://127.0.0.1:5173
- Electron은 환경변수 `RENDERER_URL` 값으로 해당 주소를 로드합니다.

## 프로덕션 빌드 및 패키징 (Windows)
```
cd electron
npm run dist:win
```

이 스크립트는 다음을 수행합니다:
- `renderer`를 Vite로 빌드하여 `electron/renderer/dist` 생성
- electron-builder로 Windows 설치파일(NSIS) 또는 포터블 생성

## 참고
- 프런트엔드 소스: `electron/renderer/src`
- 빌드 산출물: `electron/renderer/dist`
- 메인 프로세스: `electron/main.js`
- 프리로드: `electron/preload.cjs`
- 백엔드: `backend/server.py`Odin Desktop (Electron)

개요
- Electron UI + Python(FastAPI) 백엔드 조합의 데스크톱 앱입니다.

개발 실행
1) Node.js 설치 후, 의존성 설치
   npm install
2) 앱 실행
   npm run dev

Windows 패키징
- electron-builder를 사용합니다.

1) 빌드 (Portable)
   npm run pack:win

2) 설치형(NSIS) 빌드
   npm run dist:win

Python 백엔드 포함 전략
- 기본 코드는 electron/main.js에서 로컬 Python 실행 파일(PYTHON 환경변수 or PATH의 python)을 이용해 backend/server.py를 실행합니다.
- 배포 시 선택지:
  A) 사용자 PC에 Python 설치를 요구 (README 가이드 제공)
  B) PyInstaller 등으로 backend/server.py를 단일 exe로 빌드 후, electron 리소스에 포함하고 main.js에서 exe를 실행

옵션 A: 사용자 Python 사용 가이드(권장 간단 방식)
- Python 3.9+ 설치 후, 루트에 다음 실행:
   pip install -r requirements.txt
   pip install -r backend/requirements.txt
   set PYTHON=python  (필요 시 지정)
   npm run dist:win

옵션 B: PyInstaller로 백엔드 exe 만들기(고급)
1) 가상환경에서 백엔드 의존성 설치
   pip install -r requirements.txt
   pip install -r backend/requirements.txt
   pip install pyinstaller
2) 빌드
   pyinstaller --onefile backend/server.py -n odin-backend
3) electron/main.js에서 python 대신 odin-backend.exe를 실행하도록 수정

배포물 실행
- NSIS 설치본 설치 후 바로 실행 가능
- Portable 빌드의 경우 Odin Desktop.exe 실행

문제 해결
- 백엔드 포트가 이미 사용 중: 환경변수 BACKEND_PORT로 변경 후 실행
- Ollama 미설치: 옵션 탭 모델 목록이 비어있을 수 있으며 오류 메시지 노출됨
# Odin Electron App (skeleton)

This is a minimal Electron wrapper that starts the Python FastAPI backend and serves a simple 2-pane UI.

- UI (Electron): two sections
  - Left: Index & Search
  - Right: Q&A
- Backend (Python/FastAPI): reuses existing project modules for indexing/search/Q&A

## Dev Run (Windows, cmd)

1) Install Node deps

```
cd electron
npm install
```

2) (Optional) Create Python venv and install backend deps

```
cd ..\backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

3) Start Electron (which will spawn backend)

```
cd ..\electron
npm run dev
```

Backend defaults to http://127.0.0.1:8765 and is spawned by Electron main process.

You can change the Python executable used by setting the environment variable `PYTHON` before starting Electron.
