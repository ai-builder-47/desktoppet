"""桌宠会说的话。"""

from __future__ import annotations

import random
from typing import List

GREETINGS: List[str] = [
    "你好呀~",
    "嗨！",
    "在忙什么呢？",
    "今天也要加油哦！",
    "要不要休息一下？",
]

IDLE_LINES: List[str] = [
    "我在偷偷看着你工作~",
    "记得喝水哦",
    "摸鱼被我发现了！",
    "这个 bug 看起来有点难搞",
    "要不要摸摸我？",
    "工作辛苦啦",
    "肩膀会酸的，起来动一动吧",
]

DRAG_LINES: List[str] = [
    "诶——别搬我！",
    "哇哦，飞起来了",
    "放我下来嘛~",
    "晕…头晕…",
]

SLEEP_LINES: List[str] = [
    "Zzz…",
    "呼…呼…",
]


def pick(lines: List[str]) -> str:
    return random.choice(lines)
