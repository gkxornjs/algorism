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
            "escape_time": None,
            "success": False,
            "path": []
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


def check_escape_result(path, fire_time):
    if not path:
        return False, None

    for time, pos in enumerate(path):
        r, c = pos

        if fire_time[r][c] != -1 and fire_time[r][c] <= time:
            return False, time

    return True, len(path) - 1


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


def update_evacuee_result(evacuees, evacuee_id, path, fire_time):
    success, escape_time = check_escape_result(path, fire_time)

    evacuees[evacuee_id]["path"] = path
    evacuees[evacuee_id]["success"] = success
    evacuees[evacuee_id]["escape_time"] = escape_time

    return evacuees


def print_evacuation_statistics(evacuees, target_time=5):
    escape_times = []

    for evacuee_id in evacuees:
        data = evacuees[evacuee_id]

        if data["success"]:
            escape_times.append(data["escape_time"])

    sorted_times = quick_sort_escape_times(escape_times)
    count_under_target = binary_search_time(sorted_times, target_time)

    total = len(evacuees)
    success_count = len(escape_times)
    fail_count = total - success_count

    print("\n=== 대피 통계 ===")
    print(f"전체 대피자 수: {total}")
    print(f"탈출 성공: {success_count}")
    print(f"탈출 실패: {fail_count}")
    print(f"탈출 시간 정렬 결과: {sorted_times}")
    print(f"t={target_time} 이하 탈출 인원: {count_under_target}")

    if success_count > 0:
        avg_time = sum(escape_times) / success_count
        print(f"평균 탈출 시간: {avg_time:.2f}")
    else:
        print("평균 탈출 시간: 계산 불가")