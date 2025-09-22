import os
import sys
import json
import re
from datetime import datetime
from typing import Any, Dict, List, Tuple, Optional
from langchain.tools import tool

from parsers.Parser_txt import parse_txt
from parsers.Parser_word import parse_word
from parsers.Parser_pdf import parse_pdf
from parsers.Parser_excel import parse_excel
from parsers.Parser_csv import parse_csv
from parsers.Parser_pptx import parse_pptx
from parsers.Parser_hwp import parse_hwp

PARSER_MAPPING = {
    '.txt': parse_txt, '.md': parse_txt, '.docx': parse_word, '.pdf': parse_pdf,
    '.xlsx': parse_excel, '.xls': parse_excel, '.csv': parse_csv,
    '.pptx': parse_pptx, '.hwp': parse_hwp,
}

_structured_indexer = None

def get_structured_indexer():
    global _structured_indexer
    if _structured_indexer is None:
        try:
            from Langchain.structured_indexing import StructuredIndex
            _structured_indexer = StructuredIndex
        except ImportError:
            raise ImportError("StructuredIndex를 사용할 수 없습니다. structured_indexing 모듈을 확인해주세요.")
    return _structured_indexer

def _normalize_base_path(path: str) -> str:
    if not path:
        return path
    fixed = path.replace('\\', '/')
    if len(fixed) == 2 and fixed[1] == ':':
        fixed += '/'
    return fixed

def _extract_params(input_str: str, base_default: str):
    base_default = _normalize_base_path(base_default)
    params = {
        'search_query': '',
        'base_path': base_default,
        'limit': 200,
        'reindex': False,
    }
    s = (input_str or '').strip()
    if not s:
        return params

    start = s.find('{')
    end = s.rfind('}')
    if start != -1 and end != -1 and end > start:
        cand = s[start:end+1]
        cand = re.sub(r'(\"base_path\"\s*:\s*\")(.*?)(\")',
                      lambda m: m.group(1) + m.group(2).replace('\\\\', '/').replace('\\', '/') + m.group(3), cand)
        try:
            data = json.loads(cand)
            if isinstance(data, dict):
                if 'search_query' in data:
                    params['search_query'] = str(data.get('search_query') or '').strip()
                if 'base_path' in data:
                    bp = str(data.get('base_path') or '').strip()
                    params['base_path'] = _normalize_base_path(bp) or base_default
                if 'limit' in data:
                    try:
                        limit_value = data.get('limit')
                        if limit_value is not None:
                            params['limit'] = int(limit_value)
                    except Exception:
                        pass
                if 'reindex' in data:
                    try:
                        params['reindex'] = bool(data.get('reindex'))
                    except Exception:
                        pass
                return params
        except Exception:
            pass

    mq = re.search(r'\bsearch_query\b\s*:\s*[\"\']([^\"\']+)[\"\']', s)
    if mq:
        params['search_query'] = mq.group(1).strip()
    mb = re.search(r'\bbase_path\b\s*:\s*[\"\']([^\"\']+)[\"\']', s)
    if mb:
        params['base_path'] = _normalize_base_path(mb.group(1).strip()) or base_default
    ml = re.search(r'\blimit\b\s*:\s*(\d+)', s)
    if ml:
        try:
            params['limit'] = int(ml.group(1))
        except Exception:
            pass
    mri = re.search(r'\breindex\b\s*:\s*(true|false)', s, re.IGNORECASE)
    if mri:
        params['reindex'] = (mri.group(1).lower() == 'true')

    if not params['search_query']:
        params['search_query'] = s
    return params

def extract_extensions_from_query(query: str) -> List[str]:
    """Extract file extensions from query"""
    extensions = []
    ext_patterns = [
        r'\b(pdf|docx?|xlsx?|pptx?|txt|md|csv|hwp)\b',
        r'\b(pdf|마이크로소프트|excel|powerpoint|text|hwp)(?:\s*파일)?\b',
    ]

    korean_ext_map = {
        '문서': ['pdf', 'docx', 'doc'],
        '엑셀': ['xlsx', 'xls'],
        '파워포인트': ['pptx', 'ppt'],
        '텍스트': ['txt', 'md'],
        '한글': ['hwp']
    }

    query_lower = query.lower()

    for pattern in ext_patterns:
        matches = re.findall(pattern, query_lower)
        extensions.extend(matches)

    for korean, exts in korean_ext_map.items():
        if korean in query_lower:
            extensions.extend(exts)

    return list(set(extensions))

def expand_business_keywords(keywords: List[str]) -> List[str]:
    """Expand business domain keywords"""
    expansion_map = {
        '사업보고서': ['business_report', 'annual_report', '경영보고서', '연간보고서'],
        '계약서': ['contract', 'agreement', '계약', '협약'],
        '제안서': ['proposal', '제안', '기획서'],
        '회의록': ['meeting', 'minutes', '회의', '미팅'],
        '매뉴얼': ['manual', 'guide', '가이드', '지침'],
        '보고서': ['report', '리포트'],
        '계획': ['plan', 'planning', '계획서'],
        '분석': ['analysis', '리포트', 'report'],
        '예산': ['budget', '예산서'],
        '영업': ['sales', '매출', '세일즈']
    }

    expanded = keywords.copy()
    for keyword in keywords:
        if keyword in expansion_map:
            expanded.extend(expansion_map[keyword])
    return list(set(expanded))

def filter_by_extensions(file_infos, extensions: List[str]):
    """Filter by file extensions"""
    if not extensions:
        return file_infos

    ext_set = {f".{ext.lower()}" for ext in extensions}
    return [info for info in file_infos if info.extension in ext_set]

def parse_date_from_iso(iso_string: str) -> int:
    """Extract year from ISO date string"""
    try:
        return datetime.fromisoformat(iso_string.replace('Z', '+00:00')).year
    except:
        return 0

def filter_by_years(file_infos, years: List[int]):
    """Filter by modification year"""
    if not years:
        return file_infos

    year_set = set(years)
    filtered = []
    for info in file_infos:
        file_year = parse_date_from_iso(info.modified_time)
        if file_year in year_set:
            filtered.append(info)
    return filtered

def extract_year_filters(text: str) -> List[int]:
    """Extract year filters from user text"""
    text = text.strip()
    years: List[int] = []
    now_y = datetime.now().year

    m = re.findall(r"(20\d{2})\s*년?", text)
    for y in m:
        try:
            yi = int(y)
            if 2000 <= yi <= now_y + 1:
                years.append(yi)
        except Exception:
            pass

    if "작년" in text:
        years.append(now_y - 1)
    if "올해" in text or "금년" in text:
        years.append(now_y)
    if "재작년" in text:
        years.append(now_y - 2)

    return list(dict.fromkeys(years))

def extract_meaningful_keywords(query: str) -> List[str]:
    """Extract meaningful keywords from query (stopword removal, filter word exclusion)"""
    korean_stopwords = {
        '파일', '파일을', '파일이', '파일에', '파일의', '파일은', '파일과', '파일을',
        '중에', '중에서', '에서', '에게', '에', '을', '를', '이', '가', '는', '은', '의', '와', '과',
        '찾아줘', '찾아', '찾기', '검색', '검색해', '검색해줘', '보여줘', '알려줘',
        '관련', '관련된', '관련있는', '관련이', '대한', '대해', '대해서',
        '작성된', '만든', '생성된', '저장된', '있는', '없는', '되는', '하는',
        '그', '그것', '이것', '저것', '여기', '거기', '저기',
        '때', '시', '때문에', '위해', '통해', '같은', '다른', '새로운', '기존',
        '모든', '전체', '일부', '몇', '여러', '다양한',
        '좀', '좀더', '조금', '많이', '전부', '다',
        '및', '또는', '또', '그리고', '하지만', '그러나', '그래서', '따라서'
    }

    english_stopwords = {
        'file', 'files', 'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
        'find', 'search', 'show', 'get', 'related', 'about', 'from', 'that', 'this', 'all', 'some', 'any'
    }

    time_words = {
        '올해', '작년', '재작년', '금년', '년', '월', '일', '시간', '때', '시기', '기간', '동안',
        '1월', '2월', '3월', '4월', '5월', '6월', '7월', '8월', '9월', '10월', '11월', '12월'
    }

    extension_words = {
        'pdf', 'docx', 'doc', 'xlsx', 'xls', 'pptx', 'ppt', 'txt', 'md', 'csv', 'hwp',
        '문서', '엑셀', '파워포인트', '텍스트', '한글', '마이크로소프트', 'excel', 'powerpoint', 'text'
    }

    exclude_words = korean_stopwords | english_stopwords | time_words | extension_words

    tokens = re.findall(r'[\w가-힣]+', query.lower())

    meaningful_keywords = []
    for token in tokens:
        if (re.match(r'^[가-힣]+$', token) and len(token) >= 2) or \
           (re.match(r'^[a-zA-Z]+$', token) and len(token) >= 3) or \
           (re.match(r'^[\w가-힣]+$', token) and len(token) >= 3):

            if token.isdigit():
                continue

            if token not in exclude_words:
                meaningful_keywords.append(token)

    seen = set()
    unique_keywords = []
    for keyword in meaningful_keywords:
        if keyword not in seen:
            seen.add(keyword)
            unique_keywords.append(keyword)

    return unique_keywords

def advanced_search_pipeline(query: str, file_infos, limit: int = 200, llm_keywords: Optional[List[str]] = None):
    """Advanced search pipeline with LLM-based keywords and AND/OR mixed logic"""
    extensions = extract_extensions_from_query(query)
    years = extract_year_filters(query)

    if llm_keywords:
        meaningful_keywords = llm_keywords
    else:
        meaningful_keywords = extract_meaningful_keywords(query)

    expanded_keywords = expand_business_keywords(meaningful_keywords)

    all_results = []

    for keyword in expanded_keywords:
        keyword_results = []
        for info in file_infos:
            if keyword.lower() in info.name.lower() or keyword.lower() in info.path.lower():
                keyword_results.append(info)

        keyword_results = filter_by_extensions(keyword_results, extensions)
        keyword_results = filter_by_years(keyword_results, years)

        all_results.extend(keyword_results)

    seen_paths = set()
    unique_results = []
    for info in all_results:
        if info.path not in seen_paths:
            seen_paths.add(info.path)
            unique_results.append(info)

    parseable = [info for info in unique_results if info.is_parseable]
    others = [info for info in unique_results if not info.is_parseable]

    final_results = parseable + others

    search_info = {
        'results': final_results[:limit],
        'expanded_keywords': expanded_keywords,
        'extensions': extensions,
        'years': years,
        'total_matches': len(unique_results)
    }

    return search_info

def preindex_path(base_path: str) -> Dict[str, Any]:
    """Prepare index (create or load cache)"""
    StructuredIndexClass = get_structured_indexer()

    try:
        from pathlib import Path

        work_dir = Path(__file__).parent.parent
        cache_dir = work_dir / ".odin_index"
        cache_dir.mkdir(exist_ok=True)

        safe_path = str(Path(base_path)).replace(':', '').replace('\\', '_').replace('/', '_')
        csv_path = cache_dir / f"structured_index_{safe_path}.csv"

        indexer = StructuredIndexClass(base_path)

        if csv_path.exists():
            file_infos = indexer.load_from_csv(str(csv_path))
        else:
            file_infos = indexer.build_index()
            indexer.save_to_csv(file_infos, str(csv_path))

        total_count = len(file_infos)
        parseable_count = sum(1 for info in file_infos if info.is_parseable)
        folder_count = sum(1 for info in file_infos if info.is_directory)
        file_count = sum(1 for info in file_infos if not info.is_directory)

        return {
            'base_path': _normalize_base_path(base_path),
            'count': total_count,
            'parseable_count': parseable_count,
            'folder_count': folder_count,
            'file_count': file_count,
            'source': 'structured',
            'file_infos': file_infos,
            'indexer': indexer,
        }
    except Exception as e:
        raise Exception(f"구조화 인덱싱 실패: {e}")

@tool
def file_system_search(input_data: str) -> list[str]:
    """
    Search files in the file system.
    input_data should be a JSON string containing search_query and base_path.
    Options: limit(int, default 200), reindex(bool, default false)
    Example: '{"search_query": "github", "base_path": "E:/", "limit": 200, "reindex": false}'
    """
    base_default = "E:/"
    params = _extract_params(input_data, base_default)
    search_query = params['search_query']
    base_path = params['base_path']
    limit = max(1, int(params.get('limit', 200)))
    reindex = bool(params.get('reindex', False))

    if not os.path.isdir(base_path):
        return [f"오류: '{base_path}'는 유효한 디렉토리가 아닙니다."]

    search_query_lower = (search_query or "").lower()
    if not search_query_lower:
        return ["오류: 검색어(search_query)가 비어 있습니다."]

    StructuredIndexClass = get_structured_indexer()

    try:
        from pathlib import Path

        work_dir = Path(__file__).parent.parent
        cache_dir = work_dir / ".odin_index"

        safe_path = str(Path(base_path)).replace(':', '').replace('\\', '_').replace('/', '_')
        csv_path = cache_dir / f"structured_index_{safe_path}.csv"

        if csv_path.exists() and not reindex:
            indexer = StructuredIndexClass(base_path)
            file_infos = indexer.load_from_csv(str(csv_path))

            search_info = advanced_search_pipeline(search_query, file_infos, limit)
            result_infos = search_info['results']

            if result_infos:
                results = [info.path for info in result_infos]
                return results
            else:
                return ["해당 키워드를 포함하는 파일/폴더를 찾지 못했습니다."]
        else:
            indexer = StructuredIndexClass(base_path)
            file_infos = indexer.build_index()
            indexer.save_to_csv(file_infos, str(csv_path))

            search_info = advanced_search_pipeline(search_query, file_infos, limit)
            result_infos = search_info['results']

            if result_infos:
                results = [info.path for info in result_infos]
                return results
            else:
                return ["해당 키워드를 포함하는 파일/폴더를 찾지 못했습니다."]

    except Exception as e:
        return [f"검색 실패: {e}"]