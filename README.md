# 桌面宠物 (Desktop Pet)

一款用 Python 写的简易桌面宠物：一只会自己走动、睡觉、说话的小动物，
透明窗口浮在桌面上，可以拖动它、跟它互动。

形象全部由 Pillow 程序化绘制，**不需要任何图片素材**，克隆下来就能跑。

## 效果

- 三种宠物：橘猫 / 柴犬 / 兔子
- 透明背景、无边框、始终置顶
- 自主行为：随机走动 → 站立发呆 → 睡觉（冒 Zzz）
- 交互：单击说话、拖动移动、右键菜单

## 运行

需要 Python 3.8+（Windows 上验证通过，Linux/macOS 也能跑）。

```bash
pip install -r requirements.txt
python main.py
```

### 命令行参数

```bash
python main.py --pet shiba --size 160   # 指定宠物与大小
python main.py --no-topmost             # 不总在最前
```

可选宠物：`cat`（橘猫）、`shiba`（柴犬）、`rabbit`（兔子）

## 操作

| 操作 | 效果 |
| --- | --- |
| 单击桌宠 | 说一句话 |
| 按住拖动 | 把它拖到任意位置 |
| 右键 | 弹出菜单：打招呼 / 换一只 / 变大变小 / 总在最前 / 退出 |

## 配置

右键菜单里的选择会保存到 `~/.desktop_pet/config.json`，下次启动自动生效。

## 项目结构

```
main.py                 启动入口
desktoppet/
  app.py                主程序：窗口、交互、行为状态机、图像合成
  sprites.py            精灵绘制：宠物形象、动作帧、动画缓存
  phrases.py            对话台词
  config.py             配置读写
smoke_test.py           冒烟测试：跑几帧动画并导出合成图
live_test.py            功能测试：真实事件循环里验证移动/状态机/交互
transparency_test.py    透明性测试：截图验证键色确实被抠掉
```

测试脚本都会把配置写到临时目录，不会影响 `~/.desktop_pet/config.json`。

## 实现说明

- **透明窗口**：Windows 上用 Tk 的 `-transparentcolor` 抠掉键色（品红 `#FF00FF`）。
  Tk 的 PhotoImage 不支持 alpha 通道，所以所有图形都合成到键色背景上，
  精灵边缘做二值化处理以避免残留色边。
- **动画**：精灵以 4 倍超采样绘制后缩放，保证边缘平滑；渲染结果按
  `(宠物, 动作, 帧, 尺寸)` 缓存，只有切换宠物或改大小时才重新渲染。
- **行为状态机**：`idle → walk → sleep` 循环，每个状态有随机持续时间，
  走到屏幕边缘会掉头。

## 已知限制

- 抠色键方案下窗口边缘是硬边，缩放到很小尺寸时可能有轻微锯齿。
- 透明色只支持 Windows；其它平台会显示为品红背景（可后续改用
  `wm_attributes('-alpha')` 或 `pywin32` 的分层窗口方案）。
