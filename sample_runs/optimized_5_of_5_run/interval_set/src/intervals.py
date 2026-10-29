import sys
from decimal import Decimal, ROUND_HALF_UP

def format_decimal(d):
    s = format(d, 'f')
    if '.' in s:
        s = s.rstrip('0').rstrip('.')
    return s

def parse_intervals():
    intervals = []
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) != 2:
            sys.stderr.write("Error: Invalid input format\n")
            sys.exit(2)
        try:
            start = Decimal(parts[0])
            end = Decimal(parts[1])
        except:
            sys.stderr.write("Error: Invalid number format\n")
            sys.exit(2)
        
        if start > end:
            sys.stderr.write("Error: start > end\n")
            sys.exit(2)
        intervals.append((start, end))
    return intervals

def merge_intervals(intervals):
    if not intervals:
        return []
    
    intervals.sort(key=lambda x: x[0])
    
    merged = []
    curr_start, curr_end = intervals[0]
    
    for i in range(1, len(intervals)):
        next_start, next_end = intervals[i]
        if next_start <= curr_end:
            if next_end > curr_end:
                curr_end = next_end
        else:
            merged.append((curr_start, curr_end))
            curr_start, curr_end = next_start, next_end
    merged.append((curr_start, curr_end))
    return merged

def main():
    if len(sys.argv) < 2:
        sys.stderr.write("Usage: python src/intervals.py <command> [args]\n")
        sys.exit(2)
    
    command = sys.argv[1]
    intervals = parse_intervals()
    merged = merge_intervals(intervals)
    
    if command == 'merge':
        for start, end in merged:
            print(f"{format_decimal(start)} {format_decimal(end)}")
            
    elif command == 'count':
        print(len(merged))
        
    elif command == 'length':
        total = sum((end - start for start, end in merged), Decimal("0"))
        rounded = total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        print(f"{rounded:.2f}")
        
    elif command == 'covers':
        if len(sys.argv) < 3:
            sys.stderr.write("Error: Missing argument for covers\n")
            sys.exit(2)
        try:
            x = Decimal(sys.argv[2])
        except:
            sys.stderr.write("Error: Invalid number for covers\n")
            sys.exit(2)
            
        found = False
        for start, end in merged:
            if start <= x <= end:
                found = True
                break
        print("yes" if found else "no")
        
    else:
        sys.stderr.write("Error: Unknown command\n")
        sys.exit(2)

if __name__ == "__main__":
    main()
