"""透明性验证。

1. 桌宠显示时，窗口所在区域应能看到桌宠像素（橙色）；
2. 隐藏窗口后同一区域应恢复为桌面背景（说明键色被真正抠掉）；
3. 整个区域不应出现品红色残留。

用法: python transparency_test.py
"""

from __future__ import annotations

import os
import sys
import tempfile
import tkinter as tk

from PIL import ImageGrab

from desktoppet import config

config.CONFIG_DIR = tempfile.mkdtemp(prefix="desktoppet_test_")
config.CONFIG_FILE = os.path.join(config.CONFIG_DIR, "config.json")

from desktoppet.app import DesktopPet  # noqa: E402

BBOX = (300, 200, 720, 520)


def count_pet_pixels(img) -> int:
    """统计橙色调像素（桌宠主体颜色）。"""
    n = 0
    for y in range(0, img.height, 2):
        for x in range(0, img.width, 2):
            r, g, b = img.getpixel((x, y))[:3]
            if r > 200 and 120 < g < 200 and b < 140:
                n += 1
    return n


def count_magenta(img) -> int:
    n = 0
    for y in range(0, img.height, 2):
        for x in range(0, img.width, 2):
            if img.getpixel((x, y))[:3] == (255, 0, 255):
                n += 1
    return n


def main() -> int:
    cfg = config.load()
    cfg.update({"pet": "cat", "size": 120})

    root = tk.Tk()
    root.withdraw()
    pet = DesktopPet(root, cfg)
    root.deiconify()
    root.geometry("220x172+400+300")
    root.update()
    for _ in range(3):
        pet._tick()
        root.update()

    shown = ImageGrab.grab(bbox=BBOX)
    pet_px = count_pet_pixels(shown)
    magenta_px = count_magenta(shown)

    # 隐藏窗口后重新抓取同一区域作为桌面背景参照
    root.withdraw()
    root.update()
    hidden = ImageGrab.grab(bbox=BBOX)
    hidden_pet_px = count_pet_pixels(hidden)

    # 桌宠所在位置在隐藏前后应有明显差异
    same = 0
    total = 0
    for y in range(0, shown.height, 3):
        for x in range(0, shown.width, 3):
            total += 1
            a = shown.getpixel((x, y))[:3]
            b = hidden.getpixel((x, y))[:3]
            if abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[2] - b[2]) > 30:
                same += 1

    print(f"pet pixels while shown : {pet_px}")
    print(f"pet pixels while hidden: {hidden_pet_px}")
    print(f"magenta pixels         : {magenta_px}")
    print(f"pixels differing from desktop background: {same}/{total}")

    shown.save("transparency.png")

    ok = pet_px > 50 and magenta_px == 0 and same > 50
    print("RESULT:", "PASS" if ok else "FAIL")
    pet.quit()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
