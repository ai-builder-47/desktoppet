"""冒烟测试：创建窗口、跑几帧动画、导出合成图并截图。

用法: python smoke_test.py
"""

from __future__ import annotations

import sys
import tkinter as tk

from desktoppet import config
from desktoppet.app import DesktopPet


def main() -> int:
    cfg = config.load()
    cfg.update({"pet": "cat", "size": 120})

    root = tk.Tk()
    root.withdraw()
    pet = DesktopPet(root, cfg)
    root.deiconify()
    root.update()

    # 固定位置，避免走动导致截图对不上
    root.geometry("220x172+300+300")
    root.update()

    for _ in range(20):
        root.update()
        pet._tick()
    pet._say("你好呀，我是桌宠！", 60)
    for _ in range(5):
        pet._tick()
        root.update()

    # 导出合成图（键色为透明区）
    pet._composite().save("composite.png")

    try:
        from PIL import ImageGrab

        x, y = root.winfo_x(), root.winfo_y()
        w, h = root.winfo_width(), root.winfo_height()
        img = ImageGrab.grab(bbox=(x - 10, y - 10, x + w + 10, y + h + 10))
        img.save("smoke.png")
        print(f"screenshot: {img.size} at ({x},{y}) {w}x{h}")
    except Exception as exc:  # pragma: no cover
        print(f"screenshot failed: {exc}")

    print("state:", pet.state, "| geom:", root.geometry())
    root.destroy()
    return 0


if __name__ == "__main__":
    sys.exit(main())
