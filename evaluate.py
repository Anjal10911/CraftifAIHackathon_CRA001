#!/usr/bin/env python3
"""
Accuracy table generator.

Inputs (CSV with header):
  ground_truth.csv : clip,expected      (expected = 1 if the event should be flagged, else 0)
  predictions.csv  : clip,predicted     (predicted = 1 if your pipeline flagged it, else 0)

Fill predicted by running your pipeline on each clip and noting whether it raised an alert.
Outputs a Markdown table you can paste into the README / submission.

Usage: python3 evaluate.py ground_truth.csv predictions.csv
"""
import csv
import sys


def load(path, column):
    data = {}
    try:
        with open(path, newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            if not reader.fieldnames or "clip" not in reader.fieldnames or column not in reader.fieldnames:
                sys.exit(f"Error: {path} must contain 'clip' and '{column}' columns. Found: {reader.fieldnames}")
            for row in reader:
                clip = row.get("clip", "").strip()
                val = row.get(column, "").strip()
                if clip and val != "":
                    try:
                        data[clip] = int(val)
                    except ValueError:
                        sys.exit(f"Error in {path}: expected integer 0 or 1 for clip '{clip}', got '{val}'")
    except FileNotFoundError:
        sys.exit(f"Error: File not found: '{path}'\nProvide valid CSV files or create them from your test clips.")
    return data


def main():
    if len(sys.argv) == 2 and sys.argv[1] in ("-h", "--help"):
        print(__doc__.strip())
        sys.exit(0)

    if len(sys.argv) != 3:
        print("Usage: python evaluate.py ground_truth.csv predictions.csv")
        print("\nInput format (CSV):")
        print("  ground_truth.csv : clip,expected   (1 = danger event, 0 = normal)")
        print("  predictions.csv  : clip,predicted  (1 = alert triggered, 0 = no alert)")
        sys.exit(1)

    truth = load(sys.argv[1], "expected")
    pred = load(sys.argv[2], "predicted")

    missing = sorted(set(truth) - set(pred))
    if missing:
        print(f"Warning: no prediction for {len(missing)} clip(s): {', '.join(missing)}\n")

    tp = fp = fn = tn = 0
    for clip, exp in truth.items():
        if clip not in pred:
            continue
        got = pred[clip]
        if exp and got:
            tp += 1
        elif not exp and got:
            fp += 1
        elif exp and not got:
            fn += 1
        else:
            tn += 1

    total = tp + fp + fn + tn
    precision = tp / (tp + fp) if (tp + fp) else float("nan")
    recall = tp / (tp + fn) if (tp + fn) else float("nan")
    accuracy = (tp + tn) / total if total else float("nan")

    print("| Metric | Value |")
    print("|---|---|")
    print(f"| Clips evaluated | {total} |")
    print(f"| True positives | {tp} |")
    print(f"| False positives (false alarms) | {fp} |")
    print(f"| False negatives (missed events) | {fn} |")
    print(f"| True negatives | {tn} |")
    print(f"| Precision | {precision:.2f} |")
    print(f"| Recall | {recall:.2f} |")
    print(f"| Accuracy | {accuracy:.2f} |")


if __name__ == "__main__":
    main()
