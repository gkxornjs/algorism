# evacuation.py

# 자료구조: 해시맵(dict)
# 자료구조: 스택(stack)
# 알고리즘: 퀵 정렬
# 알고리즘: 이진 탐색


def create_evacuee_dict(evacuee_list):
    evacuees = {}

    for evacuee_id, name, start_pos in evacuee_list:
        evacuees[evacuee_id] = {
            "name": name,
            "start_pos": start_pos,
            "current_pos": start_pos,
            "escape_time": None,
            "success": False,
            "failed": False,
            "path": [],
            "message": "대기 중"
        }

    return evacuees


def save_path_with_stack(path):
    stack = []

    for pos in path:
        stack.append(pos)

    reversed_path = []

    while stack:
        reversed_path.append(stack.pop())

    return reversed_path


def get_evacuee_position_at_time(path, t):
    if not path:
        return None

    if t < 0:
        return path[0]

    if t >= len(path):
        return path[-1]

    return path[t]


def check_fire_collision(path, fire_time, t):
    if not path:
        return False

    current_pos = get_evacuee_position_at_time(path, t)
    r, c = current_pos

    if fire_time[r][c] != -1 and fire_time[r][c] <= t:
        return True

    return False


def check_escape_result(path, fire_time):
    if not path:
        return False, None

    for time, pos in enumerate(path):
        r, c = pos

        if fire_time[r][c] != -1 and fire_time[r][c] <= time:
            return False, time

    return True, len(path) - 1


def update_evacuee_position_by_time(evacuees, evacuee_id, t, fire_time):
    path = evacuees[evacuee_id]["path"]

    if not path:
        evacuees[evacuee_id]["message"] = "탈출 경로 없음"
        evacuees[evacuee_id]["failed"] = True
        return evacuees

    current_pos = get_evacuee_position_at_time(path, t)
    evacuees[evacuee_id]["current_pos"] = current_pos

    if check_fire_collision(path, fire_time, t):
        evacuees[evacuee_id]["success"] = False
        evacuees[evacuee_id]["failed"] = True
        evacuees[evacuee_id]["escape_time"] = None
        evacuees[evacuee_id]["message"] = f"t={t} 화재와 충돌"
        return evacuees

    if t >= len(path) - 1:
        evacuees[evacuee_id]["success"] = True
        evacuees[evacuee_id]["failed"] = False
        evacuees[evacuee_id]["escape_time"] = len(path) - 1
        evacuees[evacuee_id]["message"] = "탈출 성공"
    else:
        evacuees[evacuee_id]["success"] = False
        evacuees[evacuee_id]["failed"] = False
        evacuees[evacuee_id]["escape_time"] = None
        evacuees[evacuee_id]["message"] = "대피 중"

    return evacuees


def update_all_evacuees_by_time(evacuees, t, fire_time):
    for evacuee_id in evacuees:
        update_evacuee_position_by_time(evacuees, evacuee_id, t, fire_time)

    return evacuees


def update_evacuee_result(evacuees, evacuee_id, path, fire_time):
    success, escape_time = check_escape_result(path, fire_time)

    evacuees[evacuee_id]["path"] = path
    evacuees[evacuee_id]["success"] = success
    evacuees[evacuee_id]["escape_time"] = escape_time
    evacuees[evacuee_id]["current_pos"] = path[0] if path else None

    if success:
        evacuees[evacuee_id]["failed"] = False
        evacuees[evacuee_id]["message"] = "탈출 가능"
    else:
        evacuees[evacuee_id]["failed"] = True
        evacuees[evacuee_id]["message"] = "탈출 실패 위험"

    return evacuees


def quick_sort_escape_times(arr):
    if len(arr) <= 1:
        return arr

    pivot = arr[len(arr) // 2]

    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]

    return quick_sort_escape_times(left) + middle + quick_sort_escape_times(right)


def binary_search_time(sorted_times, target_time):
    left = 0
    right = len(sorted_times) - 1
    answer = -1

    while left <= right:
        mid = (left + right) // 2

        if sorted_times[mid] <= target_time:
            answer = mid
            left = mid + 1
        else:
            right = mid - 1

    return answer + 1


def get_evacuation_statistics(evacuees, target_time=5):
    escape_times = []

    for evacuee_id in evacuees:
        data = evacuees[evacuee_id]

        if data["success"] and data["escape_time"] is not None:
            escape_times.append(data["escape_time"])

    sorted_times = quick_sort_escape_times(escape_times)
    count_under_target = binary_search_time(sorted_times, target_time)

    total = len(evacuees)
    success_count = len(escape_times)
    fail_count = total - success_count

    avg_time = 0
    if success_count > 0:
        avg_time = sum(escape_times) / success_count

    return {
        "total": total,
        "success_count": success_count,
        "fail_count": fail_count,
        "success_rate": success_count / total * 100 if total > 0 else 0,
        "average_escape_time": avg_time,
        "sorted_escape_times": sorted_times,
        "count_under_target": count_under_target
    }


def print_evacuation_statistics(evacuees, target_time=5):
    statistics = get_evacuation_statistics(evacuees, target_time)

    print("\n=== 대피 통계 ===")
    print(f"전체 대피자 수: {statistics['total']}")
    print(f"탈출 성공: {statistics['success_count']}")
    print(f"탈출 실패: {statistics['fail_count']}")
    print(f"탈출 성공률: {statistics['success_rate']:.2f}%")
    print(f"탈출 시간 정렬 결과: {statistics['sorted_escape_times']}")
    print(f"t={target_time} 이하 탈출 인원: {statistics['count_under_target']}")
    print(f"평균 탈출 시간: {statistics['average_escape_time']:.2f}")


def get_simulation_state(evacuees, fire_time, t, target_time=5):
    update_all_evacuees_by_time(evacuees, t, fire_time)
    statistics = get_evacuation_statistics(evacuees, target_time)

    return {
        "time": t,
        "evacuees": evacuees,
        "statistics": statistics
    }