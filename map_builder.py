# map_builder.py (임시 버전)

def load_map(filepath):
    """txt 파일에서 맵 로드 후 2D 배열로 반환"""
    grid = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            row = line.strip().split()
            if row:
                grid.append(row)
    return grid

def find_positions(grid):
    """S, F, E 위치 찾기"""
    start = fire = None
    exits = []
    for r in range(len(grid)):
        for c in range(len(grid[r])):
            if grid[r][c] == 'S':
                start = (r, c)
            elif grid[r][c] == 'F':
                fire = (r, c)
            elif grid[r][c] == 'E':
                exits.append((r, c))
    return start, fire, exits