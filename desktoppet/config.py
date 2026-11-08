"""配置持久化：把用户选择存到用户目录下的 JSON 文件。"""

from __future__ import annotations

import json
import os
from typing import Any, Dict

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".desktop_pet")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

DEFAULTS: Dict[str, Any] = {
    "pet": "cat",
    "size": 120,
    "always_on_top": True,
    "speed": 2,
}


def load() -> Dict[str, Any]:
    data = dict(DEFAULTS)
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as fh:
            data.update(json.load(fh))
    except (OSError, ValueError):
        pass
    return data


def save(data: Dict[str, Any]) -> None:
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
    except OSError:
        pass
