import sys
import argparse
from decimal import Decimal, ROUND_HALF_UP

def normalize_decimal(d):
    """Convert decimal to string, removing trailing zeros."""
    return f"{d:f}".rstrip('0').rstrip('.') if '.' in f"{d:f}" else f"{d:f}"

def merge_intervals(intervals):
    """
    Merge overlapping or touching intervals.
    Intervals are (start, end) tuples of Decimals.
    """
    if not intervals:
        return []
    
    # Sort by start time
    intervals.sort()
    
    merged = []
    curr_start, curr_end = intervals[0]
    
    for next_start, next_end in intervals[1:]:
        # If the next interval starts before or exactly at the end of the current one
        if next_start <= curr_end:
            # Merge
            curr_end = max(curr_end, next_end)
        else:
            # Push current and move to next
            merged.append((curr_start, curr_end))
            curr_start, curr_end = next_start, next_end
            
    merged.append((curr_start, curr_end))
    return merged

def parse_intervals():
    intervals = []
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            parts = line.split()
            if len(parts) != 2:
                raise ValueError
            start, end = Decimal(parts[0]), Decimal(parts[1])
            if start > end:
                raise ValueError
            intervals.append((start, end))
        except:
            sys.stderr.write("Input error: Invalid interval format or constraints\n")
            sys.exit(2)
    return intervals

def main():
    parser = argparse.ArgumentParser(description="Interval set operations")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Merge command
    subparsers.add_parser('merge')
    
    # Count command
    subparsers.add_parser('count')
    
    # Length command
    subparsers.add_parser('length')
    
    # Covers command
    covers_parser = subparsers.add_parser('covers')
    covers_parser.add_argument('X', type=Decimal)
    
    # Parse initial command
    # We allow unknown args or handle validation manually because standard argparse 
    # structure is slightly tricky with the specific CLI format required.
    # Actually, sys.argv[1] is the command.
    
    if len(sys.argv) < 2:
        sys.stderr.write("Usage error: Missing command\n")
        sys.exit(2)

    try:
        args = parser.parse_args()
    except SystemExit:
        sys.stderr.write("Usage error: Invalid command\n")
        sys.exit(2)

    intervals = parse_intervals()
    merged = merge_intervals(intervals)

    if args.command == 'merge':
        for start, end in merged:
            print(f"{normalize_decimal(start)} {normalize_decimal(end)}")
            
    elif args.command == 'count':
        print(len(merged))
        
    elif args.command == 'length':
        total = sum((end - start for start, end in merged), Decimal(0))
        # Round half-up to 2 decimals: '0.01' quantize
        rounded = total.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        print(f"{rounded:.2f}")
        
    elif args.command == 'covers':
        X = args.X
        found = False
        for start, end in merged:
            if start <= X <= end:
                found = True
                break
        print("yes" if found else "no")

if __name__ == "__main__":
    main()
