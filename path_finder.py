# ============================================================
# path_finder.py
# 재난 대피 경로 안내 시스템 - 최적 대피 경로 탐색 모듈
# 담당: 팀원 3
#
# 실행 환경: VSCode / Python 3.9+
# 필요 라이브러리: matplotlib (pip install matplotlib)
#
# 자료구조: 우선순위 큐(heapq), 그래프(인접 리스트), 배열
# 알고리즘: A*(최단 경로 탐색), 유니온-파인드(연결성 확인)
#
# Input 데이터: RAW_MAP, FIRE_TIME — 직접 구성 (독립 실행용 테스트 데이터)
#              실제 실행 시 map_builder.py / fire_spread.py 에서 전달받음
# ============================================================

import heapq
import time
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import platform

# 한글 폰트 설정
if platform.system() == 'Darwin':
    plt.rcParams['font.family'] = 'AppleGothic'
elif platform.system() == 'Windows':
    plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False


# ============================================================
# 테스트 데이터 (팀원1 map_builder.py 연동 전 독립 실행용)
# 데이터 출처: 직접 구성
# ============================================================

RAW_MAP = [
    ['#', '#', '#', '#', '#', '#', '#', '#'],
    ['#', 'S', '.', '.', '#', '.', '.', '#'],
    ['#', '.', '#', '.', '#', '.', '#', '#'],
    ['#', '.', '.', '.', 'F', '.', '.', '#'],
    ['#', '#', '.', '#', '#', '.', '#', '#'],
    ['#', '.', '.', '.', '.', '.', 'E', '#'],
    ['#', '#', '#', '#', '#', '#', '#', '#'],
]

# fire_time[r][c] = 화재가 해당 셀에 도달하는 시간
# (팀원2 fire_spread.py 연동 전 직접 설정)
# INF = 화재 미도달
INF = float('inf')
FIRE_TIME = [
    [INF, INF, INF, INF, INF, INF, INF, INF],
    [INF, INF,  6,   7,  INF,  5,   4,  INF],
    [INF,  7,  INF,  5,  INF,  4,  INF, INF],
    [INF,  6,   5,   4,   0,   1,   2,  INF],
    [INF, INF,  4,  INF, INF,  2,  INF, INF],
    [INF,  5,   4,   3,   2,   1,   3,  INF],
    [INF, INF, INF, INF, INF, INF, INF, INF],
]


# ============================================================
# 유니온-파인드 (Union-Find)
# 자료구조: 배열 (parent, rank)
# 알고리즘: 유니온-파인드 (연결성 실시간 확인)
# ============================================================

class UnionFind:
    def __init__(self, n):
        self.parent = list(range(n))
        self.rank   = [0] * n

    def find(self, x):
        # 경로 압축 (Path Compression)
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, x, y):
        px, py = self.find(x), self.find(y)
        if px == py:
            return
        # 랭크 기반 합치기 (Union by Rank)
        if self.rank[px] < self.rank[py]:
            px, py = py, px
        self.parent[py] = px
        if self.rank[px] == self.rank[py]:
            self.rank[px] += 1

    def connected(self, x, y):
        return self.find(x) == self.find(y)


def build_union_find(grid, fire_time, current_time):
    """
    현재 시간(current_time) 기준으로
    화재가 없는 통로 셀만 유니온-파인드로 연결
    자료구조: 유니온-파인드
    알고리즘: 유니온-파인드 (연결성 확인)
    """
    rows, cols = len(grid), len(grid[0])
    uf = UnionFind(rows * cols)

    def idx(r, c):
        return r * cols + c

    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == '#':
                continue
            # 화재 도달 셀 제외
            if fire_time[r][c] <= current_time:
                continue
            # 오른쪽, 아래 방향으로 연결
            for dr, dc in [(0, 1), (1, 0)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    if grid[nr][nc] != '#' and fire_time[nr][nc] > current_time:
                        uf.union(idx(r, c), idx(nr, nc))
    return uf


def is_escape_possible(grid, fire_time, start, exits, current_time):
    """
    유니온-파인드로 출구까지 연결 여부 확인
    알고리즘: 유니온-파인드 (연결성 확인)
    """
    rows, cols = len(grid), len(grid[0])
    uf = build_union_find(grid, fire_time, current_time)

    def idx(r, c):
        return r * cols + c

    sr, sc = start
    for er, ec in exits:
        if fire_time[er][ec] > current_time:  # 출구도 화재 미도달이어야 함
            if uf.connected(idx(sr, sc), idx(er, ec)):
                return True, (er, ec)
    return False, None


# ============================================================
# A* 알고리즘
# 자료구조: 우선순위 큐(heapq), 그래프(인접 리스트)
# 알고리즘: A* (최단 탈출 경로 탐색)
# ============================================================

def heuristic(a, b):
    """
    맨해튼 거리 휴리스틱
    그리드 맵에서 대각선 이동 없으므로 맨해튼 거리 사용
    알고리즘: A* 휴리스틱 함수
    """
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def astar(grid, fire_time, start, goal, current_time):
    """
    A* 알고리즘으로 start → goal 최단 경로 탐색
    화재 도달 셀은 이동 불가 처리 (가중치 무한대)
    자료구조: 우선순위 큐(heapq)
    알고리즘: A* (최단 경로 탐색)
    """
    rows, cols = len(grid), len(grid[0])
    directions = [(-1,0),(1,0),(0,-1),(0,1)]

    # 우선순위 큐: (f, g, (r, c))
    # 자료구조: 우선순위 큐(heapq)
    open_list = []
    heapq.heappush(open_list, (0, 0, start))

    g = {start: 0}
    came_from  = {start: None}
    visited    = set()
    visited_order = []   # 탐색 순서 기록 (시각화용)

    while open_list:
        f, g_cur, current = heapq.heappop(open_list)

        if current in visited:
            continue
        visited.add(current)
        visited_order.append(current)

        if current == goal:
            # 경로 복원
            path = []
            node = current
            while node is not None:
                path.append(node)
                node = came_from[node]
            return path[::-1], g[goal], visited_order

        r, c = current
        for dr, dc in directions:
            nr, nc = r + dr, c + dc
            if not (0 <= nr < rows and 0 <= nc < cols):
                continue
            if grid[nr][nc] == '#':
                continue

            new_g = g[current] + 1
            # 도착 시점(current_time + new_g) 기준으로 화재 여부 판단
            # current_time 기준으로만 체크하면 이동 중 화재에 따라잡히는 경우를 못 막음
            if fire_time[nr][nc] <= current_time + new_g:
                continue
            if new_g < g.get((nr, nc), INF):
                g[(nr, nc)] = new_g
                h = heuristic((nr, nc), goal)
                f_val = new_g + h
                heapq.heappush(open_list, (f_val, new_g, (nr, nc)))
                came_from[(nr, nc)] = current

    return None, INF, visited_order  # 경로 없음


# ============================================================
# 다중 출구 처리
# ============================================================

def find_best_exit(grid, fire_time, start, exits, current_time):
    """
    다중 출구 중 A*로 가장 가까운 출구 탐색
    알고리즘: A* (다중 출구 최적 선택)
    """
    best_path = None
    best_dist = INF
    best_exit = None
    best_visited = None

    for exit_pos in exits:
        path, dist, visited_order = astar(
            grid, fire_time, start, exit_pos, current_time
        )
        if path and dist < best_dist:
            best_dist     = dist
            best_path     = path
            best_exit     = exit_pos
            best_visited  = visited_order

    return best_path, best_dist, best_exit, best_visited


# ============================================================
# 맵 파싱 유틸
# ============================================================

def parse_map(grid):
    """맵에서 시작 위치, 화재 위치, 출구 위치 추출"""
    start  = None
    fire   = []
    exits  = []
    rows, cols = len(grid), len(grid[0])

    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == 'S':
                start = (r, c)
            elif grid[r][c] == 'F':
                fire.append((r, c))
            elif grid[r][c] == 'X':
                exits.append((r, c))
    return start, fire, exits


def print_map(grid, path=None, visited=None):
    """
    맵 출력
    - 최적 경로: * 표시
    - 탐색 노드: · 표시 (시각화용)
    """
    rows, cols = len(grid), len(grid[0])
    path_set    = set(path) if path else set()
    visited_set = set(visited) if visited else set()

    print()
    for r in range(rows):
        row_str = ''
        for c in range(cols):
            cell = grid[r][c]
            pos  = (r, c)
            if cell in ('S', 'E', 'F', '#'):
                row_str += cell + ' '
            elif pos in path_set:
                row_str += '* '
            elif pos in visited_set:
                row_str += '· '
            else:
                row_str += '. '
        print(row_str)
    print()


# ============================================================
# 시각화
# 자료구조: 2D 배열
# ============================================================

def visualize(grid, fire_time, path_a, visited_a, start, exits, current_time, title=""):
    """
    A* 탐색 결과 시각화
    - 파란색: 탐색한 노드
    - 주황색: 최단 경로
    - 빨간색: 화재 셀
    """
    rows, cols = len(grid), len(grid[0])

    color_map = []
    for r in range(rows):
        row = []
        for c in range(cols):
            cell = grid[r][c]
            pos  = (r, c)
            if cell == '#':
                row.append([0.2, 0.2, 0.2])       # 벽 (진회색)
            elif fire_time[r][c] <= current_time:
                row.append([0.9, 0.3, 0.2])        # 화재 (빨강)
            elif cell == 'S':
                row.append([0.2, 0.7, 0.4])        # 시작 (초록)
            elif cell == 'E':
                row.append([0.2, 0.5, 0.9])        # 출구 (파랑)
            elif path_a and pos in set(path_a):
                row.append([1.0, 0.6, 0.1])        # 경로 (주황)
            elif visited_a and pos in set(visited_a):
                row.append([0.75, 0.85, 1.0])      # 탐색 노드 (연파랑)
            else:
                row.append([0.95, 0.95, 0.95])     # 일반 통로 (흰색)
        color_map.append(row)

    fig, ax = plt.subplots(figsize=(cols * 0.9, rows * 0.9))
    ax.imshow(color_map, aspect='equal')

    # 셀 텍스트 표시
    path_set    = set(path_a) if path_a else set()
    visited_set = set(visited_a) if visited_a else set()

    for r in range(rows):
        for c in range(cols):
            cell = grid[r][c]
            pos  = (r, c)
            if cell == 'S':
                ax.text(c, r, 'S', ha='center', va='center',
                        fontsize=13, fontweight='bold', color='white')
            elif cell == 'E':
                ax.text(c, r, 'E', ha='center', va='center',
                        fontsize=13, fontweight='bold', color='white')
            elif cell == 'F' or fire_time[r][c] <= current_time:
                ax.text(c, r, 'F', ha='center', va='center',
                        fontsize=11, color='white')
            elif pos in path_set:
                ax.text(c, r, '*', ha='center', va='center',
                        fontsize=13, fontweight='bold', color='#333')
            elif pos in visited_set:
                ax.text(c, r, '·', ha='center', va='center',
                        fontsize=10, color='#666')

    # 그리드 선
    for x in range(cols + 1):
        ax.axvline(x - 0.5, color='gray', linewidth=0.5, alpha=0.5)
    for y in range(rows + 1):
        ax.axhline(y - 0.5, color='gray', linewidth=0.5, alpha=0.5)

    # 범례
    legend_els = [
        mpatches.Patch(color=[0.2, 0.7, 0.4], label='시작 (S)'),
        mpatches.Patch(color=[0.2, 0.5, 0.9], label='출구 (E)'),
        mpatches.Patch(color=[0.9, 0.3, 0.2], label='화재 셀'),
        mpatches.Patch(color=[1.0, 0.6, 0.1], label='최단 경로 (*)'),
        mpatches.Patch(color=[0.75, 0.85, 1.0], label='A* 탐색 노드'),
        mpatches.Patch(color=[0.2, 0.2, 0.2], label='벽 (#)'),
    ]
    ax.legend(handles=legend_els, loc='upper right',
              bbox_to_anchor=(1.35, 1.0), fontsize=9)
    ax.set_title(title, fontsize=13, fontweight='bold', pad=10)
    ax.axis('off')
    plt.tight_layout()
    plt.show()


# ============================================================
# 메인 실행
# ============================================================

def run(grid=None, fire_time=None, current_time=0):
    """
    path_finder 메인 실행 함수
    grid, fire_time 미입력 시 테스트 데이터 사용
    """
    if grid is None:
        grid = RAW_MAP
    if fire_time is None:
        fire_time = FIRE_TIME

    rows, cols = len(grid), len(grid[0])
    start, fire_pos, exits = parse_map(grid)

    print("=" * 50)
    print(" 최적 대피 경로 탐색 시스템")
    print("=" * 50)
    print(f"맵 크기     : {rows} x {cols}")
    print(f"시작 위치   : {start}")
    print(f"화재 위치   : {fire_pos}")
    print(f"출구 위치   : {exits}")
    print(f"현재 시간   : t={current_time}")
    print()

    # ── Step 1: 유니온-파인드로 연결성 확인 ──
    # 알고리즘: 유니온-파인드 (연결성 확인)
    print("[ Step 1 ] 유니온-파인드 연결성 확인...")
    t0 = time.perf_counter()
    possible, reachable_exit = is_escape_possible(
        grid, fire_time, start, exits, current_time
    )
    uf_time = time.perf_counter() - t0

    if not possible:
        print("❌ 탈출 불가 — 모든 출구가 화재로 차단되었습니다.")
        print_map(grid)
        return None

    print(f"✅ 연결성 확인 완료 — 출구 {reachable_exit}까지 경로 존재")
    print(f"   유니온-파인드 실행 시간: {uf_time*1000:.3f}ms")
    print()

    # ── Step 2: A*로 최단 경로 탐색 ──
    # 알고리즘: A* (최단 경로 탐색)
    print("[ Step 2 ] A* 최단 경로 탐색...")
    t0 = time.perf_counter()
    path, dist, best_exit, visited_order = find_best_exit(
        grid, fire_time, start, exits, current_time
    )
    astar_time = time.perf_counter() - t0

    if not path:
        print("❌ 탈출 불가 — 경로를 찾을 수 없습니다.")
        return None

    # ── 결과 출력 ──
    print(f"✅ 최적 경로 탐색 완료")
    print(f"   경로    : {' → '.join(str(p) for p in path)}")
    print(f"   이동 거리: {dist}칸")
    print(f"   탐색 노드: {len(visited_order)}개 / 전체 통로 노드")
    print(f"   실행 시간: {astar_time*1000:.3f}ms")
    print()

    # 화재 도달 전 탈출 가능 여부
    goal = path[-1]
    fire_arrival = fire_time[goal[0]][goal[1]]
    if dist < fire_arrival:
        print(f"✅ 탈출 가능 — 이동 거리 {dist}칸 < 화재 도달 t={fire_arrival}")
    else:
        print(f"⚠️  주의 — 이동 거리 {dist}칸 ≥ 화재 도달 t={fire_arrival}")

    # 맵 출력 (* = 경로, · = 탐색 노드)
    print("\n[ 대피 경로 맵 ]  (* = 최단 경로, · = A* 탐색 노드)")
    print_map(grid, path, visited_order)

    # 시각화
    visualize(
        grid, fire_time, path, visited_order,
        start, exits, current_time,
        title=f"A* 최단 대피 경로 탐색  (t={current_time})"
    )

    return path


# ============================================================
# 팀원2 연동 함수 (fire_spread.py에서 호출)
# ============================================================

def get_escape_path(grid, graph, fire_time, current_time=0):
    """
    연동용 함수: (path, dist, possible) 튜플 반환
    graph: map_builder 인접 리스트 (내부 미사용, 인터페이스 호환용)
    fire_time: fire_spread가 계산한 화재 도달 시간 2D 배열 (미도달=float('inf'))
    """
    _, _, exits = parse_map(grid)

    # parse_map이 출구를 못 찾으면 graph에서 추출
    if not exits and graph:
        exits = [pos for pos in graph if grid[pos[0]][pos[1]] == 'X']

    possible, _ = is_escape_possible(grid, fire_time, *_find_start(grid), exits, current_time)

    path = run(grid, fire_time, current_time)
    if path is None:
        return None, INF, False

    dist = len(path) - 1
    return path, dist, possible


def _find_start(grid):
    """grid에서 'S' 위치 반환"""
    for r, row in enumerate(grid):
        for c, cell in enumerate(row):
            if cell == 'S':
                return (r, c),
    return (0, 0),


# ============================================================
# 직접 실행
# ============================================================

if __name__ == "__main__":
    # 기본 실행 (t=0 기준)
    run()

    # 화재가 더 번진 상황 (t=3 기준)
    print("\n" + "=" * 50)
    print(" t=3 시점 — 화재 확산 후 재탐색")
    print("=" * 50)
    run(current_time=3)
