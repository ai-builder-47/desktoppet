"""桌宠启动入口。

用法:
    python main.py            # 正常启动
    python main.py --pet shiba --size 160
"""

from __future__ import annotations

import argparse
import sys

from desktoppet import config
from desktoppet.app import run


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="简易桌面宠物")
    parser.add_argument(
        "--pet",
        choices=["cat", "shiba", "rabbit"],
        help="选择初始宠物形象",
    )
    parser.add_argument("--size", type=int, help="初始像素大小 (60-240)")
    parser.add_argument(
        "--no-topmost", action="store_true", help="窗口不总在最前"
    )
    args = parser.parse_args(argv)

    cfg = config.load()
    if args.pet:
        cfg["pet"] = args.pet
    if args.size:
        cfg["size"] = max(60, min(240, args.size))
    if args.no_topmost:
        cfg["always_on_top"] = False

    try:
        run(cfg)
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
