# fire_spread.py

from collections import deque
import random

# 자료구조: 큐(deque)
# 자료구조: 2D 배열(fire_time)
# 알고리즘: BFS(화재 확산)
# 알고리즘: 그리디(확산 우선순위 결정)

WALL = "#"
EMPTY = "."
START = "S"
FIRE = "F"
EXIT = "E"

DIRECTIONS = [(-1, 0), (1, 0), (0, -1), (0, 1)]


def is_valid(grid, r, c):
    return 0 <= r < len(grid) and 0 <= c < len(grid[0])


def count_adjacent_walls(grid, r, c):
    wall_count = 0

    for dr, dc in DIRECTIONS:
        nr, nc = r + dr, c + dc

        if not is_valid(grid, nr, nc) or grid[nr][nc] == WALL:
            wall_count += 1

    return wall_count


ROOM = "R"

def get_random_fire_positions(grid, count=1):
    """
    화재 발생 후보 셀 중 count개를 중복 없이 랜덤 선택
    후보: 이동 가능한 모든 셀 (., S, R)
    """
    candidates = []

    for r in range(len(grid)):
        for c in range(len(grid[r])):
            if grid[r][c] in [EMPTY, START, ROOM]:
                candidates.append((r, c))

    if not candidates:
        return []

    return random.sample(candidates, min(count, len(candidates)))


def get_neighbors_by_greedy(grid, r, c):
    neighbors = []

    for dr, dc in DIRECTIONS:
        nr, nc = r + dr, c + dc

        if is_valid(grid, nr, nc) and grid[nr][nc] != WALL:
            wall_count = count_adjacent_walls(grid, nr, nc)
            neighbors.append((wall_count, nr, nc))

    neighbors.sort()
    return [(nr, nc) for wall_count, nr, nc in neighbors]


def simulate_fire_spread(grid, fire_positions):
    """
    fire_positions: 단일 튜플 (r, c) 또는 튜플 리스트 [(r,c), ...]
    다중 화재 지점을 BFS 큐에 동시에 넣어 동시 확산 처리
    """
    rows = len(grid)
    cols = len(grid[0])

    if isinstance(fire_positions, tuple):
        fire_positions = [fire_positions]

    INF = float('inf')
    fire_time = [[INF for _ in range(cols)] for _ in range(rows)]
    queue = deque()

    fire_log = {0: []}
    for fr, fc in fire_positions:
        fire_time[fr][fc] = 0
        queue.append((fr, fc))
        fire_log[0].append((fr, fc))

    print("=== 화재 확산 시뮬레이션 시작 ===")
    print(f"t=0: 화재 발생 위치 {fire_log[0]}")

    while queue:
        r, c = queue.popleft()
        current_time = fire_time[r][c]

        for nr, nc in get_neighbors_by_greedy(grid, r, c):
            if fire_time[nr][nc] == INF:
                fire_time[nr][nc] = current_time + 1
                queue.append((nr, nc))

                if current_time + 1 not in fire_log:
                    fire_log[current_time + 1] = []

                fire_log[current_time + 1].append((nr, nc))

    for time in sorted(fire_log.keys()):
        if time == 0:
            continue
        print(f"t={time}: 화재 확산 -> {fire_log[time]}")

    return fire_time, fire_log


def print_fire_map_at_time(grid, fire_time, t):
    print(f"\n=== t={t} 화재 상태 ===")

    for r in range(len(grid)):
        row = []

        for c in range(len(grid[r])):
            if fire_time[r][c] <= t:
                row.append("F")
            else:
                row.append(grid[r][c])

        print(" ".join(row))


def get_exit_fire_times(fire_time, exits):
    print("\n=== 출구 화재 도달 시간 ===")

    result = {}

    for exit_pos in exits:
        r, c = exit_pos
        t = fire_time[r][c]
        result[exit_pos] = t

        if t == float('inf'):
            print(f"출구 {exit_pos}: 화재 미도달")
        else:
            print(f"출구 도달 예상 시간: t={t} -> 출구 {exit_pos}")

    return result


def simulate_fire(grid, fire_count=1):
    """
    연동용 래퍼: 랜덤 화재 위치 fire_count개 선정 후 확산 시뮬레이션 실행
    반환: fire_time 2D 배열 (미도달 셀 = float('inf'))
    """
    fire_positions = get_random_fire_positions(grid, count=fire_count)
    if not fire_positions:
        rows, cols = len(grid), len(grid[0])
        return [[float('inf')] * cols for _ in range(rows)]
    fire_time, _ = simulate_fire_spread(grid, fire_positions)
    return fire_time