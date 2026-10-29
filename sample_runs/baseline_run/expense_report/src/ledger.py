import sys
import csv
from decimal import Decimal, ROUND_HALF_UP
from collections import defaultdict

def format_money(amount):
    """Formats a Decimal to a string with 2 decimal places, rounded half-up."""
    return f"{amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):.2f}"

def parse_input():
    """Reads expense records from stdin."""
    records = []
    try:
        reader = csv.reader(sys.stdin)
        for line_no, row in enumerate(reader, 1):
            if not row:  # skip blank lines
                continue
            
            if len(row) != 3:
                print(f"Error: Malformed record at line {line_no}", file=sys.stderr)
                sys.exit(2)
            
            date, category, amount_str = row
            try:
                amount = Decimal(amount_str)
            except:
                print(f"Error: Invalid amount at line {line_no}", file=sys.stderr)
                sys.exit(2)
            
            records.append({'category': category.strip(), 'amount': amount})
    except Exception as e:
        print(f"Error parsing input: {e}", file=sys.stderr)
        sys.exit(2)
    return records

def process_categories(records):
    """Sums amounts per category."""
    totals = defaultdict(Decimal)
    for r in records:
        totals[r['category']] += r['amount']
    
    # Sort: amount descending, then category ascending
    # We use -amount for descending, and name for ascending
    sorted_items = sorted(totals.items(), key=lambda x: (-x[1], x[0]))
    return sorted_items

def main():
    if len(sys.argv) < 2:
        print("Usage: ledger.py <command> [args]", file=sys.stderr)
        sys.exit(2)

    command = sys.argv[1]
    records = parse_input()

    if command == "total":
        total = sum((r['amount'] for r in records), Decimal('0'))
        print(format_money(total))
    
    elif command == "count":
        print(len(records))
    
    elif command == "average":
        if not records:
            print("0.00")
        else:
            total = sum((r['amount'] for r in records), Decimal('0'))
            avg = total / len(records)
            print(format_money(avg))
    
    elif command == "categories":
        for cat, total in process_categories(records):
            print(f"{cat}: {format_money(total)}")
            
    elif command == "top":
        if len(sys.argv) < 3:
            print("Usage: ledger.py top <N>", file=sys.stderr)
            sys.exit(2)
        try:
            n = int(sys.argv[2])
        except ValueError:
            print("Error: N must be an integer", file=sys.stderr)
            sys.exit(2)
            
        for cat, total in process_categories(records)[:n]:
            print(f"{cat}: {format_money(total)}")
            
    elif command == "category":
        if len(sys.argv) < 3:
            print("Usage: ledger.py category <NAME>", file=sys.stderr)
            sys.exit(2)
        
        target_cat = sys.argv[2]
        found = False
        total = Decimal('0')
        for r in records:
            if r['category'] == target_cat:
                total += r['amount']
                found = True
        
        if not found:
            # The prompt says: "If there is no such category, print an error to stderr and exit 1."
            print(f"Error: Category '{target_cat}' not found", file=sys.stderr)
            sys.exit(1)
        else:
            print(format_money(total))
            
    else:
        print(f"Error: Unknown command '{command}'", file=sys.stderr)
        sys.exit(2)

if __name__ == "__main__":
    main()
