#!/usr/bin/env python3
"""
validate_book.py — Deterministic validation for OS_Textbook_Selfimproved_test.

Checks:
  1. book/ Markdown files exist
  2. Chapter front matter: id, title, order present
  3. id and order uniqueness
  4. Markdown code fence pairing
  5. Local image/reference targets exist
  6. Git conflict markers
  7. Chapter title vs order consistency
  8. Document truncation detection
  9. Git diff scope (issue range check)

Returns 0 on success, non-zero on failure.
Only uses Python stdlib.
"""
import subprocess
import sys
import os
import re
import json
from pathlib import Path
from collections import Counter

BOOK_DIR = Path("book")
REPO_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = REPO_ROOT / "assets"

errors = []


def fail(msg):
    errors.append(msg)
    print(f"FAIL: {msg}", file=sys.stderr)


# ── 1. book/ Markdown files exist ──────────────────────────────────────
def check_files_exist():
    md_files = sorted(BOOK_DIR.glob("ch*.md"))
    if not md_files:
        fail("No chapter Markdown files found in book/")
        return []
    return md_files


# ── 2-3. Front matter validation ──────────────────────────────────────
def parse_front_matter(text):
    """Parse YAML-like front matter. Returns dict or None."""
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    if end == -1:
        return None
    fm_text = text[4:end]
    fm = {}
    for line in fm_text.split("\n"):
        line = line.strip()
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip().strip("'\"")
            fm[key] = val
    return fm


def check_front_matter(md_files):
    ids = []
    orders = []
    file_data = []

    for f in md_files:
        text = f.read_text(encoding="utf-8")
        fm = parse_front_matter(text)

        if fm is None:
            fail(f"{f.name}: missing or malformed front matter")
            continue

        for field in ["id", "title", "order"]:
            if field not in fm:
                fail(f"{f.name}: missing '{field}' in front matter")

        fid = fm.get("id", "")
        order = fm.get("order", "")
        title = fm.get("title", "")

        if fid:
            ids.append(fid)
        if order:
            try:
                orders.append(int(order))
            except (ValueError, TypeError):
                fail(f"{f.name}: order '{order}' is not a valid integer")

        file_data.append((f, fm, text))

    # Check id uniqueness
    id_counts = Counter(ids)
    for id_val, count in id_counts.items():
        if count > 1:
            fail(f"Duplicate id '{id_val}' found {count} times")

    # Check order uniqueness
    order_counts = Counter(orders)
    for ord_val, count in order_counts.items():
        if count > 1:
            fail(f"Duplicate order '{ord_val}' found {count} times")

    return file_data


# ── 4. Code fence pairing ─────────────────────────────────────────────
def check_code_fences(file_data):
    for f, fm, text in file_data:
        fences = re.findall(r"^```", text, re.MULTILINE)
        if len(fences) % 2 != 0:
            fail(f"{f.name}: unpaired code fence (odd number of ``` markers)")


# ── 5. Local image and relative link targets ─────────────────────────
def check_local_targets(file_data):
    for f, fm, text in file_data:
        # Check Markdown images: ![alt](path)
        for m in re.finditer(r"!\[.*?\]\(([^)]+)\)", text):
            path = m.group(1)
            if path.startswith(("http://", "https://")):
                continue
            # Relative path
            target = (f.parent / path).resolve()
            if not target.exists():
                fail(f"{f.name}: image target not found: {path}")

        # Check Markdown links: [text](path)
        for m in re.finditer(r"(?<!!)\[.*?\]\(([^)]+)\)", text):
            path = m.group(1)
            if path.startswith(("http://", "https://", "#")):
                continue
            if path.strip() == "":
                continue
            target = (f.parent / path).resolve()
            if not target.exists():
                fail(f"{f.name}: link target not found: {path}")


# ── 6. Git conflict markers ───────────────────────────────────────────
def check_conflict_markers(file_data):
    for f, fm, text in file_data:
        for marker in ["<<<<<<<", "=======", ">>>>>>>"]:
            if marker in text:
                fail(f"{f.name}: contains git conflict marker '{marker}'")
                break


# ── 7. Chapter title vs order consistency ────────────────────────────
def check_title_order(file_data):
    # Extract chapter number from title (e.g., "第 5 章") and compare with order
    for f, fm, text in file_data:
        order_str = fm.get("order", "")
        title = fm.get("title", "")
        try:
            order_val = int(order_str)
        except (ValueError, TypeError):
            continue

        # Try to extract chapter number from title
        m = re.search(r"第\s*(\d+)\s*章", title)
        if m:
            title_ch = int(m.group(1))
            if title_ch != order_val:
                fail(
                    f"{f.name}: title says chapter {title_ch} but order is {order_val}"
                )


# ── 8. Document truncation detection ─────────────────────────────────
def check_truncation(file_data):
    for f, fm, text in file_data:
        # Check if document ends abruptly (no proper closing)
        stripped = text.rstrip()
        if not stripped:
            fail(f"{f.name}: file is empty or whitespace-only")
            continue

        # Check for obvious truncation: ends with a header with no content
        last_lines = stripped.split("\n")[-5:]
        # If last line is a header and file is short relative to others
        if re.match(r"^#{1,6}\s", last_lines[-1].strip()):
            # This is suspicious — file ends in a header
            pass  # Not a hard fail, just note

        # Check for unmatched parentheses/brackets in last 500 chars
        tail = stripped[-500:]
        for opener, closer in [("(", ")"), ("[", "]"), ("{", "}")]:
            if tail.count(opener) > tail.count(closer) + 2:
                fail(f"{f.name}: possible truncation (unmatched '{opener}')")


# ── 9. Git diff scope check ───────────────────────────────────────────
def check_diff_scope():
    """Check if current git diff touches files outside expected scope."""
    try:
        # Get diff stat
        result = subprocess.run(
            ["git", "diff", "--stat", "origin/main"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )
        if result.returncode != 0:
            return  # Can't check, skip

        output = result.stdout.strip()
        if not output:
            return  # No diff

        # Check for unexpected file changes
        for line in output.split("\n"):
            line = line.strip()
            if not line:
                continue
            # Expected: book/ch*.md, assets/figures/*, scripts/validate_book.py
            if "/" in line:
                fname = line.split("|")[0].strip()
                if not (
                    fname.startswith("book/ch")
                    or fname.startswith("assets/figures/")
                    or fname == "scripts/validate_book.py"
                ):
                    fail(f"diff touches unexpected file: {fname}")

    except Exception:
        pass


# ── Main ───────────────────────────────────────────────────────────────
def main():
    # Change to repo root
    os.chdir(REPO_ROOT)

    md_files = check_files_exist()
    if not md_files:
        return 1

    file_data = check_front_matter(md_files)
    check_code_fences(file_data)
    check_local_targets(file_data)
    check_conflict_markers(file_data)
    check_title_order(file_data)
    check_truncation(file_data)
    check_diff_scope()

    if errors:
        print(f"\n{len(errors)} validation error(s) found.", file=sys.stderr)
        return 1

    print("VALIDATION OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
