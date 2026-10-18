#!/usr/bin/env python3
"""Turns text copied from the Arduino Serial Monitor (or saved by a terminal program such as PuTTY) into a clean CSV that the other tools can read.

The sketch prints a capture as a header line (t,u,pv for an open-loop step, t,sp,u,pv for a closed-loop run), numbered rows, and a line "# done",
mixed with comment lines that start with #. The Serial Monitor can also put a time stamp in front of every line ("12:00:01.234 -> ...").
This keeps only the header and the rows of one capture.

    python3 tools/from_monitor.py raw.txt step.csv             # the last capture in the file
    python3 tools/from_monitor.py raw.txt step.csv --block 0   # the first one
"""
import argparse
import re
import sys

HEADER = re.compile(r"^t,[a-z,]+$")
ROW = re.compile(r"^-?\d+(\.\d+)?(,-?\d+(\.\d+)?)+$")


def clean(line):
    line = line.strip()
    if "->" in line:                                  # a Serial Monitor time stamp: "12:00:01.234 -> text"
        line = line.split("->", 1)[1].strip()
    return line


def blocks(text):
    """Every capture in the text, each as a list of lines: the header first, then the rows."""
    found, current = [], None
    for raw in text.splitlines():
        line = clean(raw)
        if HEADER.match(line):
            current = [line]
            found.append(current)
        elif current is not None and ROW.match(line) and line.count(",") == current[0].count(","):
            current.append(line)
        else:
            current = None
    return [b for b in found if len(b) > 1]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("raw", help="the text copied from the Serial Monitor")
    ap.add_argument("csv", help="the clean file to write")
    ap.add_argument("--block", type=int, default=-1, help="which capture to take (0 is the first, -1 the last, the default)")
    a = ap.parse_args(argv)
    with open(a.raw, encoding="utf-8", errors="replace") as f:
        found = blocks(f.read())
    if not found:
        print("no capture found: there should be a line starting t,u,pv or t,sp,u,pv followed by rows of numbers", file=sys.stderr)
        return 1
    try:
        chosen = found[a.block]
    except IndexError:
        print(f"the file has {len(found)} capture(s); --block {a.block} does not exist", file=sys.stderr)
        return 1
    with open(a.csv, "w", newline="") as f:
        f.write("\n".join(chosen) + "\n")
    print(f"wrote {a.csv}: {chosen[0]} with {len(chosen) - 1} rows (capture {found.index(chosen)} of {len(found)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
