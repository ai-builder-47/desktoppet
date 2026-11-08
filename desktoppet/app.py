"""桌宠主程序。

在 Windows 上使用 Tk 的 -transparentcolor 实现逐像素透明（抠色键），
精灵由 Pillow 绘制并程序化合成成一张图片贴到 Canvas 上。
"""

from __future__ import annotations

import random
import time
import tkinter as tk
from typing import List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont, ImageTk

from . import config, phrases
from .sprites import PETS, SpriteBank

# 抠色键：不会出现在精灵与气泡中的颜色
KEY_COLOR = "#FF00FF"
KEY_RGB = (255, 0, 255)

SS = 4  # 超采样倍数
BUBBLE_H = 52  # 气泡区域高度（逻辑像素）
FRAME_MS = 90  # 每一帧的间隔

_FONT_CANDIDATES = (
    "msyh.ttc",
    "msyhl.ttc",
    "simhei.ttf",
    "simsun.ttc",
    "arial.ttf",
    "DejaVuSans.ttf",
)


def load_font(size: int) -> ImageFont.ImageFont:
    """加载一个能显示中文的字体，失败则退回默认字体。"""
    for name in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()


def wrap_text(text: str, font: ImageFont.ImageFont, max_width: int) -> List[str]:
    """按像素宽度折行（中文逐字折行即可）。"""
    lines: List[str] = []
    current = ""
    for ch in text:
        if ch == "\n":
            lines.append(current)
            current = ""
            continue
        probe = current + ch
        if font.getlength(probe) > max_width and current:
            lines.append(current)
            current = ch
        else:
            current = probe
    if current:
        lines.append(current)
    return lines


class DesktopPet:
    def __init__(self, root: tk.Tk, cfg: dict) -> None:
        self.root = root
        self.cfg = cfg
        self.bank = SpriteBank()

        self.pet: str = cfg.get("pet", "cat")
        self.size: int = int(cfg.get("size", 120))
        self.topmost: bool = bool(cfg.get("always_on_top", True))
        self.speed: int = max(1, int(cfg.get("speed", 2)))

        # 行为状态机
        self.state = "idle"
        self.frame_index = 0
        self.state_until = time.monotonic() + random.uniform(1.5, 4.0)
        self.direction = random.choice((-1, 1))

        # 气泡
        self.bubble_text: str = ""
        self.bubble_until: float = 0.0
        self._bubble_key: Tuple[str, int] = ("", 0)
        self._bubble_cache: Optional[Image.Image] = None

        # 拖拽
        self.dragging = False
        self.drag_offset = (0, 0)
        self.drag_start = (0, 0)

        self.win_w = max(self.size + 24, 220)
        self.win_h = self.size + BUBBLE_H

        self._build_ui()
        self._place_initial()
        self._tick()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        root = self.root
        root.title("桌面宠物")
        root.overrideredirect(True)
        root.configure(bg=KEY_COLOR)
        try:
            root.wm_attributes("-transparentcolor", KEY_COLOR)
        except tk.TclError:
            pass
        root.wm_attributes("-topmost", self.topmost)

        self.canvas = tk.Canvas(
            root,
            width=self.win_w,
            height=self.win_h,
            bg=KEY_COLOR,
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack()

        self.image_id = self.canvas.create_image(
            self.win_w // 2, self.win_h - 1, anchor="s"
        )
        self._photo: Optional[ImageTk.PhotoImage] = None

        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Button-3>", self._on_right_click)

        self.menu = tk.Menu(root, tearoff=0)
        self.menu.add_command(label="打个招呼", command=self._say_hello)
        self.menu.add_command(label="换一只", command=self._next_pet)
        self.menu.add_separator()
        self.menu.add_command(label="变大", command=lambda: self._resize(20))
        self.menu.add_command(label="变小", command=lambda: self._resize(-20))
        self._topmost_var = tk.BooleanVar(value=self.topmost)
        self.menu.add_checkbutton(
            label="总在最前",
            command=self._toggle_topmost,
            variable=self._topmost_var,
        )
        self.menu.add_separator()
        self.menu.add_command(label="退出", command=self.quit)

    def _place_initial(self) -> None:
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = screen_w - self.win_w - 60
        y = screen_h - self.win_h - 60
        self.root.geometry(f"{self.win_w}x{self.win_h}+{max(x, 0)}+{max(y, 0)}")

    # ------------------------------------------------------------- rendering
    def _composite(self) -> Image.Image:
        """把气泡和精灵合成为一张与窗口等大的 RGB 图。

        Tk 的 PhotoImage 不支持 alpha 通道，因此这里统一画到键色背景上，
        由 -transparentcolor 把键色抠掉，实现窗口透明。
        """
        full = Image.new("RGB", (self.win_w, self.win_h), KEY_RGB)

        # 精灵：边缘做二值化，避免抠色键留下色边
        sprite = self.bank.frame(self.pet, self.state, self.frame_index, self.size)
        mask = sprite.getchannel("A").point(lambda a: 255 if a >= 100 else 0)
        full.paste(
            sprite.convert("RGB"),
            ((self.win_w - self.size) // 2, self.win_h - self.size),
            mask,
        )

        # 气泡
        if self.bubble_text and time.monotonic() < self.bubble_until:
            bubble = self._render_bubble(self.bubble_text)
            bmask = bubble.getchannel("A").point(lambda a: 255 if a >= 128 else 0)
            full.paste(
                bubble.convert("RGB"),
                ((self.win_w - bubble.width) // 2, 0),
                bmask,
            )
        elif self.state == "sleep":
            zzz = self.bank.zzz(max(24, self.size // 2))
            zmask = zzz.getchannel("A").point(lambda a: 255 if a >= 128 else 0)
            full.paste(
                zzz.convert("RGB"),
                ((self.win_w - self.size) // 2 + int(self.size * 0.78), self.win_h - self.size),
                zmask,
            )
        return full

    def _render_bubble(self, text: str) -> Image.Image:
        key = (text, self.size)
        if key == self._bubble_key and self._bubble_cache is not None:
            return self._bubble_cache
        self._bubble_key = key

        font = load_font(13 * SS)
        max_text_w = (self.win_w - 24) * SS
        lines = wrap_text(text, font, max_text_w)
        line_h = 18 * SS
        text_w = max(int(font.getlength(line)) for line in lines)
        text_h = line_h * len(lines)

        pad_x, pad_y = 14 * SS, 10 * SS
        w = text_w + pad_x * 2
        h = text_h + pad_y * 2

        # 白底：文字在白底上做抗锯齿，再整体抠出圆角形状
        layer = Image.new("RGB", (w, h), (255, 255, 255))
        d = ImageDraw.Draw(layer)
        d.text((pad_x, pad_y - 2), "\n".join(lines), font=font, fill=(60, 60, 72))
        d.rounded_rectangle(
            (1, 1, w - 2, h - 2), radius=12 * SS, outline=(226, 226, 236), width=SS
        )

        mask = Image.new("L", (w, h), 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            (0, 0, w - 1, h - 1), radius=12 * SS, fill=255
        )
        mask = mask.resize((w // SS, h // SS), Image.LANCZOS)

        bubble = layer.resize((w // SS, h // SS), Image.LANCZOS).convert("RGBA")
        bubble.putalpha(mask)
        self._bubble_cache = bubble
        return bubble

    # ------------------------------------------------------------- behaviour
    def _tick(self) -> None:
        now = time.monotonic()
        self._advance_state(now)

        if self.state == "walk":
            self._move(self.direction * self.speed)

        self.frame_index += 1
        image = self._composite()
        self._photo = ImageTk.PhotoImage(image)
        self.canvas.itemconfig(self.image_id, image=self._photo)

        self.root.after(FRAME_MS, self._tick)

    def _advance_state(self, now: float) -> None:
        if self.dragging:
            self.state = "drag"
            return
        if now < self.state_until:
            return
        # 状态切换
        if self.state == "idle":
            self.state = "walk"
            self.direction = random.choice((-1, 1))
            self.state_until = now + random.uniform(2.0, 6.0)
        elif self.state == "walk":
            self.state = random.choice(("idle", "idle", "sleep"))
            duration = random.uniform(1.5, 3.5) if self.state == "idle" else random.uniform(6.0, 12.0)
            self.state_until = now + duration
        else:  # sleep
            self.state = "idle"
            self.state_until = now + random.uniform(1.5, 3.5)

    def _move(self, dx: int) -> None:
        x = self.root.winfo_x()
        y = self.root.winfo_y()
        screen_w = self.root.winfo_screenwidth()
        new_x = x + dx
        # 撞到屏幕边缘就掉头
        if new_x <= 0:
            new_x = 0
            self.direction = 1
        elif new_x + self.win_w >= screen_w:
            new_x = screen_w - self.win_w
            self.direction = -1
        self.root.geometry(f"+{new_x}+{y}")

    # -------------------------------------------------------------- 交互
    def _on_press(self, event: tk.Event) -> None:
        self.dragging = False
        self.drag_offset = (event.x_root - self.root.winfo_x(), event.y_root - self.root.winfo_y())
        self.drag_start = (event.x_root, event.y_root)

    def _on_drag(self, event: tk.Event) -> None:
        moved = abs(event.x_root - self.drag_start[0]) > 4 or abs(
            event.y_root - self.drag_start[1]
        ) > 4
        if not moved:
            return
        self.dragging = True
        x = event.x_root - self.drag_offset[0]
        y = event.y_root - self.drag_offset[1]
        self.root.geometry(f"+{x}+{y}")
        if self.bubble_text and self.state != "drag":
            self._say(phrases.pick(phrases.DRAG_LINES), 1.5)

    def _on_release(self, event: tk.Event) -> None:
        was_dragging = self.dragging
        self.dragging = False
        if was_dragging:
            # 放开后重新开始一轮行为计时
            self.state_until = time.monotonic() + random.uniform(1.0, 2.5)
        else:
            self._say(phrases.pick(phrases.IDLE_LINES), 3.0)

    def _on_right_click(self, event: tk.Event) -> None:
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()

    # -------------------------------------------------------------- 命令
    def _say(self, text: str, duration: float = 3.0) -> None:
        self.bubble_text = text
        self.bubble_until = time.monotonic() + duration

    def _say_hello(self) -> None:
        self._say(phrases.pick(phrases.GREETINGS), 3.0)

    def _next_pet(self) -> None:
        names = list(PETS)
        idx = (names.index(self.pet) + 1) % len(names)
        self.pet = names[idx]
        self._save()

    def _resize(self, delta: int) -> None:
        self.size = max(60, min(240, self.size + delta))
        new_w = max(self.size + 24, 220)
        new_h = self.size + BUBBLE_H
        # 保持桌宠脚部位置不变，避免改大小时整个形象跳走
        bottom = self.root.winfo_y() + self.win_h
        x = self.root.winfo_x()
        y = bottom - new_h
        screen_h = self.root.winfo_screenheight()
        y = max(0, min(y, screen_h - new_h))
        self.win_w, self.win_h = new_w, new_h
        self.canvas.configure(width=new_w, height=new_h)
        self.root.geometry(f"{new_w}x{new_h}+{x}+{y}")
        self._save()

    def _toggle_topmost(self) -> None:
        self.topmost = self._topmost_var.get()
        self.root.wm_attributes("-topmost", self.topmost)
        self._save()

    def _save(self) -> None:
        self.cfg.update(
            {
                "pet": self.pet,
                "size": self.size,
                "always_on_top": self.topmost,
                "speed": self.speed,
            }
        )
        config.save(self.cfg)

    def quit(self) -> None:
        self._save()
        self.root.destroy()


def run(cfg: Optional[dict] = None) -> None:
    cfg = cfg if cfg is not None else config.load()
    root = tk.Tk()
    root.withdraw()  # 避免闪现默认窗口
    DesktopPet(root, cfg)
    root.deiconify()
    root.mainloop()
