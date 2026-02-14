# ses_weg/services/banlist.py
from __future__ import annotations
import json
from pathlib import Path
from typing import Iterable

# 你也可以换成 data/ban_list.json，看你项目习惯
BANLIST_PATH = Path("data") / "ban_list.json"

DEFAULT_BANLIST = [
    "何意味", "？", "?", "1", "嗯", "对",
    "你妈死了", "你妈", "我去", "6", "吊",
    "是", "还真是", "艾斯比", "傻逼",
]

def _ensure_file():
    BANLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not BANLIST_PATH.exists():
        BANLIST_PATH.write_text(json.dumps(DEFAULT_BANLIST, ensure_ascii=False, indent=2), encoding="utf-8")

def load_set() -> set[str]:
    _ensure_file()
    try:
        data = json.loads(BANLIST_PATH.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return set(str(x) for x in data)
    except Exception:
        pass
    # 文件坏了就回退默认
    return set(DEFAULT_BANLIST)

def save_set(s: set[str]) -> None:
    BANLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    BANLIST_PATH.write_text(
        json.dumps(sorted(s), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

def add(items: Iterable[str]) -> tuple[int, int]:
    """返回 (added_count, total_count)"""
    s = load_set()
    before = len(s)
    for x in items:
        t = (x or "").strip()
        if t:
            s.add(t)
    save_set(s)
    return (len(s) - before, len(s))

def remove(items: Iterable[str]) -> tuple[int, int]:
    s = load_set()
    before = len(s)
    for x in items:
        t = (x or "").strip()
        if t and t in s:
            s.remove(t)
    save_set(s)
    return (before - len(s), len(s))
