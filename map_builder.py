# ============================================================
# map_builder.py
# 재난 대피 경로 안내 시스템 - 맵 파싱 및 그래프 구성 모듈
# 담당: 팀원 1 (민재)
#
# 실행 환경: VSCode / Python 3.9+
# 필요 라이브러리: 없음 (Python 기본 내장 모듈만 사용)
#
# 자료구조: 2D 배열, 그래프(인접 리스트), 딕셔너리
# 알고리즘: DFS(연결성 검증), 삽입 정렬(출구 거리 정렬)
#
# Input 데이터: building_map.txt — 직접 구성 (가천대학교 AI공학관 기반)
# ============================================================

import os

# 이동 가능한 셀 심볼
PASSABLE = {'.', 'R', 'X', 'E', 'S', 'F'}
# 탈출 목표 심볼
EXIT_SYMBOL = 'X'


# ============================================================
# 맵 로딩
# ============================================================

def load_map(filename="building_map.txt"):
    """
    building_map.txt를 읽어 2D 배열로 변환
    자료구조: 2D 배열 (list of list)
    """
    if not os.path.exists(filename):
        raise FileNotFoundError(f"맵 파일을 찾을 수 없습니다: {filename}")

    grid = []
    with open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            row = list(line.rstrip('\n'))
            if row:
                grid.append(row)

    if not grid:
        raise ValueError("맵 파일이 비어 있습니다.")

    return grid


# ============================================================
# 그래프 구성
# ============================================================

def build_graph(grid):
    """
    2D 배열을 인접 리스트 그래프로 변환
    이동 가능 셀(. R X E S F)만 노드로 포함
    자료구조: 딕셔너리 기반 인접 리스트
    반환: graph[(r, c)] = [(nr, nc), ...]
    """
    rows = len(grid)
    cols = len(grid[0])
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]

    graph = {}
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] not in PASSABLE:
                continue
            neighbors = []
            for dr, dc in directions:
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    if grid[nr][nc] in PASSABLE:
                        neighbors.append((nr, nc))
            graph[(r, c)] = neighbors

    return graph


# ============================================================
# DFS 연결성 검증
# ============================================================

def _dfs(graph, start, visited):
    """반복적 DFS — 재귀 깊이 제한 우회"""
    stack = [start]
    while stack:
        node = stack.pop()
        if node in visited:
            continue
        visited.add(node)
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                stack.append(neighbor)


def dfs_verify(grid, graph, exits):
    """
    DFS로 각 출구(X)가 그래프 내에서 연결 컴포넌트를 형성하는지 검증
    맵에 통로가 고립된 X가 없음을 확인
    자료구조: 스택(반복적 DFS)
    알고리즘: DFS (연결성 검증)
    반환: valid_exits (연결된 출구 목록), isolated (고립 출구 목록)
    """
    valid_exits = []
    isolated = []

    for exit_pos in exits:
        if exit_pos not in graph:
            isolated.append(exit_pos)
            continue

        visited = set()
        _dfs(graph, exit_pos, visited)

        # 같은 컴포넌트 내 다른 통로 셀이 존재하면 유효한 출구
        reachable_passable = [
            node for node in visited
            if node != exit_pos and grid[node[0]][node[1]] in PASSABLE
        ]
        if reachable_passable:
            valid_exits.append(exit_pos)
        else:
            isolated.append(exit_pos)

    return valid_exits, isolated


# ============================================================
# 삽입 정렬 — 출구 거리 정렬
# ============================================================

def _manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def sort_exits_by_distance(exits, start):
    """
    삽입 정렬로 출구 목록을 시작점 기준 맨해튼 거리순 정렬
    자료구조: 배열
    알고리즘: 삽입 정렬
    반환: 거리순 정렬된 출구 목록 (원본 변경 없이 새 리스트 반환)
    """
    sorted_exits = list(exits)
    for i in range(1, len(sorted_exits)):
        key = sorted_exits[i]
        key_dist = _manhattan(key, start)
        j = i - 1
        while j >= 0 and _manhattan(sorted_exits[j], start) > key_dist:
            sorted_exits[j + 1] = sorted_exits[j]
            j -= 1
        sorted_exits[j + 1] = key
    return sorted_exits


# ============================================================
# 출구 목록 추출
# ============================================================

def find_exits(grid):
    """맵에서 모든 X(계단/비상구) 위치 추출"""
    exits = []
    for r, row in enumerate(grid):
        for c, cell in enumerate(row):
            if cell == EXIT_SYMBOL:
                exits.append((r, c))
    return exits


# ============================================================
# 메인 빌드 함수
# ============================================================

def build_map(filename="building_map.txt", start=None):
    """
    맵 파일을 읽어 grid, graph, exits를 반환하는 메인 함수

    매개변수:
        filename : 맵 파일 경로
        start    : 시작 위치 (r, c). 주어지면 exits를 거리순 정렬

    반환:
        grid  : 2D 배열 (list of list)
        graph : 인접 리스트 딕셔너리 {(r,c): [(nr,nc), ...]}
        exits : X 위치 목록 (start 주어지면 거리순 정렬됨)
    """
    grid = load_map(filename)
    graph = build_graph(grid)
    exits = find_exits(grid)

    if not exits:
        raise ValueError("맵에 비상구(X)가 존재하지 않습니다.")

    valid_exits, isolated = dfs_verify(grid, graph, exits)

    if isolated:
        print(f"[경고] 고립된 출구 {len(isolated)}개 감지: {isolated}")

    if not valid_exits:
        raise ValueError("유효한 비상구가 없습니다 — 모든 출구가 고립되어 있습니다.")

    if start is not None:
        valid_exits = sort_exits_by_distance(valid_exits, start)

    return grid, graph, valid_exits


# ============================================================
# 직접 실행 (모듈 테스트)
# ============================================================

if __name__ == "__main__":
    MAP_FILE = os.path.join(os.path.dirname(__file__), "building_map.txt")

    print("=" * 50)
    print(" map_builder 모듈 테스트")
    print("=" * 50)

    grid, graph, exits = build_map(MAP_FILE)

    rows = len(grid)
    cols = len(grid[0]) if grid else 0
    passable_count = sum(1 for node in graph)
    print(f"맵 크기         : {rows} 행 × {cols} 열")
    print(f"이동 가능 노드  : {passable_count}개")
    print(f"비상구(X) 위치  : {exits}")
    print(f"인접 리스트 크기: {len(graph)}개 노드")
    print()

    # 임의의 시작점으로 거리순 정렬 테스트
    test_start = (1, 1)
    _, _, sorted_exits = build_map(MAP_FILE, start=test_start)
    print(f"시작점 {test_start} 기준 출구 거리 정렬:")
    for pos in sorted_exits:
        d = abs(pos[0] - test_start[0]) + abs(pos[1] - test_start[1])
        print(f"  {pos}  맨해튼 거리: {d}")
