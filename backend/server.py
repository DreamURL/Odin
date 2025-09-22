import os
import sys
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import subprocess
import time

if sys.platform == "win32":
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['PYTHONLEGACYWINDOWSSTDIO'] = '0'
    os.environ['PYTHONUTF8'] = '1'

    try:
        subprocess.run(['chcp', '65001'], shell=True, capture_output=True, check=False)
    except:
        pass

    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from pathlib import Path as _Path
_PROJECT_ROOT = str(_Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from Langchain.structured_indexing import StructuredIndex, FileInfo
from Langchain.InteractiveSearch import SearchSession

app = FastAPI(title="Odin Backend API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_SESSIONS: Dict[str, SearchSession] = {}
_STARTED_AT = time.time()

def get_cache_dir():
    """Get cache directory path based on execution location"""
    from pathlib import Path

    if getattr(sys, 'frozen', False):
        app_path = Path(sys.executable).parent
    else:
        app_path = Path(__file__).parent.parent

    cache_dir = app_path / ".odin_index"
    cache_dir.mkdir(exist_ok=True)
    return cache_dir

class IndexRequest(BaseModel):
    base_path: str

class IndexResponse(BaseModel):
    count: int
    extensions: List[str]
    ai_readable_exts: List[str]
    base_path: str
    cache_dir: str
    csv_path: str
    safe_path: str

class SearchRequest(BaseModel):
    base_path: str
    query: str
    allowed_exts: Optional[List[str]] = None

class FileInfoDTO(BaseModel):
    path: str
    name: str
    extension: Optional[str]
    size_bytes: int
    is_directory: bool
    created_time: Optional[str]
    modified_time: Optional[str]

class SearchResponse(BaseModel):
    keywords: List[str]
    expanded_keywords: List[str]
    extensions: List[str]
    years: List[int]
    items: List[FileInfoDTO]

class RefineRequest(BaseModel):
    base_path: str
    keywords: List[str]
    current_items: List[str]

class ProceedRequest(BaseModel):
    base_path: str
    paths: List[str]

class QARequest(BaseModel):
    base_path: str
    question: str

class QAResponse(BaseModel):
    answer: str

def _get_session(base_path: str) -> SearchSession:
    sess = _SESSIONS.get(base_path)
    if not sess:
        sess = SearchSession(base_path)
        _SESSIONS[base_path] = sess
    return sess

def _load_parser_registry() -> Dict[str, str]:
    import importlib
    mapping = [
        ("parsers.Parser_txt", "parse_txt", [".txt", ".md"]),
        ("parsers.Parser_word", "parse_word", [".docx"]),
        ("parsers.Parser_pdf", "parse_pdf", [".pdf"]),
        ("parsers.Parser_excel", "parse_excel", [".xlsx", ".xls"]),
        ("parsers.Parser_csv", "parse_csv", [".csv"]),
        ("parsers.Parser_pptx", "parse_pptx", [".pptx"]),
        ("parsers.Parser_hwp", "parse_hwp", [".hwp"]),
    ]
    reg: Dict[str, str] = {}
    for mod_name, func_name, exts in mapping:
        try:
            mod = importlib.import_module(mod_name)
            func = getattr(mod, func_name)
            for ext in exts:
                reg[ext] = func.__name__
        except Exception:
            continue
    return reg

@app.get("/health")
def api_health():
    """Health check endpoint"""
    ollama_available = False
    try:
        subprocess.run(["ollama", "list"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=1, check=False)
        ollama_available = True
    except Exception:
        ollama_available = False

    return {
        "ok": True,
        "status": "ready",
        "uptime_sec": round(time.time() - _STARTED_AT, 2),
        "ollama": {
            "available": ollama_available
        }
    }

@app.post("/index", response_model=IndexResponse)
def api_index(req: IndexRequest):
    base = req.base_path
    if not os.path.isdir(base):
        raise ValueError("Invalid base_path")

    indexer = StructuredIndex(base)
    from pathlib import Path
    cache_dir = get_cache_dir()
    safe_path = str(Path(base)).replace(':', '').replace('\\', '_').replace('/', '_')
    csv_path = cache_dir / f"structured_index_{safe_path}.csv"

    if csv_path.exists():
        existing_infos = indexer.load_from_csv(str(csv_path))
        infos = indexer.update_index_incremental(existing_infos)
        if infos != existing_infos:
            indexer.save_to_csv(infos, str(csv_path))
    else:
        infos = indexer.build_index()
        indexer.save_to_csv(infos, str(csv_path))

    exts = sorted({fi.extension for fi in infos if not fi.is_directory and fi.extension})
    parser_reg = _load_parser_registry()
    ai_exts = sorted([e for e in exts if e in parser_reg and e != '.hwp'])

    _get_session(base)
    return IndexResponse(
        count=len(infos),
        extensions=exts,
        ai_readable_exts=ai_exts,
        base_path=base,
        cache_dir=str(cache_dir),
        csv_path=str(csv_path),
        safe_path=safe_path,
    )

@app.post("/search", response_model=SearchResponse)
def api_search(req: SearchRequest):
    sess = _get_session(req.base_path)
    keywords = sess.extract_keywords(req.query)

    from Langchain.Searchtool import advanced_search_pipeline

    indexer = StructuredIndex(req.base_path)
    from pathlib import Path
    cache_dir = get_cache_dir()
    safe_path = str(Path(req.base_path)).replace(':', '').replace('\\', '_').replace('/', '_')
    csv_path = cache_dir / f"structured_index_{safe_path}.csv"
    if csv_path.exists():
        infos = indexer.load_from_csv(str(csv_path))
    else:
        infos = indexer.build_index()
        indexer.save_to_csv(infos, str(csv_path))

    search_info = advanced_search_pipeline(req.query, infos, limit=200, llm_keywords=keywords)
    merged = search_info['results']

    allowed = set(req.allowed_exts or [])
    if allowed:
        merged = [i for i in merged if (not i.is_directory and i.extension in allowed)]

    items = [FileInfoDTO(
        path=i.path,
        name=i.name,
        extension=i.extension,
        size_bytes=int(i.size_bytes),
        is_directory=bool(i.is_directory),
        created_time=i.created_time,
        modified_time=i.modified_time,
    ) for i in merged]

    return SearchResponse(
        keywords=keywords,
        expanded_keywords=search_info['expanded_keywords'],
        extensions=search_info['extensions'],
        years=search_info['years'],
        items=items
    )

@app.post("/refine", response_model=SearchResponse)
def api_refine(req: RefineRequest):
    sess = _get_session(req.base_path)
    current_paths = req.current_items

    indexer = StructuredIndex(req.base_path)
    from pathlib import Path
    cache_dir = get_cache_dir()
    safe_path = str(Path(req.base_path)).replace(':', '').replace('\\', '_').replace('/', '_')
    csv_path = cache_dir / f"structured_index_{safe_path}.csv"
    infos = indexer.load_from_csv(str(csv_path)) if os.path.exists(csv_path) else indexer.build_index()
    info_by_path = {fi.path: fi for fi in infos}
    filtered_paths = sess.filter_results_by_keywords(current_paths, req.keywords)
    merged_infos: List[FileInfo] = [info_by_path[p] for p in filtered_paths if p in info_by_path]
    items = [FileInfoDTO(
        path=i.path,
        name=i.name,
        extension=i.extension,
        size_bytes=int(i.size_bytes),
        is_directory=bool(i.is_directory),
        created_time=i.created_time,
        modified_time=i.modified_time,
    ) for i in merged_infos]

    return SearchResponse(
        keywords=req.keywords,
        expanded_keywords=req.keywords,
        extensions=[],
        years=[],
        items=items
    )

class ModelSelectRequest(BaseModel):
    base_path: str
    model: str

@app.get("/ollama/models")
def api_ollama_models():
    try:
        out = subprocess.check_output(["ollama", "list"], stderr=subprocess.STDOUT, text=True)
        lines = [l.strip() for l in out.splitlines() if l.strip()]
        names: List[str] = []
        for i, line in enumerate(lines):
            if i == 0 and ("NAME" in line and "SIZE" in line):
                continue
            parts = line.split()
            if parts:
                names.append(parts[0])
        return {"models": names}
    except Exception as e:
        return {"models": [], "error": str(e)}

@app.post("/ollama/pull")
def api_ollama_pull(req: ModelSelectRequest):
    try:
        subprocess.check_call(["ollama", "pull", req.model])
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.post("/ollama/select")
def api_ollama_select(req: ModelSelectRequest):
    sess = SearchSession(req.base_path, model_name=req.model)
    _SESSIONS[req.base_path] = sess
    return {"ok": True, "model": req.model}

@app.post("/proceed")
def api_proceed(req: ProceedRequest):
    sess = _get_session(req.base_path)
    contents = sess.load_contents(req.paths)
    return {"loaded": list(contents.keys())}

@app.post("/qa", response_model=QAResponse)
def api_qa(req: QARequest):
    sess = _get_session(req.base_path)
    answer = sess.answer_with_context(req.question)
    return QAResponse(answer=str(answer))

def _sse_format(data: str, event: Optional[str] = None) -> str:
    lines = []
    if event:
        lines.append(f"event: {event}")
    for line in str(data).splitlines() or [""]:
        lines.append(f"data: {line}")
    lines.append("")
    return "\n".join(lines)

@app.get("/qa/stream")
def api_qa_stream(base_path: str, q: str):
    sess = _get_session(base_path)

    def gen():
        try:
            answer = str(sess.answer_with_context(q))
            chunk_size = 80
            for i in range(0, len(answer), chunk_size):
                yield _sse_format(answer[i:i+chunk_size])
            yield _sse_format("done", event="done")
        except Exception as e:
            yield _sse_format(f"error: {e}", event="error")

    return StreamingResponse(gen(), media_type="text/event-stream")

@app.get("/ollama/pull/stream")
def api_ollama_pull_stream(model: str):
    def gen():
        try:
            proc = subprocess.Popen(["ollama", "pull", model], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            if not proc.stdout:
                yield _sse_format("No output", event="error")
                return
            for line in proc.stdout:
                yield _sse_format(line.rstrip())
            code = proc.wait()
            if code == 0:
                yield _sse_format("ok", event="done")
            else:
                yield _sse_format(f"exit code {code}", event="error")
        except Exception as e:
            yield _sse_format(str(e), event="error")

    return StreamingResponse(gen(), media_type="text/event-stream")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8765"))
    uvicorn.run(app, host="127.0.0.1", port=port, reload=False)