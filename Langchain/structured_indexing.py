#!/usr/bin/env python3
# 개선된 구조화 인덱싱 시스템

import os
import json
import csv
import re
from datetime import datetime
from typing import Any, Dict, List, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path

@dataclass
class FileInfo:
    """파일/폴더 정보 구조체"""
    path: str
    name: str
    parent_path: str
    is_directory: bool
    extension: str
    size_bytes: int
    created_time: str
    modified_time: str
    is_parseable: bool
    depth_level: int

class StructuredIndex:
    """구조화된 파일 인덱스"""
    
    def __init__(self, base_path: str):
        self.base_path = Path(base_path).resolve()
        self.parseable_extensions = {'.txt', '.md', '.docx', '.pdf', '.xlsx', '.xls', '.csv', '.pptx', '.hwp'}
        self.exclude_dirs = {
            '.git', '.hg', '.svn', 'node_modules', '__pycache__', '.venv', 'venv', 'env',
            '.mypy_cache', '.ruff_cache', '$recycle.bin', 'system volume information', 'windows',
            'program files', 'program files (x86)', 'programdata', 'msocache', 'perflogs', 'recovery',
            'documents and settings'
        }
        
    def _get_file_info(self, path: Path, depth: int) -> Optional[FileInfo]:
        """개별 파일/폴더의 메타데이터 추출"""
        try:
            stat = path.stat()
            is_dir = path.is_dir()
            extension = path.suffix.lower() if not is_dir else ""
            
            return FileInfo(
                path=str(path),
                name=path.name,
                parent_path=str(path.parent),
                is_directory=is_dir,
                extension=extension,
                size_bytes=stat.st_size if not is_dir else 0,
                created_time=datetime.fromtimestamp(stat.st_ctime).isoformat(),
                modified_time=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                is_parseable=extension in self.parseable_extensions,
                depth_level=depth
            )
        except (OSError, PermissionError):
            return None
    
    def build_index(self) -> List[FileInfo]:
        """트리 구조로 파일 시스템 인덱싱"""
        file_infos = []
        
        def _walk_directory(current_path: Path, depth: int = 0):
            try:
                # 현재 디렉토리 정보 추가
                if depth > 0:  # 루트는 제외
                    dir_info = self._get_file_info(current_path, depth)
                    if dir_info:
                        file_infos.append(dir_info)
                
                # 하위 항목들 처리
                try:
                    items = list(current_path.iterdir())
                    # 폴더 먼저, 파일 나중에 정렬
                    dirs = [p for p in items if p.is_dir() and not any(p.name.lower().startswith(exc) for exc in self.exclude_dirs)]
                    files = [p for p in items if p.is_file()]
                    
                    # 폴더 재귀 탐색
                    for dir_path in sorted(dirs):
                        _walk_directory(dir_path, depth + 1)
                    
                    # 파싱 가능한 파일들을 먼저 추가
                    parseable_files = []
                    other_files = []
                    
                    for file_path in sorted(files):
                        file_info = self._get_file_info(file_path, depth + 1)
                        if file_info:
                            if file_info.is_parseable:
                                parseable_files.append(file_info)
                            else:
                                other_files.append(file_info)
                    
                    # 파싱 가능한 파일들을 먼저 추가
                    file_infos.extend(parseable_files)
                    file_infos.extend(other_files)
                    
                except PermissionError:
                    pass
                    
            except (OSError, PermissionError):
                pass
        
        print(f"📁 파일 시스템 스캔 시작: {self.base_path}")
        _walk_directory(self.base_path)
        
        # 통계 계산
        folders = sum(1 for info in file_infos if info.is_directory)
        files = sum(1 for info in file_infos if not info.is_directory)
        parseable = sum(1 for info in file_infos if info.is_parseable)
        
        print(f"✅ 구조화 인덱싱 완료: {len(file_infos)} 항목 (폴더: {folders}, 파일: {files}, 파싱가능: {parseable})")
        
        return file_infos
    
    def save_to_csv(self, file_infos: List[FileInfo], csv_path: str):
        """인덱스를 CSV 파일로 저장"""
        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'path', 'name', 'parent_path', 'is_directory', 'extension',
                'size_bytes', 'created_time', 'modified_time', 'is_parseable', 'depth_level'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for info in file_infos:
                writer.writerow({
                    'path': info.path,
                    'name': info.name,
                    'parent_path': info.parent_path,
                    'is_directory': info.is_directory,
                    'extension': info.extension,
                    'size_bytes': info.size_bytes,
                    'created_time': info.created_time,
                    'modified_time': info.modified_time,
                    'is_parseable': info.is_parseable,
                    'depth_level': info.depth_level
                })
    
    def load_from_csv(self, csv_path: str) -> List[FileInfo]:
        """CSV 파일에서 인덱스 로드"""
        file_infos = []
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    file_infos.append(FileInfo(
                        path=row['path'],
                        name=row['name'],
                        parent_path=row['parent_path'],
                        is_directory=row['is_directory'].lower() == 'true',
                        extension=row['extension'],
                        size_bytes=int(row['size_bytes']),
                        created_time=row['created_time'],
                        modified_time=row['modified_time'],
                        is_parseable=row['is_parseable'].lower() == 'true',
                        depth_level=int(row['depth_level'])
                    ))
        except (FileNotFoundError, ValueError, KeyError):
            pass
            
        return file_infos
    
    def search(self, file_infos: List[FileInfo], query: str, limit: int = 200) -> List[FileInfo]:
        """구조화된 인덱스에서 검색"""
        query_lower = query.lower()
        
        # 파싱 가능한 파일과 일반 파일 분리
        parseable_matches = []
        other_matches = []
        
        for info in file_infos:
            if query_lower in info.name.lower() or query_lower in info.path.lower():
                if info.is_parseable:
                    parseable_matches.append(info)
                else:
                    other_matches.append(info)
                
                if len(parseable_matches) + len(other_matches) >= limit:
                    break
        
        # 파싱 가능한 파일 우선 반환
        results = parseable_matches + other_matches
        return results[:limit]

    def check_index_freshness(self, existing_infos: List[FileInfo]) -> Tuple[List[str], List[str], List[str]]:
        """기존 인덱스와 현재 파일시스템을 비교하여 변경사항을 감지

        다음 변경을 감지합니다:
        - 새로 생성된 파일
        - 수정된 파일(수정시간, 크기, 생성시간 중 하나라도 변경)
        - 삭제된 파일(경로가 더 이상 존재하지 않음)

        Returns:
            Tuple[새로운 파일들, 수정된 파일들, 삭제된 파일들]
        """
        # 기존 인덱스에서 파일 경로와 (modified, size, created) 매핑 생성
        # 경로 비교는 OS 차이에 안전하도록 정규화(normcase + normpath)해서 수행
        def _norm(p: str) -> str:
            try:
                return os.path.normcase(os.path.normpath(p))
            except Exception:
                return p

        existing_files: Dict[str, Tuple[str, int, str]] = {}
        for info in existing_infos:
            if not info.is_directory:  # 파일만 체크
                # created_time, modified_time은 ISO 문자열, size는 int
                existing_files[_norm(info.path)] = (
                    info.modified_time,
                    int(info.size_bytes),
                    info.created_time,
                )

        # 현재 파일시스템 스캔: (modified, size, created)
        current_files: Dict[str, Tuple[str, int, str]] = {}

        def _scan_files(current_path: Path):
            try:
                for item in current_path.iterdir():
                    if item.is_dir():
                        # 제외 디렉토리 체크
                        if not any(item.name.lower().startswith(exc) for exc in self.exclude_dirs):
                            _scan_files(item)
                    else:
                        try:
                            stat = item.stat()
                            modified_time = datetime.fromtimestamp(stat.st_mtime).isoformat()
                            created_time = datetime.fromtimestamp(stat.st_ctime).isoformat()
                            size_bytes = int(stat.st_size)
                            current_files[_norm(str(item))] = (modified_time, size_bytes, created_time)
                        except (OSError, PermissionError):
                            continue
            except (OSError, PermissionError):
                pass

        _scan_files(self.base_path)

        # 변경사항 감지
        new_files: List[str] = []
        modified_files: List[str] = []
        deleted_files: List[str] = []

        # 새로운 파일과 수정된 파일 찾기
        for path, triple in current_files.items():
            if path not in existing_files:
                new_files.append(path)
            else:
                if existing_files[path] != triple:
                    modified_files.append(path)

        # 삭제된 파일 찾기
        for path in existing_files:
            if path not in current_files:
                deleted_files.append(path)

        return new_files, modified_files, deleted_files

    def update_index_incremental(self, existing_infos: List[FileInfo]) -> List[FileInfo]:
        """증분 업데이트: 변경된 파일들만 다시 인덱싱"""
        new_files, modified_files, deleted_files = self.check_index_freshness(existing_infos)

        def _norm(p: str) -> str:
            try:
                return os.path.normcase(os.path.normpath(p))
            except Exception:
                return p
        
        if not new_files and not modified_files and not deleted_files:
            print("인덱스가 최신 상태입니다. 업데이트가 필요하지 않습니다.")
            return existing_infos
        
        print(f"증분 업데이트 시작:")
        print(f"  - 새로운 파일: {len(new_files)}개")
        print(f"  - 수정된 파일: {len(modified_files)}개") 
        print(f"  - 삭제된 파일: {len(deleted_files)}개")
        
        # 기존 인덱스에서 삭제된 파일들과 수정된 파일들 제거
        files_to_remove = set(deleted_files + modified_files)
        files_to_remove_norm = {_norm(p) for p in files_to_remove}
        updated_infos: List[FileInfo] = []
        for info in existing_infos:
            if info.is_directory:
                # 존재하지 않는 디렉토리 제거
                try:
                    if Path(info.path).exists():
                        updated_infos.append(info)
                except (OSError, PermissionError):
                    # 접근 불가 디렉토리는 유지하지 않음
                    pass
            else:
                # 제거/수정 대상 파일 제외
                if _norm(info.path) not in files_to_remove_norm:
                    updated_infos.append(info)
        
        # 새로운 파일들과 수정된 파일들을 다시 인덱싱
        files_to_reindex = new_files + modified_files
        
        for file_path in files_to_reindex:
            try:
                path_obj = Path(file_path)
                if path_obj.exists() and path_obj.is_file():
                    # 파일의 depth 계산 (Windows 대소문자/구분자 차이 대응)
                    try:
                        rel = os.path.relpath(str(path_obj), str(self.base_path))
                    except Exception:
                        rel = None
                    if not rel or rel.startswith('..'):
                        # base_path 밖의 파일은 스킵
                        continue
                    depth = len(Path(rel).parts)
                    
                    file_info = self._get_file_info(path_obj, depth)
                    if file_info:
                        updated_infos.append(file_info)
            except (OSError, PermissionError):
                continue
        
        # 디렉토리 정보도 업데이트 (새로운 디렉토리들)
        existing_dirs = {info.path for info in updated_infos if info.is_directory}

        def _check_new_dirs(current_path: Path, depth: int = 0):
            try:
                if depth > 0 and str(current_path) not in existing_dirs:
                    dir_info = self._get_file_info(current_path, depth)
                    if dir_info:
                        updated_infos.append(dir_info)

                for item in current_path.iterdir():
                    if item.is_dir() and not any(item.name.lower().startswith(exc) for exc in self.exclude_dirs):
                        _check_new_dirs(item, depth + 1)
            except (OSError, PermissionError):
                pass

        _check_new_dirs(self.base_path)

        # 정규화 경로 기준으로 중복 제거 (최신 항목 우선)
        dedup: dict[str, FileInfo] = {}
        for fi in updated_infos:
            dedup[_norm(fi.path)] = fi
        updated_infos = list(dedup.values())

        # 경로별로 정렬 (기존 build_index와 동일한 순서 유지)
        updated_infos.sort(key=lambda x: (x.path, not x.is_directory))

        print(f"증분 업데이트 완료: 총 {len(updated_infos)}개 항목")
        return updated_infos

# 테스트 함수
def test_structured_index():
    """구조화 인덱싱 테스트"""
    base_path = "e:/coding/Odin"
    cache_dir = Path("e:/coding/Odin/.odin_index")
    cache_dir.mkdir(exist_ok=True)
    csv_path = cache_dir / "structured_index.csv"
    
    indexer = StructuredIndex(base_path)
    
    # 캐시가 있으면 로드, 없으면 새로 생성
    if csv_path.exists():
        print("기존 CSV 인덱스 로드 중...")
        file_infos = indexer.load_from_csv(str(csv_path))
    else:
        print("새 인덱스 생성 중...")
        file_infos = indexer.build_index()
        indexer.save_to_csv(file_infos, str(csv_path))
    
    # 통계 출력
    total_files = sum(1 for info in file_infos if not info.is_directory)
    total_dirs = sum(1 for info in file_infos if info.is_directory)
    parseable_files = sum(1 for info in file_infos if info.is_parseable)
    
    print(f"\n=== 인덱스 통계 ===")
    print(f"전체 항목: {len(file_infos)}")
    print(f"폴더: {total_dirs}")
    print(f"파일: {total_files}")
    print(f"파싱 가능한 파일: {parseable_files}")
    
    # 검색 테스트
    query = "py"
    results = indexer.search(file_infos, query, 10)
    
    print(f"\n=== 검색 결과: '{query}' ===")
    for i, info in enumerate(results, 1):
        file_type = "📁" if info.is_directory else ("📄" if info.is_parseable else "📋")
        size_str = f" ({info.size_bytes:,} bytes)" if not info.is_directory else ""
        print(f"{i:2d}. {file_type} {info.name}{size_str}")
        print(f"     {info.path}")

if __name__ == "__main__":
    test_structured_index()