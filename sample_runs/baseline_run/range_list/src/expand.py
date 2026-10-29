import sys

def expand_range(item):
    if '-' in item:
        try:
            start, end = map(int, item.split('-'))
            # Generate range from start to end (inclusive)
            return list(range(start, end + 1))
        except ValueError:
            return []
    else:
        try:
            return [int(item)]
        except ValueError:
            return []

def main():
    # Read one line from stdin, strip whitespace
    input_data = sys.stdin.read().strip()
    
    if not input_data:
        return

    # Split by comma
    items = input_data.split(',')
    
    result = []
    for item in items:
        # Strip potential whitespace around items
        item = item.strip()
        if not item:
            continue
            
        result.extend(expand_range(item))
    
    # Print space-separated
    print(*(result))

if __name__ == "__main__":
    main()
