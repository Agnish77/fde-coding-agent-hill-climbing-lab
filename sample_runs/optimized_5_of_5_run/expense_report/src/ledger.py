import sys
from decimal import Decimal, ROUND_HALF_UP
from collections import defaultdict

def format_money(amount):
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def parse_input():
    records = []
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        parts = line.split(',')
        if len(parts) != 3:
            sys.stderr.write("Error: Malformed line\n")
            sys.exit(2)
        date, category, amount_str = parts
        try:
            amount = Decimal(amount_str)
        except:
            sys.stderr.write("Error: Invalid amount\n")
            sys.exit(2)
        records.append({'category': category, 'amount': amount})
    return records

def main():
    if len(sys.argv) < 2:
        sys.stderr.write("Error: Missing command\n")
        sys.exit(2)

    records = parse_input()
    command = sys.argv[1]

    if command == 'total':
        total = sum((r['amount'] for r in records), Decimal("0"))
        print(f"{format_money(total):.2f}")

    elif command == 'count':
        print(len(records))

    elif command == 'average':
        if not records:
            print("0.00")
        else:
            total = sum((r['amount'] for r in records), Decimal("0"))
            avg = total / len(records)
            print(f"{format_money(avg):.2f}")

    elif command == 'categories':
        cat_totals = defaultdict(Decimal)
        for r in records:
            cat_totals[r['category']] += r['amount']
        
        # Sort: amount descending, name ascending
        sorted_cats = sorted(cat_totals.items(), key=lambda x: (-x[1], x[0]))
        for cat, total in sorted_cats:
            print(f"{cat}: {format_money(total):.2f}")

    elif command == 'top':
        if len(sys.argv) < 3:
            sys.stderr.write("Error: Missing N for top\n")
            sys.exit(2)
        try:
            n = int(sys.argv[2])
        except ValueError:
            sys.stderr.write("Error: Invalid N\n")
            sys.exit(2)
            
        cat_totals = defaultdict(Decimal)
        for r in records:
            cat_totals[r['category']] += r['amount']
        
        sorted_cats = sorted(cat_totals.items(), key=lambda x: (-x[1], x[0]))
        for cat, total in sorted_cats[:n]:
            print(f"{cat}: {format_money(total):.2f}")

    elif command == 'category':
        if len(sys.argv) < 3:
            sys.stderr.write("Error: Missing category name\n")
            sys.exit(2)
        target_cat = sys.argv[2]
        
        cat_totals = defaultdict(Decimal)
        for r in records:
            cat_totals[r['category']] += r['amount']
            
        if target_cat not in cat_totals:
            sys.stderr.write(f"Error: Category {target_cat} not found\n")
            sys.exit(1)
        
        print(f"{format_money(cat_totals[target_cat]):.2f}")

    else:
        sys.stderr.write("Error: Unknown command\n")
        sys.exit(2)

if __name__ == '__main__':
    main()
