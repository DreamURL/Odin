import os
import re
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Union

from Ollama_model import get_ollama_llm
from Langchain.Searchtool import file_system_search, preindex_path

class SearchSession:
    def __init__(self, base_path: str, model_name: str = "llama3:8b") -> None:
        self.base_path = base_path
        self.llm = get_ollama_llm(model_name)
        self.index_info = preindex_path(base_path)
        self.now_dt: datetime = datetime.now()

        self.selected_files: List[str] = []
        self.loaded_docs: Dict[str, str] = {}
        self._last_folder_suggestions = set()

    def suggest_subkeywords(self, paths: List[str], max_suggestions: int = 20) -> List[str]:
        """Extract frequently appearing tokens from file paths for sub-keyword suggestions"""
        file_counter: Dict[str, int] = {}
        file_token_seen_per_path: Dict[str, set[str]] = {}
        folder_tokens_set: set[str] = set()
        stopwords_kr = {"파일", "문서", "자료", "최종", "최종본", "사본", "수정", "최신", "버전", "보고", "보고서", "첨부"}
        stopwords_en = {"final", "copy", "new", "ver", "version", "doc", "file", "report", "draft"}

        for p in paths:
            base = os.path.splitext(os.path.basename(p))[0]
            tokens = [t for t in re.split(r"[^0-9A-Za-z가-힣]+", base) if t]
            per_path_seen: set[str] = set()
            for t in tokens:
                if t.isdigit():
                    continue
                t_norm = t.lower()
                if len(t_norm) < 2:
                    continue
                if t in stopwords_kr or t_norm in stopwords_en:
                    continue
                if t_norm not in per_path_seen:
                    file_counter[t] = file_counter.get(t, 0) + 1
                    per_path_seen.add(t_norm)

            parent = os.path.dirname(p)
            for part in re.split(r"[\\/]+", parent):
                if not part:
                    continue
                folder_tokens = [t for t in re.split(r"[^0-9A-Za-z가-힣]+", part) if t]
                for ft in folder_tokens:
                    if ft.isdigit():
                        continue
                    ft_norm = ft.lower()
                    if len(ft_norm) < 2:
                        continue
                    if ft in stopwords_kr or ft_norm in stopwords_en:
                        continue
                    folder_tokens_set.add(ft)

        filename_candidates = [t for t, c in file_counter.items() if c >= 2]
        filename_candidates_sorted = sorted(filename_candidates, key=lambda t: (-file_counter[t], t))

        folder_candidates_sorted = sorted(folder_tokens_set)

        merged: List[str] = []
        for t in filename_candidates_sorted:
            merged.append(t)
            if len(merged) >= max_suggestions:
                break
        if len(merged) < max_suggestions:
            for ft in folder_candidates_sorted:
                if ft not in merged:
                    merged.append(ft)
                    if len(merged) >= max_suggestions:
                        break

        self._last_folder_suggestions = set(folder_candidates_sorted)
        return merged

    def filter_results_by_keywords(self, results: List[str], keywords: List[str]) -> List[str]:
        """Filter results using OR logic for keywords"""
        if not keywords:
            return results
        kws_norm = [k.strip() for k in keywords if k and k.strip()]
        if not kws_norm:
            return results
        filtered: List[str] = []
        for p in results:
            path_l = p.lower()
            base_l = os.path.splitext(os.path.basename(p))[0].lower()
            hit = False
            for k in kws_norm:
                k_l = k.lower()
                if k_l in path_l or k in p or k_l in base_l:
                    hit = True
                    break
            if hit:
                filtered.append(p)
        return filtered

    def extract_keywords(self, question: str) -> List[str]:
        """Extract core search keywords from question"""
        prompt = f"""
파일 검색을 위한 키워드만 추출하세요.

질문: "{question}"

현재 기준 시각(ISO8601): {self.now_dt.isoformat()}

규칙:
- 한국어 우선 3~5개의 핵심 키워드만 선택 (불릿/설명/레이블 금지)
- 불필요한 기호 제거(*, +, (), :, - 등)
- 동의어가 필요하면 한국어 위주로 포함, 영어는 최소화
- 출력은 반드시 JSON 배열 문자열로만 출력 (예: ["결혼","혼인","웨딩","신혼"]) 그 외 어떤 텍스트도 금지
"""

        try:
            resp = self.llm.invoke(prompt)
            raw = (resp or "").strip()
            json_text = None
            if "[" in raw and "]" in raw:
                try:
                    json_text = raw[raw.index("[") : raw.rindex("]") + 1]
                except Exception:
                    json_text = raw
            keywords: List[str] = []
            if json_text:
                try:
                    data = json.loads(json_text)
                    if isinstance(data, list):
                        keywords = [str(x) for x in data]
                except Exception:
                    pass
            if not keywords:
                parts = re.split(r"[\n,]+", raw)
                keywords = [p.strip().strip("\"'") for p in parts if p.strip()]

            cleaned: List[str] = []
            for k in keywords:
                k2 = self._normalize_keyword(k)
                if k2 and len(k2) > 1:
                    cleaned.append(k2)
            dedup = list(dict.fromkeys(cleaned))

            en_terms = self._extract_english_terms(question)
            if en_terms:
                for t in en_terms:
                    if t not in dedup:
                        dedup.append(t)
                ko_terms = self._translate_en_terms_to_ko(en_terms)
                for t in ko_terms:
                    t2 = self._normalize_keyword(t)
                    if t2 and t2 not in dedup:
                        dedup.append(t2)

            return dedup[:8] if dedup else [question]

        except Exception as e:
            return [question]

    def _normalize_keyword(self, s: str) -> str:
        """Remove bullets/labels/brackets/symbols and trim"""
        if not s:
            return ""
        s = s.strip()
        s = re.sub(r"^([*+\-•\d\.\)\(\s]+)", "", s)
        s = re.sub(r"^(유사어|동의어|영어키워드|영문|keyword|synonyms?)\s*:\s*", "", s, flags=re.I)
        s = re.sub(r"[()\[\]{}]", " ", s)
        s = re.sub(r"\s+", " ", s).strip()
        s = s.strip("'\" :+,-")
        return s

    def _extract_english_terms(self, text: str) -> List[str]:
        """Extract English keyword candidates from text"""
        import re
        tokens = [t for t in re.split(r"[^A-Za-z0-9]+", text) if t]
        stop_en = {"the","and","or","a","an","to","for","of","on","in","at","by","with","from","is","are","be","this","that","it","as","we","you","they","new","final","ver","version","doc","file","report","draft"}
        out: List[str] = []
        seen = set()
        for t in tokens:
            if t.isdigit():
                continue
            tl = t.lower()
            if len(tl) < 2:
                continue
            if tl in stop_en:
                continue
            if tl not in seen:
                seen.add(tl)
                out.append(t)
        return out[:5]

    def _translate_en_terms_to_ko(self, terms: List[str]) -> List[str]:
        """Translate English keywords to Korean search keywords"""
        if not terms:
            return []
        import json
        prompt = (
            "다음 영문 키워드들을 한국어 검색 키워드로 번역하세요.\n"
            "- 각 항목마다 한국어로 1~2개의 적절한 검색 키워드를 제시합니다.\n"
            "- 불필요한 설명 없이 JSON 배열 문자열만 출력합니다. 예: [\"계약\", \"매출\"]\n"
            f"영문 키워드: {json.dumps(terms, ensure_ascii=False)}"
        )
        try:
            resp = self.llm.invoke(prompt)
            raw = (resp or "").strip()
            json_text = None
            if "[" in raw and "]" in raw:
                try:
                    json_text = raw[raw.index("[") : raw.rindex("]") + 1]
                except Exception:
                    json_text = raw
            if json_text:
                try:
                    data = json.loads(json_text)
                    if isinstance(data, list):
                        return [str(x) for x in data if str(x).strip()]
                except Exception:
                    pass
            parts = re.split(r"[\n,]+", raw)
            return [p.strip().strip("\"'") for p in parts if p.strip()]
        except Exception:
            return []

    def initial_search(self, keywords: Union[str, List[str]], limit: int = 200, reindex: bool = False) -> List[str]:
        """Multi-keyword search with fallback"""
        import json

        if isinstance(keywords, str):
            keywords = [keywords]

        total_results = []
        used_keywords = []

        for i, keyword in enumerate(keywords):
            keyword = self._normalize_keyword(keyword)

            try:
                action_input = {
                    "search_query": keyword,
                    "base_path": self.base_path,
                    "limit": limit,
                    "reindex": reindex if i == 0 else False,
                }
                results = file_system_search.run(json.dumps(action_input))

                parsed_results = []
                if isinstance(results, list):
                    parsed_results = results
                elif isinstance(results, str):
                    lines = [line.strip().strip("'\"") for line in results.splitlines() if line.strip()]
                    parsed_results = lines

                if parsed_results and len(parsed_results) > 0:
                    used_keywords.append(keyword)
                    total_results.extend(parsed_results)

                    if i == 0 and len(parsed_results) >= 10:
                        break

                    if len(total_results) >= 20:
                        break

            except Exception as e:
                continue

        unique_results = list(dict.fromkeys(total_results))
        return unique_results[:limit]

    def extract_year_filters(self, text: str) -> List[int]:
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
        years = list(dict.fromkeys(years))
        return years

    def filter_results_by_years(self, results: List[str], years: List[int]) -> List[str]:
        if not years:
            return results
        years_set = set(years)
        filtered: List[str] = []
        for p in results:
            try:
                mt = os.path.getmtime(p)
                y = datetime.fromtimestamp(mt).year
                if y in years_set:
                    filtered.append(p)
            except Exception:
                pass
        return filtered

    def extract_relative_day_flags(self, text: str) -> Dict[str, bool]:
        t = text.strip()
        return {
            "today": ("오늘" in t),
            "yesterday": ("어제" in t),
            "day_before_yesterday": ("그제" in t or "그저께" in t),
        }

    def filter_results_by_relative_days(self, results: List[str], flags: Dict[str, bool]) -> List[str]:
        if not any(flags.values()):
            return results
        today = self.now_dt.date()
        yest = today - timedelta(days=1)
        dbf = today - timedelta(days=2)
        allowed_dates = set()
        if flags.get("today"):
            allowed_dates.add(today)
        if flags.get("yesterday"):
            allowed_dates.add(yest)
        if flags.get("day_before_yesterday"):
            allowed_dates.add(dbf)
        filtered: List[str] = []
        for p in results:
            try:
                mt = os.path.getmtime(p)
                d = datetime.fromtimestamp(mt).date()
                if d in allowed_dates:
                    filtered.append(p)
            except Exception:
                pass
        return filtered

    def choose_files_cli(self, results: List[str]) -> List[str]:
        if not results:
            return []

        for i, path in enumerate(results, 1):
            print(f"{i}. {path}")

        sel = input("선택할 번호 (쉼표로 구분) 또는 Enter로 건너뛰기 >> ").strip()
        if not sel:
            return []
        idxs = []
        for t in sel.split(','):
            t = t.strip()
            if t.isdigit():
                idx = int(t)
                if 1 <= idx <= len(results):
                    idxs.append(idx)
        chosen = [results[i-1] for i in idxs]
        self.selected_files = chosen
        return chosen

    def load_contents(self, paths: List[str]) -> Dict[str, str]:
        """Load and parse file contents"""
        from Langchain.Searchtool import PARSER_MAPPING
        contents: Dict[str, str] = {}

        for p in paths:
            if not os.path.isfile(p):
                continue
            ext = os.path.splitext(p)[1].lower()
            parser = PARSER_MAPPING.get(ext)
            if not parser:
                continue
            try:
                text = parser(p) or ""
                if text:
                    contents[p] = text
            except Exception as e:
                text = ""

        self.loaded_docs = contents
        return contents

    def answer_with_context(self, user_question: str) -> str:
        """Answer using loaded document content as context"""
        if not self.loaded_docs:
            return "(선택된 파일 내용이 없습니다. 먼저 파일을 선택하고 읽어주세요.)"
        context_blocks = []
        for path, text in self.loaded_docs.items():
            snippet = text[:3000]
            context_blocks.append(f"[FILE]{path}\n{text[:3000]}")
        context = "\n\n".join(context_blocks)
        prompt = (
            "다음은 사용자가 선택하여 제공한 문서들입니다. 문서 내용만 근거로 삼아 한국어로만 답변하세요.\n"
            "- 반드시 한국어(한글)로만 출력하세요. 영어 문장/단어를 불필요하게 포함하지 마세요.\n"
            "- 답변은 간결하고 정확하게 서술하세요.\n"
            "- 필요하면 관련 파일명을 함께 언급하세요.\n"
            f"문서들:\n{context}\n\n질문: {user_question}\n\n한국어 답변:"
        )
        try:
            return self.llm.invoke(prompt)
        except Exception as e:
            return f"LLM 호출 실패: {e}"

def run_interactive_flow(base_path: str):
    """Interactive CLI flow for search and Q&A"""
    sess = SearchSession(base_path)

    while True:
        question = input("\n[질문 입력] (종료: exit) >> ").strip()
        if not question or question.lower() in ("exit", "quit", "q"):
            print("세션을 종료합니다.")
            return

        sess.loaded_docs = {}

        keywords = sess.extract_keywords(question)
        print(f"[키워드] {', '.join(keywords)}")

        results = sess.initial_search(keywords)
        if results and isinstance(results, list):
            results = [r for r in results if not r.startswith("해당 키워드를") and os.path.exists(r)]

        years = sess.extract_year_filters(question)
        if years:
            results = sess.filter_results_by_years(results, years)
        day_flags = sess.extract_relative_day_flags(question)
        if any(day_flags.values()):
            results = sess.filter_results_by_relative_days(results, day_flags)

        print("\n[검색 결과]")
        if not results:
            print("검색 결과가 없습니다. 다른 질문을 입력해보세요.")
            continue
        else:
            for r in results[:50]:
                print(r)
            if len(results) > 50:
                print(f"... (총 {len(results)}건, 상위 50건만 표시)")

        while True:
            choice = input("\n[세부키워드]로 간추릴까요, 아니면 [여기서 진행]? (sub/proceed, 종료: exit) >> ").strip().lower()
            if choice in ("exit", "quit"):
                print("세션을 종료합니다.")
                return
            if choice in ("proceed", "p", "go", "여기서 진행"):
                break

            if choice in ("sub", "r", "refine", "세부", "세부키워드"):
                suggestions = sess.suggest_subkeywords(results, max_suggestions=20)
                if suggestions:
                    print("\n[세부 키워드 후보]")
                    for i, s in enumerate(suggestions, 1):
                        mark = " (폴더)" if s in sess._last_folder_suggestions else ""
                        print(f"{i}. {s}{mark}")
                else:
                    print("\n세부 키워드 후보를 찾지 못했습니다. 직접 키워드를 입력해 주세요.")

                sel = input("선택할 번호(쉼표) 또는 직접 키워드(쉼표로 복수 입력 가능). 예: 1,3,계약,모집 >> ").strip()
                if not sel:
                    print("선택이 없어 간추리기를 건너뜁니다.")
                    continue

                selected_keywords: List[str] = []
                parts = [x.strip() for x in re.split(r"[,\s]+", sel) if x.strip()]
                for part in parts:
                    if part.isdigit() and suggestions:
                        idx = int(part)
                        if 1 <= idx <= len(suggestions):
                            selected_keywords.append(suggestions[idx - 1])
                    else:
                        selected_keywords.append(part)

                narrowed = sess.filter_results_by_keywords(results, selected_keywords)
                if not narrowed:
                    print("\n해당 키워드로 일치하는 파일이 없습니다. 이전 결과를 유지합니다.")
                else:
                    results = narrowed
                    print(f"\n간추린 결과: 총 {len(results)}건")
                    for r in results[:50]:
                        print(r)
                    if len(results) > 50:
                        print(f"... (총 {len(results)}건, 상위 50건만 표시)")
                continue

            print("입력을 이해하지 못했습니다. 'sub' 또는 'proceed'를 입력해 주세요.")

        chosen = sess.choose_files_cli(results)
        if not chosen:
            print("선택된 파일이 없습니다. 다른 질문을 이어서 하실 수 있습니다.")
            continue

        contents = sess.load_contents(chosen)
        if not contents:
            print("파일 내용을 불러오지 못했습니다. 다른 질문을 이어서 하실 수 있습니다.")
            continue

        print("\n내용을 확인했습니다. 무엇을 도와드릴까요?")

        while True:
            q = input("\n[후속 질문] (검색으로 돌아가기: back, 종료: exit) >> ").strip()
            if q.lower() in ("exit", "quit"):
                print("세션을 종료합니다.")
                return
            if q.lower() in ("back", "b"):
                break
            ans = sess.answer_with_context(q)
            print("\n[답변]\n" + str(ans))