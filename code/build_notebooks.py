"""Convert notebooks_src/*.py (cells separated by '# %%' / '# %% [markdown]') into .ipynb files."""
import json
import re
import sys
from pathlib import Path

SRC = Path(__file__).parent / "notebooks_src"
DST = Path(__file__).parent / "notebooks"
DST.mkdir(exist_ok=True)

SETUP = '''# --- common setup: find the t15 code package (attached Kaggle Dataset or local) ---
import sys, os, glob
cands = (glob.glob("/kaggle/input/**/code/t15", recursive=True)
         + glob.glob("/kaggle/working/code/t15") + ["../code/t15", "./t15", "../t15"])
CODE = os.path.dirname(next(c for c in cands if os.path.isdir(c)))
sys.path.insert(0, CODE)
print("t15 package from", CODE)
!pip install -q pyfixest osmnx psutil 2>/dev/null | tail -1
from t15 import config as C, data as D, pipeline as PL
print(C.paths())
!find -L /kaggle/input -maxdepth 4 -type d 2>/dev/null | head -30'''


def cells_from(text: str):
    parts = re.split(r"^# %%(.*)$", text, flags=re.M)
    cells = []
    head = parts[0].strip()
    if head:
        cells.append(("code", head))
    for i in range(1, len(parts), 2):
        tag, body = parts[i], parts[i + 1].strip("\n")
        if "[markdown]" in tag:
            body = "\n".join(l[2:] if l.startswith("# ") else l.lstrip("#") for l in body.splitlines())
            cells.append(("markdown", body.strip()))
        elif body.strip() == "SETUP":
            cells.append(("code", SETUP))
        elif body.strip():
            cells.append(("code", body))
    return cells


def to_nb(cells):
    return {
        "cells": [{"cell_type": t, "metadata": {}, "source": src.splitlines(keepends=True),
                   **({"outputs": [], "execution_count": None} if t == "code" else {})} for t, src in cells],
        "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                     "language_info": {"name": "python"}},
        "nbformat": 4, "nbformat_minor": 5,
    }


for f in sorted(SRC.glob("*.py")):
    nb = to_nb(cells_from(f.read_text(encoding="utf-8")))
    out = DST / (f.stem + ".ipynb")
    out.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
    print("built", out.name, len(nb["cells"]), "cells")
