#!/usr/bin/env python3
import os
from urllib.parse import quote

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
GITHUB_BASE = "https://raw.githubusercontent.com/PawMarques/Luthia-App/main"
OUTPUT_FILE = os.path.join(REPO_ROOT, "file_list.txt")

EXCLUDED_DIRS = {
    "raw_data",
    "ideas",
    ".git",
    ".next",
    "node_modules",
    ".pytest_cache",
    "__pycache__",
}

EXCLUDED_FILES = {".DS_Store", "file_list.txt"}

lines = []

for dirpath, dirnames, filenames in os.walk(REPO_ROOT):
    # Prune excluded directories in-place so os.walk won't descend into them
    dirnames[:] = [d for d in sorted(dirnames) if d not in EXCLUDED_DIRS]

    for filename in sorted(filenames):
        if filename in EXCLUDED_FILES:
            continue

        full_path = os.path.join(dirpath, filename)
        relative_path = os.path.relpath(full_path, REPO_ROOT)
        encoded_path = quote(relative_path, safe="/")
        lines.append(f"{GITHUB_BASE}/{encoded_path}")

with open(OUTPUT_FILE, "w") as f:
    f.write("\n".join(lines) + "\n")

print(f"Generated {len(lines)} URLs → file_list.txt")