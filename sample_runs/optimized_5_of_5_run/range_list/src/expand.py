import sys

def parse_range(item):
    parts = item.split('-')
    if len(parts) == 2:
        return int(parts[0]), int(parts[1])
    elif len(parts) == 3:
        if parts[0] == '':
            return -int(parts[1]), int(parts[2])
        else:
            return int(parts[0]), -int(parts[2])
    elif len(parts) == 4:
        return -int(parts[1]), -int(parts[3])
    else:
        raise ValueError("Invalid range format")

def expand_ranges():
    try:
        input_data = sys.stdin.read().strip()
        if not input_data:
            return

        items = input_data.split(',')
        result = []

        for item in items:
            item = item.strip()
            if not item:
                continue
            
            if '-' in item:
                try:
                    start, end = parse_range(item)
                    
                    if start <= end:
                        result.extend(range(start, end + 1))
                    else:
                        result.extend(range(start, end - 1, -1))
                except ValueError:
                    pass
            else:
                try:
                    result.append(int(item))
                except ValueError:
                    pass
        
        print(*(result))
    except Exception:
        pass

if __name__ == "__main__":
    expand_ranges()
