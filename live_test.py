"""功能测试：在真实事件循环里跑一小段时间，验证移动、状态机、交互。

用法: python live_test.py
配置写入临时文件，不会动用户的 ~/.desktop_pet/config.json。
"""

from __future__ import annotations

import os
import sys
import tempfile
import tkinter as tk

from desktoppet import config

# 把配置重定向到临时目录，避免污染用户配置
config.CONFIG_DIR = tempfile.mkdtemp(prefix="desktoppet_test_")
config.CONFIG_FILE = os.path.join(config.CONFIG_DIR, "config.json")

from desktoppet.app import DesktopPet  # noqa: E402  (需在重定向之后再导入)


def main() -> int:
    cfg = config.load()
    cfg.update({"pet": "cat", "size": 120})

    root = tk.Tk()
    root.withdraw()
    pet = DesktopPet(root, cfg)
    root.deiconify()
    root.geometry("220x172+400+300")
    root.update()

    x0 = root.winfo_x()
    samples = []

    def sample() -> None:
        samples.append((pet.state, pet.frame_index))
        if len(samples) < 120:
            root.after(30, sample)
            return

        x1 = root.winfo_x()
        print("moved px:", x1 - x0)
        print("states seen:", sorted({s for s, _ in samples}))
        print("frames advanced:", samples[-1][1] - samples[0][1])

        # 单击交互
        evt = type("E", (), {"x_root": 410, "y_root": 360})()
        pet._on_press(evt)
        pet._on_release(evt)
        root.update()
        print("bubble:", repr(pet.bubble_text))

        # 菜单命令
        pet._next_pet()
        print("pet now:", pet.pet)
        pet._resize(30)
        root.update()
        print("size now:", pet.size, "| geom:", root.geometry())
        print("canvas size:", pet.canvas.winfo_width(), "x", pet.canvas.winfo_height())
        pet.quit()

    sample()
    root.mainloop()
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
