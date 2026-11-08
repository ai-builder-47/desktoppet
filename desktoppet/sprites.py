"""桌宠精灵绘制。

所有形象都由 Pillow 程序化绘制，不依赖任何外部图片资源。
每个动作由若干帧组成，渲染结果缓存在内存中，避免逐帧重绘的开销。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from PIL import Image, ImageDraw, ImageFont

# 逻辑画布尺寸（最终按用户设定的像素大小缩放）
BASE = 120
SS = 4  # 超采样倍数，用于抗锯齿


@dataclass(frozen=True)
class PetSpec:
    """一种宠物形象的外观参数。"""

    name: str
    body: str
    body_dark: str
    belly: str
    ear: str
    inner_ear: str
    nose: str
    tail_len: float
    ear_kind: str = "pointy"  # pointy | round
    tuft: bool = False


PETS: Dict[str, PetSpec] = {
    "cat": PetSpec(
        name="橘猫",
        body="#F0A860",
        body_dark="#D98B45",
        belly="#FBE3C4",
        ear="#E79B52",
        inner_ear="#F7C3AC",
        nose="#E8708A",
        tail_len=1.0,
        ear_kind="pointy",
        tuft=True,
    ),
    "shiba": PetSpec(
        name="柴犬",
        body="#E8A45C",
        body_dark="#C97F35",
        belly="#FBF3E4",
        ear="#D9903F",
        inner_ear="#EFC0A0",
        nose="#3A3230",
        tail_len=0.85,
        ear_kind="pointy",
    ),
    "rabbit": PetSpec(
        name="兔子",
        body="#F2F0F5",
        body_dark="#D8D4DE",
        belly="#FFFFFF",
        ear="#E9E6EE",
        inner_ear="#F6C6D0",
        nose="#E8768F",
        tail_len=0.5,
        ear_kind="round",
    ),
}

ACTIONS = ("idle", "walk", "sleep", "drag")
_FRAME_COUNT = {"idle": 4, "walk": 4, "sleep": 2, "drag": 1}


class _Canvas:
    """按比例放大坐标的绘图辅助类。"""

    def __init__(self, draw: ImageDraw.ImageDraw, scale: int = SS) -> None:
        self._d = draw
        self._s = scale

    def _b(self, coords):
        return tuple(c * self._s for c in coords)

    @staticmethod
    def _scale_width(kw: dict) -> dict:
        """线宽也要按超采样倍数放大，否则线条会显得过细。"""
        if "width" in kw and kw["width"]:
            kw = dict(kw)
            kw["width"] = kw["width"] * SS
        return kw

    def ellipse(self, coords, **kw):
        self._d.ellipse(self._b(coords), **kw)

    def rect(self, coords, radius, **kw):
        self._d.rounded_rectangle(self._b(coords), radius=radius * self._s, **kw)

    def polygon(self, points, **kw):
        self._d.polygon([(x * self._s, y * self._s) for x, y in points], **kw)

    def line(self, points, **kw):
        self._d.line(
            [(x * self._s, y * self._s) for x, y in points], **self._scale_width(kw)
        )

    def arc(self, coords, **kw):
        self._d.arc(self._b(coords), **self._scale_width(kw))


def _draw_tail(c: _Canvas, spec: PetSpec, wag: int):
    """尾巴：从身体右下方伸出，随 wag 参数上下摆动。"""
    x0, y0 = 84, 78
    dx = 20 * spec.tail_len
    dy = -26 * spec.tail_len + wag
    c.line(
        [(x0, y0), (x0 + dx * 0.55, y0 + dy * 0.45), (x0 + dx, y0 + dy)],
        fill=spec.body,
        width=9,
        joint="curve",
    )
    c.ellipse(
        (x0 + dx - 5, y0 + dy - 5, x0 + dx + 5, y0 + dy + 5),
        fill=spec.body,
    )


def _draw_legs(c: _Canvas, spec: PetSpec, action: str, frame: int):
    """四条小短腿，walk 帧做交替抬腿，drag 时垂下。"""
    positions = ((42, 0), (52, 1), (66, 1), (76, 0))
    for idx, (lx, _phase) in enumerate(positions):
        up = 0
        if action == "walk" and (idx + frame) % 2 == 0:
            up = 4
        elif action == "drag":
            up = 5
        c.rect(
            (lx, 94 - up, lx + 9, 108 - up),
            4,
            fill=spec.body_dark if idx % 2 else spec.body,
        )


def _draw_head(c: _Canvas, spec: PetSpec, bob: int):
    c.ellipse((34, 18 + bob, 86, 70 + bob), fill=spec.body)
    c.ellipse((44, 44 + bob, 76, 68 + bob), fill=spec.belly)

    if spec.ear_kind == "round":
        # 兔子：长耳朵
        c.ellipse((38, 2, 56, 34), fill=spec.ear)
        c.ellipse((43, 7, 51, 29), fill=spec.inner_ear)
        c.ellipse((64, 2, 82, 34), fill=spec.ear)
        c.ellipse((69, 7, 77, 29), fill=spec.inner_ear)
    else:
        c.polygon([(34, 30), (46, 8), (58, 28)], fill=spec.ear)
        c.polygon([(39, 29), (46, 16), (53, 28)], fill=spec.inner_ear)
        c.polygon([(62, 28), (74, 8), (86, 30)], fill=spec.ear)
        c.polygon([(67, 28), (74, 16), (81, 29)], fill=spec.inner_ear)

    if spec.tuft:
        c.polygon([(60, 20 + bob), (56, 6 + bob), (63, 16 + bob)], fill=spec.body_dark)


def _draw_face(c: _Canvas, spec: PetSpec, bob: int, eye_mode: str, blink: bool):
    eyes = ((50, 44), (70, 44))
    for ex, ey in eyes:
        if eye_mode == "closed" or blink:
            c.arc((ex - 6, ey - 2, ex + 6, ey + 6), start=200, end=340, fill="#3A3230", width=3)
        elif eye_mode == "happy":
            c.arc((ex - 6, ey - 8, ex + 6, ey + 6), start=180, end=360, fill="#3A3230", width=3)
        else:
            h = 9 if eye_mode == "wide" else 7
            c.ellipse((ex - 5, ey - h, ex + 5, ey + h), fill="#3A3230")
            c.ellipse((ex - 1, ey - h + 1, ex + 3, ey - h + 5), fill="#FFFFFF")

    nose_y = 52 + bob
    c.ellipse((56, nose_y, 64, nose_y + 5), fill=spec.nose)
    c.arc((48, nose_y + 2, 60, nose_y + 12), start=0, end=140, fill="#3A3230", width=2)
    c.arc((60, nose_y + 2, 72, nose_y + 12), start=40, end=180, fill="#3A3230", width=2)

    # 腮红
    c.ellipse((38, 50 + bob, 47, 55 + bob), fill=(240, 150, 150, 110))
    c.ellipse((73, 50 + bob, 82, 55 + bob), fill=(240, 150, 150, 110))


def _render_frame(spec: PetSpec, action: str, frame: int) -> Image.Image:
    """渲染一帧到 RGBA 图（BASE x BASE）。"""
    img = Image.new("RGBA", (BASE * SS, BASE * SS), (0, 0, 0, 0))
    c = _Canvas(ImageDraw.Draw(img))

    bob = 0
    blink = False
    eye_mode = "open"

    if action == "idle":
        bob = (0, -1, 0, 1)[frame % 4]
        blink = frame == 3
    elif action == "walk":
        bob = (0, -2, 0, -2)[frame % 4]
    elif action == "sleep":
        bob = 3
        eye_mode = "closed"
    elif action == "drag":
        bob = -2
        eye_mode = "wide"

    # 尾巴（在身体之后绘制）
    _draw_tail(c, spec, 3 if action == "walk" and frame % 2 else -3 if action == "walk" else 0)

    # 腿
    _draw_legs(c, spec, action, frame)

    # 身体
    c.ellipse((32, 54 + bob, 88, 102 + bob), fill=spec.body)
    c.ellipse((46, 68 + bob, 76, 100 + bob), fill=spec.belly)

    # 头
    _draw_head(c, spec, bob)

    # 脸
    _draw_face(c, spec, bob, eye_mode, blink)

    return img.resize((BASE, BASE), Image.LANCZOS)


def _render_zzz(size: int) -> Image.Image:
    """睡眠时头顶的 z 字。"""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    font = None
    for name in ("arial.ttf", "DejaVuSans.ttf", "segoeui.ttf"):
        try:
            font = ImageFont.truetype(name, int(size * 0.18))
            break
        except Exception:
            continue
    if font is None:
        font = ImageFont.load_default()
    d.text((size * 0.70, size * 0.00), "z", font=font, fill=(120, 120, 160, 220))
    d.text((size * 0.82, size * 0.10), "z", font=font, fill=(100, 100, 150, 170))
    return img


class SpriteBank:
    """按 (宠物, 动作, 帧, 尺寸) 缓存渲染结果。"""

    def __init__(self) -> None:
        self._cache: Dict[Tuple[str, str, int, int], Image.Image] = {}

    def frame(self, pet: str, action: str, index: int, size: int) -> Image.Image:
        key = (pet, action, index % _FRAME_COUNT.get(action, 1), size)
        img = self._cache.get(key)
        if img is None:
            base = _render_frame(PETS[pet], action, key[2])
            img = base.resize((size, size), Image.LANCZOS)
            self._cache[key] = img
        return img

    def zzz(self, size: int) -> Image.Image:
        key = ("__zzz__", "", 0, size)
        img = self._cache.get(key)
        if img is None:
            img = _render_zzz(size)
            self._cache[key] = img
        return img

    @staticmethod
    def actions() -> List[str]:
        return list(ACTIONS)
