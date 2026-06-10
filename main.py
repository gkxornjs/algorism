import os
import copy
import random
import matplotlib
matplotlib.use('Agg')   # GUI 없는 환경에서 plt.show() 블로킹 방지
import numpy as np
from PIL import Image
from map_builder import build_map
from fire_spread import (
    simulate_fire,
    simulate_fire_spread,
    get_random_fire_positions,
    get_exit_fire_times,
)
from path_finder import get_escape_path, is_escape_possible, find_best_exit, parse_map
from evacuation import (
    create_evacuee_dict,
    update_evacuee_result,
    print_evacuation_statistics,
    quick_sort_escape_times,
    binary_search_time,
)

MAP_FILE = os.path.join(os.path.dirname(__file__), "building_map.txt")

PASSABLE = {'.', 'R', 'X', 'E', 'S', 'F'}


def pick_random_start(grid):
    candidates = [
        (r, c)
        for r, row in enumerate(grid)
        for c, cell in enumerate(row)
        if cell in ('.', 'R')
    ]
    return random.choice(candidates)


def set_start(grid, pos):
    r, c = pos
    grid[r][c] = 'S'


def run_integration_test():
    print("=" * 60)
    print(" 재난 대피 경로 안내 시스템 — 통합 테스트")
    print("=" * 60)

    # Step 1: 맵 로드
    grid, graph, exits = build_map(MAP_FILE)
    print(f"[1] 맵 로드 완료: {len(grid)}행 × {len(grid[0])}열")
    print(f"    비상구(X): {exits}")

    # Step 2: 시작 위치 설정
    start = pick_random_start(grid)
    set_start(grid, start)
    _, graph, exits = build_map(MAP_FILE, start=start)
    print(f"[2] 시작 위치: {start}")

    # Step 3: 화재 시뮬레이션 (화재 지점 2개)
    fire_time = simulate_fire(grid, fire_count=2)
    print(f"[3] 화재 확산 시뮬레이션 완료 (화재 지점 2곳)")
    get_exit_fire_times(fire_time, exits)

    # Step 4: 대피자 등록 (테스트용 3명)
    evacuee_list = [
        (1, "김민재", start),
        (2, "이태권", start),
        (3, "박지원", start),
    ]
    evacuees = create_evacuee_dict(evacuee_list)
    print(f"\n[4] 대피자 {len(evacuees)}명 등록 완료")

    # Step 5: 각 시간 t=0, 3, 6 에서 경로 탐색
    for t in [0, 3, 6]:
        print(f"\n{'─'*50}")
        print(f" t={t} 시점 탈출 경로 탐색")
        print(f"{'─'*50}")

        path, dist, possible = get_escape_path(grid, graph, fire_time, current_time=t)

        if possible and path:
            print(f"탈출 가능: 경로 길이 {dist}칸")
            print(f"경로 (처음 5칸): {path[:5]} ...")

            for eid in evacuees:
                evacuees = update_evacuee_result(evacuees, eid, path, fire_time)
        else:
            print("탈출 불가 — 모든 출구가 화재로 차단")

    # Step 6: 통계 출력
    print()
    print_evacuation_statistics(evacuees, target_time=20)

    print("\n[완료] 모든 모듈 연동 성공")


# ============================================================
# Streamlit UI (담당: 지원)
# 자료구조/알고리즘 모듈 시각화 — streamlit run main.py
# ============================================================

INF = float('inf')
PASSABLE_START = ('.', 'R')   # 사용자 시작 가능 셀

# README 색상 기준 (path_finder.visualize 색 체계 재사용)
C_WALL    = [0.20, 0.20, 0.20]   # 벽 (#)
C_FIRE    = [0.90, 0.30, 0.20]   # 화재 셀
C_START   = [0.20, 0.70, 0.40]   # 시작 (S)
C_EXIT    = [0.95, 0.75, 0.15]   # 비상구 (X)
C_ELEV    = [0.20, 0.50, 0.90]   # 엘리베이터 (E)
C_PATH    = [1.00, 0.60, 0.10]   # 최단 경로 (*)
C_VISITED = [0.75, 0.85, 1.00]   # A* 탐색 노드
C_FLOOR   = [0.96, 0.96, 0.96]   # 일반 통로
C_CHAR    = [0.55, 0.10, 0.80]   # 대피자(캐릭터) 현재 위치
C_TRAIL   = [0.80, 0.70, 0.92]   # 지나온 자취
C_FIREPT  = [0.65, 0.10, 0.05]   # 수동 지정 화재 발화점(시작 전 미리보기)

FIRE_OK = ('.', 'R')   # 수동 화재 지정 가능 셀


def load_base_map():
    """맵 1회 로드 — grid_base(원본), exits 반환."""
    grid_base, _graph, exits = build_map(MAP_FILE)
    return grid_base, exits


def make_grid_with_start(grid_base, start):
    """원본을 보존하기 위해 깊은 복사 후 시작 위치 'S' 표기 (렌더 마커용)."""
    grid = copy.deepcopy(grid_base)
    r, c = start
    if grid[r][c] in PASSABLE_START:
        grid[r][c] = 'S'
    return grid


def generate_fire(grid_base, fire_count):
    """랜덤 화재 발생 후 BFS 확산 시뮬레이션. fire_time/positions/log 반환."""
    positions = get_random_fire_positions(grid_base, count=fire_count)
    fire_time, fire_log = simulate_fire_spread(grid_base, positions)
    return fire_time, positions, fire_log


def build_color_array(grid, fire_time, path, start, exits, current_time,
                      char_pos=None, trail=None, fire_preview=None,
                      trail_on_top=False):
    """
    맵을 rows×cols×3 RGB(float 0~1) 배열로 변환.
    화재 도달은 현재 시각(current_time) 기준. 대피자(char_pos)·지나온 자취(trail)·
    예정 경로(path)·수동 화재 발화점(fire_preview)을 함께 그린다.
    trail_on_top=True면(탈출 완료 후) 자취를 화재 위에 그려 가려진 경로까지 보여준다.
    """
    rows, cols = len(grid), len(grid[0])
    path_set    = set(path) if path else set()
    trail_set   = set(trail) if trail else set()
    preview_set = set(fire_preview) if fire_preview else set()

    img = np.zeros((rows, cols, 3))
    for r in range(rows):
        for c in range(cols):
            cell = grid[r][c]
            pos  = (r, c)
            if cell == '#':
                img[r][c] = C_WALL
            elif char_pos is not None and pos == tuple(char_pos):
                img[r][c] = C_CHAR            # 대피자 현재 위치 (최우선)
            elif trail_on_top and pos in trail_set:
                img[r][c] = C_TRAIL           # 탈출 완료 후: 화재보다 우선해 경로 표시
            elif fire_time[r][c] <= current_time:
                img[r][c] = C_FIRE            # 현재 시각 기준 화재 도달
            elif pos in preview_set:
                img[r][c] = C_FIREPT          # 시작 전 수동 화재 발화점 미리보기
            elif cell == 'X':
                img[r][c] = C_EXIT
            elif pos in path_set:
                img[r][c] = C_PATH            # 지금 위치에서 출구까지 예정 경로
            elif pos in trail_set:
                img[r][c] = C_TRAIL           # 지나온 자취
            elif cell == 'S' or pos == tuple(start):
                img[r][c] = C_START
            elif cell == 'E':
                img[r][c] = C_ELEV
            else:
                img[r][c] = C_FLOOR
    return img


def build_map_image(grid, fire_time, path, start, exits, current_time, cell_px=12,
                    char_pos=None, trail=None, fire_preview=None, trail_on_top=False):
    """
    색상 배열을 셀당 cell_px 픽셀로 확대한 PIL 이미지로 변환.
    클릭 좌표 → 셀 매핑이 선형이 되도록 축/여백 없이 순수 픽셀로 렌더한다.
    """
    img = build_color_array(grid, fire_time, path, start, exits, current_time,
                            char_pos=char_pos, trail=trail, fire_preview=fire_preview,
                            trail_on_top=trail_on_top)
    arr = (img * 255).astype(np.uint8)
    big = np.repeat(np.repeat(arr, cell_px, axis=0), cell_px, axis=1)
    return Image.fromarray(big)


def _swatch(color, label):
    rgb = f"rgb({int(color[0]*255)},{int(color[1]*255)},{int(color[2]*255)})"
    return (f"<span style='display:inline-block;width:12px;height:12px;"
            f"background:{rgb};border:1px solid #999;"
            f"margin:0 4px -1px 8px'></span>{label}")


def legend_html():
    """클릭형 이미지에는 범례가 없으므로 HTML 색상 범례를 따로 그린다."""
    items = [
        (C_CHAR, '대피자'), (C_START, '시작(S)'), (C_EXIT, '비상구(X)'),
        (C_FIRE, '화재'), (C_PATH, '예정 경로'), (C_TRAIL, '지나온 길'),
        (C_ELEV, '엘리베이터(E)'), (C_WALL, '벽(#)'),
    ]
    return "".join(_swatch(c, l) for c, l in items)


def simulate_evacuees(grid_base, fire_time, exits, current_time, n=10):
    """
    랜덤 시작점 n명을 생성해 각자 최단 경로를 탐색하고
    evacuation 모듈로 성공/탈출시간을 기록한다.
    반환: evacuees dict, 성공 탈출시간 정렬 리스트
    """
    candidates = [
        (r, c)
        for r, row in enumerate(grid_base)
        for c, cell in enumerate(row)
        if cell in PASSABLE_START
    ]
    picks = random.sample(candidates, min(n, len(candidates)))

    evacuee_list = [(i + 1, f"대피자{i + 1}", pos) for i, pos in enumerate(picks)]
    evacuees = create_evacuee_dict(evacuee_list)

    for eid, data in evacuees.items():
        start = data["start_pos"]
        path, _dist, _exit, _vis = find_best_exit(
            grid_base, fire_time, start, exits, current_time
        )
        evacuees = update_evacuee_result(evacuees, eid, path or [], fire_time)

    escape_times = [
        d["escape_time"] for d in evacuees.values()
        if d["success"] and d["escape_time"] is not None
    ]
    sorted_times = quick_sort_escape_times(escape_times)
    return evacuees, sorted_times


def advance_simulation(grid_base, fire_time, exits):
    """
    (b) 실시간 재경로 — 매 스텝마다 '대피자 현재 위치 + 현재 화재 상황' 기준으로
    A*를 다시 돌려 한 칸 이동시키고 시각을 1 진행한다. session_state를 직접 갱신.
    """
    import streamlit as st
    t   = st.session_state["sim_time"]
    pos = tuple(st.session_state["char_pos"])
    exit_set = {tuple(e) for e in exits}

    # 이미 출구 도착 → 탈출 성공
    if pos in exit_set:
        st.session_state["char_state"] = "escaped"
        st.session_state["playing"] = False
        return

    # 현재 위치가 화재에 휩싸임 → 탈출 실패
    if fire_time[pos[0]][pos[1]] <= t:
        st.session_state["char_state"] = "trapped"
        st.session_state["playing"] = False
        return

    # ── 1) 안전 경로(도착 시점까지 화재 안전) 우선 탐색 ──
    path, dist, best_exit, visited = find_best_exit(
        grid_base, fire_time, pos, exits, t
    )
    if path and len(path) >= 2:
        st.session_state["plan_path"] = path
        st.session_state["plan_dist"] = dist
        st.session_state["best_exit"] = best_exit
        st.session_state["visited_n"] = len(visited) if visited else 0
        st.session_state["risky"] = False
        nxt = tuple(path[1])
        st.session_state["char_pos"] = nxt
        st.session_state["trail"].append(nxt)
        st.session_state["sim_time"] = t + 1
        if nxt in exit_set:
            st.session_state["char_state"] = "escaped"
            st.session_state["playing"] = False
        return

    # 이미 출구에 서 있던 경우(len==1) → 성공
    if path and tuple(path[-1]) in exit_set:
        st.session_state["char_state"] = "escaped"
        st.session_state["playing"] = False
        return

    # ── 2) 안전 경로 없음 → best-effort: 불 안 붙은 칸으로 출구 방향 한 칸 전진 ──
    #     실제로 둘러싸이거나 불에 닿을 때까지 계속 움직여 '막히는 과정'을 보여준다.
    st.session_state["plan_path"] = []
    st.session_state["best_exit"] = best_exit
    st.session_state["visited_n"] = 0
    st.session_state["risky"] = True

    trail = st.session_state["trail"]
    prev = tuple(trail[-2]) if len(trail) >= 2 else None
    nxt = _best_effort_next(grid_base, fire_time, pos, exits, t, prev=prev)
    if nxt is None:
        st.session_state["char_state"] = "trapped"
        st.session_state["playing"] = False
        return

    st.session_state["char_pos"] = nxt
    trail.append(nxt)
    st.session_state["sim_time"] = t + 1
    if nxt in exit_set:
        st.session_state["char_state"] = "escaped"
        st.session_state["playing"] = False


def _best_effort_next(grid, fire_time, pos, exits, t, prev=None):
    """
    안전 경로가 없을 때의 한 칸 선택. 현재 불타지 않는 이웃 칸 중
    가장 가까운 출구 방향으로 전진한다. 직전 칸으로의 즉시 후퇴는
    다른 선택지가 있으면 피한다. 갈 곳이 없으면 None(=고립).
    """
    rows, cols = len(grid), len(grid[0])
    r, c = pos

    def exit_dist(rr, cc):
        return min(abs(rr - er) + abs(cc - ec) for er, ec in exits)

    candidates = []
    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        nr, nc = r + dr, c + dc
        if not (0 <= nr < rows and 0 <= nc < cols):
            continue
        if grid[nr][nc] == '#':
            continue
        if fire_time[nr][nc] <= t:      # 현재 불타는 칸 제외
            continue
        candidates.append((nr, nc))

    if not candidates:
        return None

    non_back = [p for p in candidates if prev is None or p != prev]
    pool = non_back if non_back else candidates
    pool.sort(key=lambda p: exit_dist(*p))
    return pool[0]


def _init_sim_state(st):
    """시뮬레이션 관련 session_state 기본값 1회 초기화."""
    defaults = {
        "start": (50, 5),       # 기본 시작 위치(출구와 연결된 통로)
        "phase": "setup",       # setup(설정) | running(재생)
        "fire_mode": "랜덤",     # 랜덤 | 직접 지정
        "click_target": "내 위치",  # 직접 지정 모드에서 클릭이 무엇을 찍을지
        "manual_fires": [],     # 수동 화재 발화점 목록
        "playing": False,       # 자동 재생 여부
        "speed": 0.5,           # 한 스텝당 대기(초)
        "sim_time": 0,          # 경과 시각 t
        "char_pos": None,       # 대피자 현재 위치
        "char_state": "moving",  # moving | escaped | trapped
        "trail": [],            # 지나온 자취
        "plan_path": [],        # 현재 예정 경로
        "plan_dist": INF,
        "best_exit": None,
        "visited_n": 0,
        "risky": False,         # 안전 경로 없이 위험 이동(best-effort) 중인지
        "fire_time": None,      # 확산 시뮬레이션 결과
        "fire_positions": [],
        "evac_total": 0,        # 통계(시작 시 1회 고정)
        "evac_sorted": [],
        "last_click": None,     # 마지막으로 '처리한' 지도 클릭값 (중복 처리 방지)
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _start_simulation(st, grid_base, exits):
    """화재를 확정하고 재생 단계로 진입 — 통계도 이때 1회만 계산해 고정."""
    if st.session_state["fire_mode"] == "랜덤":
        positions = get_random_fire_positions(
            grid_base, count=st.session_state["fire_count"]
        )
        # 랜덤 모드: '시작'마다 내 위치도 통로/강의실 중 무작위로 새로 뽑음
        st.session_state["start"] = pick_random_start(grid_base)
    else:
        positions = list(st.session_state["manual_fires"])

    if not positions:
        st.warning("화재 발화점이 없습니다. 화재 지점을 1곳 이상 지정하세요.")
        return

    fire_time, _log = simulate_fire_spread(grid_base, positions)

    st.session_state["fire_time"] = fire_time
    st.session_state["fire_positions"] = positions
    st.session_state["phase"] = "running"
    st.session_state["sim_time"] = 0
    st.session_state["char_pos"] = st.session_state["start"]
    st.session_state["char_state"] = "moving"
    st.session_state["trail"] = [st.session_state["start"]]
    st.session_state["plan_path"] = []
    st.session_state["playing"] = True

    # 대피 통계는 시작 시 한 번만 계산해 고정(매 프레임 재추첨 방지)
    _evac, sorted_times = simulate_evacuees(grid_base, fire_time, exits, 0, n=10)
    st.session_state["evac_total"] = 10
    st.session_state["evac_sorted"] = sorted_times


def _reset_simulation(st):
    """재생 상태만 초기화하고 설정(시작점/화재 모드)은 유지."""
    st.session_state["phase"] = "setup"
    st.session_state["playing"] = False
    st.session_state["sim_time"] = 0
    st.session_state["char_pos"] = None
    st.session_state["char_state"] = "moving"
    st.session_state["trail"] = []
    st.session_state["plan_path"] = []
    st.session_state["fire_time"] = None


def render_streamlit_ui():
    import time
    import streamlit as st
    from streamlit_image_coordinates import streamlit_image_coordinates

    st.set_page_config(page_title="재난 대피 경로 시뮬레이터", layout="wide")
    st.title("🚨 재난 대피 경로 안내 시스템")
    st.caption("가천대학교 AI공학관 — 화재 확산 시 최단 탈출 경로 실시간 시뮬레이터")

    grid_base, exits = load_base_map()
    rows, cols = len(grid_base), len(grid_base[0])
    CELL_PX = 12   # 셀당 픽셀 (클릭 좌표 ↔ 셀 매핑 기준)

    _init_sim_state(st)
    phase = st.session_state["phase"]
    start = st.session_state["start"]

    # ── 사이드바: 설정 / 재생 컨트롤 ──
    with st.sidebar:
        st.header("⚙️ 시뮬레이션 설정")

        sr, sc = start
        st.subheader("📍 내 위치 (S)")
        st.success(f"행 {sr + 1}, 열 {sc + 1}")

        if phase == "setup":
            st.caption("👉 오른쪽 지도에서 통로/강의실 칸을 클릭하면 위치가 바뀝니다.")

            st.subheader("🔥 화재 설정")
            st.session_state["fire_mode"] = st.radio(
                "발화 방식", ["랜덤", "직접 지정"],
                index=0 if st.session_state["fire_mode"] == "랜덤" else 1,
                horizontal=True,
            )
            if st.session_state["fire_mode"] == "랜덤":
                st.session_state["fire_count"] = st.number_input(
                    "화재 지점 수", 1, 5, value=st.session_state.get("fire_count", 2),
                    step=1,
                )
            else:
                st.session_state["click_target"] = st.radio(
                    "지도 클릭 시 찍을 대상", ["내 위치", "화재 지점"],
                    index=0 if st.session_state["click_target"] == "내 위치" else 1,
                    horizontal=True,
                )
                st.caption(f"지정한 화재 발화점: {st.session_state['manual_fires']}")
                if st.button("화재 지점 초기화", use_container_width=True):
                    st.session_state["manual_fires"] = []
                    st.rerun()

            st.divider()
            if st.button("▶️ 시뮬레이션 시작", type="primary",
                         use_container_width=True):
                _start_simulation(st, grid_base, exits)
                st.rerun()

        else:  # running
            st.subheader("⏱️ 경과 시간")
            st.metric("t", st.session_state["sim_time"])
            st.session_state["speed"] = st.slider(
                "재생 속도", 0.1, 1.5, st.session_state["speed"], 0.1
            )
            st.caption("👈 빠름  ·  느림 👉")

            moving = st.session_state["char_state"] == "moving"
            b1, b2 = st.columns(2)
            if moving:
                label = "⏸️ 일시정지" if st.session_state["playing"] else "▶️ 재생"
                if b1.button(label, use_container_width=True):
                    st.session_state["playing"] = not st.session_state["playing"]
                    st.rerun()
                if b2.button("⏭️ 다음 단계", use_container_width=True,
                             disabled=st.session_state["playing"]):
                    advance_simulation(grid_base, st.session_state["fire_time"], exits)
                    st.rerun()
            if st.button("🔄 처음으로", use_container_width=True):
                _reset_simulation(st)
                st.rerun()

    # ── 현재 화재/경로 상태 준비 ──
    if phase == "running":
        fire_time = st.session_state["fire_time"]
        current_time = st.session_state["sim_time"]
        char_pos = st.session_state["char_pos"]
        trail = st.session_state["trail"]
        plan_path = st.session_state["plan_path"]
        fire_preview = None
    else:
        fire_time = [[INF] * cols for _ in range(rows)]
        current_time = 0
        char_pos = None
        trail = None
        plan_path = None
        fire_preview = (st.session_state["manual_fires"]
                        if st.session_state["fire_mode"] == "직접 지정" else None)

    grid = make_grid_with_start(grid_base, start)

    # ── 레이아웃: 좌(클릭 맵) / 우(경로·통계) ──
    col_map, col_info = st.columns([3, 2])

    with col_map:
        st.subheader(f"🗺️ 실시간 대피 맵  (t = {current_time})")
        pil = build_map_image(
            grid, fire_time, plan_path, start, exits, current_time, CELL_PX,
            char_pos=char_pos, trail=trail, fire_preview=fire_preview,
            trail_on_top=(st.session_state["char_state"] == "escaped"),
        )
        coords = streamlit_image_coordinates(pil, key="map_click")
        st.markdown(legend_html(), unsafe_allow_html=True)

        if phase == "setup":
            st.caption("지도의 통로(흰색)·강의실(R) 칸을 클릭하세요. "
                       "‘직접 지정’ 모드에선 클릭 대상(내 위치/화재)을 사이드바에서 고릅니다.")
            # 클릭 → 셀 매핑. 컴포넌트는 같은 클릭값을 rerun마다 다시 돌려주므로
            # '새 클릭'일 때만 처리한다(중복 처리 = 화면 떨림/엉뚱한 반영의 원인).
            sig = tuple(sorted(coords.items())) if coords is not None else None
            if sig is not None and sig != st.session_state["last_click"]:
                st.session_state["last_click"] = sig
                cc = min(max(int(coords["x"] / coords["width"] * cols), 0), cols - 1)
                cr = min(max(int(coords["y"] / coords["height"] * rows), 0), rows - 1)
                clicked = (cr, cc)
                manual_fire = (st.session_state["fire_mode"] == "직접 지정"
                               and st.session_state["click_target"] == "화재 지점")
                if manual_fire:
                    if grid_base[cr][cc] in FIRE_OK:
                        fires = st.session_state["manual_fires"]
                        if clicked in fires:
                            fires.remove(clicked)   # 다시 클릭하면 해제
                        else:
                            fires.append(clicked)
                        st.rerun()
                    else:
                        st.warning(f"({cr + 1}, {cc + 1})은(는) 화재를 둘 수 없는 칸입니다.")
                elif clicked != start:
                    if grid_base[cr][cc] in PASSABLE_START:
                        st.session_state["start"] = clicked
                        st.rerun()
                    else:
                        st.warning(f"({cr + 1}, {cc + 1})은(는) 이동할 수 없는 칸입니다. "
                                   "통로/강의실을 클릭하세요.")
        else:
            st.caption("▶️ 재생 중에는 지도 클릭이 비활성화됩니다. "
                       "위치/화재를 바꾸려면 ‘처음으로’를 누르세요.")

    with col_info:
        if phase == "setup":
            st.info("👈 위치와 화재를 설정한 뒤 **시뮬레이션 시작**을 누르세요.")
            st.markdown(
                "- **랜덤**: 화재 지점 수만 정하면 무작위로 발화\n"
                "- **직접 지정**: 실제 상황처럼 화재 위치를 클릭으로 지정\n"
                "- 시작하면 대피자가 **매 순간 화재를 피해 경로를 다시 잡으며** 탈출합니다."
            )
            return

        # ── 재생 단계: 대피자 상태 ──
        st.subheader("🧭 대피 진행")
        state = st.session_state["char_state"]
        t = st.session_state["sim_time"]
        if state == "escaped":
            st.success(f"탈출 성공 ✅ — {t}초 만에 비상구 도착")
        elif state == "trapped":
            st.error(f"탈출 실패 ❌ — 화재에 가로막힘 (t={t})")
        elif st.session_state["risky"]:
            st.warning("⚠️ 안전 경로 없음 — 화재를 피해 탈출 시도 중…")
        else:
            remain = max(len(st.session_state["plan_path"]) - 1, 0)
            st.info(f"🟣 대피 중 — 출구까지 약 {remain}칸 남음")

        best_exit = st.session_state["best_exit"]
        m1, m2, m3 = st.columns(3)
        m1.metric("이동한 거리", f"{max(len(st.session_state['trail']) - 1, 0)} 칸")
        m2.metric("목표 출구", f"{best_exit}" if best_exit else "—")
        if best_exit:
            fa = st.session_state["fire_time"][best_exit[0]][best_exit[1]]
            m3.metric("출구 화재 도달", "안전" if fa == INF else f"t={int(fa)}")
        else:
            m3.metric("출구 화재 도달", "—")
        st.caption(f"이번 스텝 A* 탐색 노드: {st.session_state['visited_n']}개  ·  "
                   f"화재 발화점: {st.session_state['fire_positions']}")

        st.divider()
        st.subheader("📊 전체 대피 통계 (랜덤 10명)")
        st.caption("시작 시점에 무작위 10명을 배치해 각자 최단 경로로 탈출시킨 결과입니다.")
        sorted_times = st.session_state["evac_sorted"]
        total = st.session_state["evac_total"]
        success = len(sorted_times)
        target_time = st.slider("목표 탈출 시간(초)", 0, 50, value=20, key="target_t")
        st.caption("👆 이 시간 안에 몇 명이 빠져나갔는지(이진 탐색) 확인하는 기준입니다.")
        under = binary_search_time(sorted_times, target_time)
        avg = sum(sorted_times) / success if success else 0.0

        s1, s2, s3 = st.columns(3)
        s1.metric("탈출 성공", f"{success}/{total}")
        s2.metric("평균 탈출시간", f"{avg:.1f}" if success else "—")
        s3.metric(f"t≤{target_time} 인원", f"{under}명")
        st.caption(f"탈출시간 정렬(퀵정렬): {sorted_times}")

    # ── 자동 재생: 한 프레임 보여준 뒤 한 스텝 진행하고 rerun ──
    if (phase == "running" and st.session_state["playing"]
            and st.session_state["char_state"] == "moving"):
        time.sleep(st.session_state["speed"])
        advance_simulation(grid_base, st.session_state["fire_time"], exits)
        st.rerun()


def _running_in_streamlit():
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        # suppress_warning: 터미널(python3 main.py) 모드의 ScriptRunContext 경고 억제
        return get_script_run_ctx(suppress_warning=True) is not None
    except Exception:
        return False


if __name__ == "__main__":
    if _running_in_streamlit():
        render_streamlit_ui()
    else:
        run_integration_test()
