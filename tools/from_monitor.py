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


def read_text(path):
    """The file's text. Notepad can save as UTF-16 ("Unicode") or with a byte-order mark; both are handled."""
    with open(path, "rb") as f:
        data = f.read()
    if data.startswith((b"\xff\xfe", b"\xfe\xff")) or (len(data) > 0 and data.count(b"\x00") > len(data) // 4):
        return data.decode("utf-16", errors="replace")
    return data.decode("utf-8-sig", errors="replace")


def explain(text):
    """Why no capture was found, in words: what the file contains and what to do about it."""
    lines = [clean(raw) for raw in text.splitlines() if raw.strip()]
    rows = [line for line in lines if ROW.match(line)]
    notes = [f"the file has {len(lines)} non-empty line(s)."]
    if not lines:
        notes.append("It is empty. Copy the output of the Serial Monitor (click in it, Ctrl+A, Ctrl+C) AFTER the line '# done' has appeared, and paste it into the file.")
    elif any("unknown command" in line for line in lines):
        notes.append("The sketch answered 'unknown command'. Check that the Serial Monitor line ending is 'Newline' and that the command is typed exactly (S500 or R2000, no spaces).")
    elif rows and not any(HEADER.match(line) for line in lines):
        notes.append(f"It has {len(rows)} rows of numbers but no header line (t,u,pv or t,sp,u,pv): the top of the capture was cut off. The Serial Monitor keeps only its most recent lines, "
                     "so run the capture again and copy it at once.")
    elif not any(line.startswith("t,") for line in lines):
        notes.append("There is no capture in it, only: " + " | ".join(lines[:3])[:200] + ". Send the command (S500 or R2000), wait for '# done', then copy.")
    else:
        notes.append("There is a header but no rows after it: copy again after the line '# done' has appeared.")
    return " ".join(notes)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("raw", help="the text copied from the Serial Monitor")
    ap.add_argument("csv", help="the clean file to write")
    ap.add_argument("--block", type=int, default=-1, help="which capture to take (0 is the first, -1 the last, the default)")
    a = ap.parse_args(argv)
    try:
        text = read_text(a.raw)
    except OSError as e:
        print(f"cannot read {a.raw}: {e.strerror}", file=sys.stderr)
        return 1
    found = blocks(text)
    if not found:
        print("from_monitor: no capture found (there should be a line starting t,u,pv or t,sp,u,pv followed by rows of numbers).\n  " + explain(text), file=sys.stderr)
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
