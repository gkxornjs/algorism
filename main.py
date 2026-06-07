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


def build_color_array(grid, fire_time, path, visited, start, exits, current_time):
    """
    맵을 rows×cols×3 RGB(float 0~1) 배열로 변환.
    path_finder.visualize의 색 체계 재사용. 화재 도달은 도착 시각(current_time) 기준.
    """
    rows, cols = len(grid), len(grid[0])
    path_set    = set(path) if path else set()
    visited_set = set(visited) if visited else set()

    img = np.zeros((rows, cols, 3))
    for r in range(rows):
        for c in range(cols):
            cell = grid[r][c]
            pos  = (r, c)
            if cell == '#':
                img[r][c] = C_WALL
            elif fire_time[r][c] <= current_time:
                img[r][c] = C_FIRE            # 현재 시각 기준 화재 도달
            elif cell == 'S' or pos == tuple(start):
                img[r][c] = C_START
            elif cell == 'X':
                img[r][c] = C_EXIT
            elif pos in path_set:
                img[r][c] = C_PATH
            elif pos in visited_set:
                img[r][c] = C_VISITED
            elif cell == 'E':
                img[r][c] = C_ELEV
            else:
                img[r][c] = C_FLOOR
    return img


def build_map_image(grid, fire_time, path, visited, start, exits, current_time, cell_px=12):
    """
    색상 배열을 셀당 cell_px 픽셀로 확대한 PIL 이미지로 변환.
    클릭 좌표 → 셀 매핑이 선형이 되도록 축/여백 없이 순수 픽셀로 렌더한다.
    """
    img = build_color_array(grid, fire_time, path, visited, start, exits, current_time)
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
        (C_START, '시작(S)'), (C_EXIT, '비상구(X)'), (C_FIRE, '화재'),
        (C_PATH, '최단경로'), (C_VISITED, 'A* 탐색'),
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


def render_streamlit_ui():
    import streamlit as st
    from streamlit_image_coordinates import streamlit_image_coordinates

    st.set_page_config(page_title="재난 대피 경로 시뮬레이터", layout="wide")
    st.title("🚨 재난 대피 경로 안내 시스템")
    st.caption("가천대학교 AI공학관 — 화재 확산 시 최단 탈출 경로 실시간 시뮬레이터")

    grid_base, exits = load_base_map()
    rows, cols = len(grid_base), len(grid_base[0])
    CELL_PX = 12   # 셀당 픽셀 (클릭 좌표 ↔ 셀 매핑 기준)

    # 시작 위치는 지도 클릭으로 갱신 — session_state에 보관
    if "start" not in st.session_state:
        st.session_state["start"] = (50, 5)   # 기본값: 출구와 연결된 통로

    # ── 사이드바: 사용자 입력 ──
    with st.sidebar:
        st.header("⚙️ 시뮬레이션 설정")

        sr, sc = st.session_state["start"]
        st.subheader("📍 현재 위치 (S)")
        st.success(f"행 {sr + 1}, 열 {sc + 1}")
        st.caption("👉 오른쪽 지도에서 통로/강의실 칸을 클릭하면 위치가 바뀝니다.")

        st.subheader("🔥 화재 발생")
        fire_count = st.number_input("화재 지점 수", 1, 5, value=2, step=1)
        if st.button("화재 발생 / 재발생", type="primary", use_container_width=True):
            fire_time, positions, fire_log = generate_fire(grid_base, fire_count)
            max_t = max(fire_log.keys()) if fire_log else 0
            st.session_state["fire_time"] = fire_time
            st.session_state["fire_positions"] = positions
            st.session_state["max_t"] = max_t

        st.subheader("⏱️ 시간")
        if "fire_time" in st.session_state:
            max_t = st.session_state.get("max_t", 0)
            current_time = st.slider("경과 시간 t", 0, max(max_t, 1), value=0)
        else:
            current_time = 0
            st.info("‘화재 발생’ 버튼을 눌러 시뮬레이션을 시작하세요.")

    start = st.session_state["start"]

    # ── 화재 상태 / 경로 탐색 (매 rerun) ──
    fire_present = "fire_time" in st.session_state
    if fire_present:
        fire_time = st.session_state["fire_time"]
        fire_positions = st.session_state["fire_positions"]
        possible, _ = is_escape_possible(grid_base, fire_time, start, exits, current_time)
        path, dist, best_exit, visited = find_best_exit(
            grid_base, fire_time, start, exits, current_time
        )
    else:
        fire_time = [[INF] * cols for _ in range(rows)]
        fire_positions = []
        possible, path, dist, best_exit, visited = False, None, INF, None, None

    grid = make_grid_with_start(grid_base, start)

    # ── 레이아웃: 좌(클릭 맵) / 우(경로·통계) ──
    col_map, col_info = st.columns([3, 2])

    with col_map:
        st.subheader(f"🗺️ 실시간 대피 맵  (t = {current_time})")
        pil = build_map_image(
            grid, fire_time, path, visited, start, exits, current_time, CELL_PX
        )
        coords = streamlit_image_coordinates(pil, key="map_click")
        st.markdown(legend_html(), unsafe_allow_html=True)
        st.caption("지도의 통로(흰색)·강의실(R) 칸을 클릭해 현재 위치(S)를 옮기세요.")

        # 클릭 → 셀 매핑 (반환된 표시 크기 기준으로 비율 환산)
        if coords is not None:
            cc = int(coords["x"] / coords["width"] * cols)
            cr = int(coords["y"] / coords["height"] * rows)
            cr = min(max(cr, 0), rows - 1)
            cc = min(max(cc, 0), cols - 1)
            clicked = (cr, cc)
            if clicked != start:
                if grid_base[cr][cc] in PASSABLE_START:
                    st.session_state["start"] = clicked
                    st.rerun()
                else:
                    st.warning(f"({cr + 1}, {cc + 1})은(는) 이동할 수 없는 칸입니다. "
                               "통로/강의실을 클릭하세요.")

    with col_info:
        if not fire_present:
            st.info("👈 지도를 클릭해 위치를 정하고 **화재 발생** 버튼을 누르세요.")
            return

        st.subheader("🧭 탈출 경로")
        if path:
            fire_at_exit = fire_time[best_exit[0]][best_exit[1]]
            safe = dist < fire_at_exit
            st.success("탈출 가능 ✅" if safe else "탈출 경로 존재 (위험) ⚠️")
            m1, m2, m3 = st.columns(3)
            m1.metric("이동 거리", f"{dist} 칸")
            m2.metric("도착 출구", f"{best_exit}")
            m3.metric("출구 화재 도달",
                      "안전" if fire_at_exit == INF else f"t={int(fire_at_exit)}")
            st.caption(f"A* 탐색 노드: {len(visited) if visited else 0}개  ·  "
                       f"화재 발생 지점: {fire_positions}")
        else:
            start_on_fire = fire_time[start[0]][start[1]] <= current_time
            if start_on_fire:
                st.error("탈출 불가 ❌ — 현재 위치가 화재에 휩싸였습니다.")
            elif possible:
                st.error("탈출 불가 ❌ — 출구로 가는 경로가 화재로 차단되었습니다.")
            else:
                st.error("도달 가능한 출구가 없습니다 ❌ — 고립된 구역이거나 "
                         "모든 출구가 화재로 차단되었습니다.")
            st.caption(f"화재 발생 지점: {fire_positions}")

        st.divider()
        st.subheader("📊 대피 통계 (랜덤 10명 시뮬레이션)")
        target_time = st.slider("목표 탈출 시간", 0, 50, value=20, key="target_t")
        evacuees, sorted_times = simulate_evacuees(
            grid_base, fire_time, exits, current_time, n=10
        )
        total = len(evacuees)
        success = len(sorted_times)
        under = binary_search_time(sorted_times, target_time)
        avg = sum(sorted_times) / success if success else 0.0

        s1, s2, s3 = st.columns(3)
        s1.metric("탈출 성공", f"{success}/{total}")
        s2.metric("평균 탈출시간", f"{avg:.1f}" if success else "—")
        s3.metric(f"t≤{target_time} 인원", f"{under}명")
        st.caption(f"탈출시간 정렬(퀵정렬): {sorted_times}")


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
