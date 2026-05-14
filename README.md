<p align="center">
  <img src="https://img.shields.io/badge/MCP-Protocol-black?style=flat-square&logo=anthropic" alt="MCP">
  <img src="https://img.shields.io/badge/Python-3.11+-blue?style=flat-square&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="License">
  <img src="https://img.shields.io/badge/tools-21-orange?style=flat-square" alt="Tools">
  <img src="https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey?style=flat-square" alt="Platform">
</p>

<h1 align="center">FrameRonin MCP</h1>

<p align="center">
  <strong>21 MCP tools. One server. Complete pixel art game asset pipeline for AI.</strong><br>
  AI generates → AI processes → Game-ready assets. All through a single MCP connection.
</p>

<p align="center">
  English | <a href="#中文">中文</a>
</p>

---

## Overview

FrameRonin MCP wraps the [FrameRonin](https://github.com/systemchester/FrameRonin) pixel art toolset into an MCP (Model Context Protocol) server. AI assistants can directly generate sprites via multiple backends, remove backgrounds, compose sprite sheets, convert GIFs, pixelate images, and extract video frames — all through tool calls.

> **Original project**: [systemchester/FrameRonin](https://github.com/systemchester/FrameRonin) — a full-stack web application with UI for pixel art processing. This MCP server extracts the core algorithms and adds AI-powered generation, making them callable by Claude, Gemini CLI, Copilot, and other MCP-compatible AI tools.

### What Can AI Do With This?

```
"Generate a pixel art fire mage sprite sheet and prepare it for RPG Maker"
  → generate_rpgmaker("fire mage, red robes", rows=4, cols=4, width=48, height=48)
  → 16 frame PNGs, transparent background, no watermark, ready to import

"Remove the green screen from this actor photo"
  → image_chroma_key("actor_green_screen.png", key_color="green", tolerance=40)

"Convert this video of a walk cycle into a sprite sheet"
  → video_to_spritesheet("walk_cycle.mp4", fps=12, columns=4)

"Turn this high-res artwork back into pixel art"
  → image_pixelate("artwork.png", num_colors=16, scale_result=4)
```

### Screenshots

### What You Get

Gemini generates a sprite sheet (4×4 grid). FrameRonin processes it into usable game assets:

<p align="center">
  <img src="docs/assets/pipeline-demo.png" alt="Pipeline" width="100%">
</p>

**Each row is an animation direction, each column is a frame of that animation:**

<p align="center">
  <img src="docs/assets/01_warrior_anim.gif" width="144">  
  <img src="docs/assets/02_sword_anim.gif" width="144">  
  <img src="docs/assets/03_slime_anim.gif" width="144">
  <br><sub>Warrior walk · Sword glow · Slime bounce — 4-frame loops extracted from sprite sheet</sub>
</p>

| Step | Tool | Input → Output |
|---|---|---|
| 1. Generate | `generate_gemini` | Prompt → 2048×2048 sprite sheet |
| 2. Clean | `image_remove_gemini_watermark` | Remove AI watermark |
| 3. Matte | `image_remove_background` | White bg → transparent |
| 4. Resize | `image_resize` | 2048² → 192×192 (4×48px grid) |
| 5. Split | `spritesheet_split` | Sheet → 16 individual frame PNGs |

**Final output**: 16 PNGs (48×48 each with transparent background) — directly importable into RPG Maker MV, Godot, Unity, or any 2D game engine.

---

## Install

```bash
pip install frame-ronin-mcp
```

> Requires Python 3.11+, FFmpeg (for video tools), Chrome (for Gemini web generation).

## Configure

Add to your MCP client config (e.g. `.claude/mcp.json` for Claude Code):

```json
{
  "mcpServers": {
    "frame-ronin": {
      "command": "frame-ronin-mcp"
    }
  }
}
```

No environment variables needed for free Gemini generation or any post-processing tools.

## Tools (21)

### Generation — 5 tools

Four independent backends + one unified pipeline. Each backend is a self-contained module — add new ones by dropping a `.py` file.

| Tool | Backend | Auth | Best for |
|---|---|---|---|
| `generate_gemini` | [Gemini](https://gemini.google.com) free web app | Google login (once) | Free, no setup |
| `generate_dalle` | [OpenAI DALL-E 3](https://platform.openai.com) | `OPENAI_API_KEY` | Natural language, diverse styles |
| `generate_stability` | [Stability AI](https://platform.stability.ai) | `STABILITY_API_KEY` | Pixel art control, fine-tuning |
| `generate_gemini_api` | [Gemini API](https://aistudio.google.com) | `GOOGLE_API_KEY` + billing | Fastest, programmatic |
| `generate_rpgmaker` | Any backend → full pipeline | per backend | One-call: gen → clean → matte → split |

> **`generate_rpgmaker` pipeline**: generate → remove Gemini watermark → AI background removal (rembg/U2Net) → resize to RPG Maker grid → split into individual frame PNGs. All in one call.

### Processing — 16 tools

| Category | Tool | Description |
|---|---|---|
| **Video** | `video_to_spritesheet` | Extract frames → rembg matting → sprite sheet + index JSON |
| | `video_get_info` | Probe video: duration, resolution, fps, frame count |
| | `video_remove_watermark` | Remove Seedance/Jiemeng watermark (crop bottom 180px) |
| **Matting** | `image_remove_background` | AI matting via rembg/U2Net |
| | `image_chroma_key` | Green/blue screen removal + spill suppression + edge erosion |
| | `image_double_background_matte` | Black+white differential alpha extraction |
| **Image** | `image_remove_gemini_watermark` | Reverse alpha blending with embedded 48/96px mask |
| | `image_resize` | Scale (lanczos/nearest/bilinear/bicubic) |
| | `image_crop` | Crop to rectangle |
| | `image_merge_grid` | Merge images into grid atlas |
| **GIF/Sprite** | `gif_extract_frames` | Extract frames from animated GIF |
| | `frames_to_gif` | Combine frames into GIF |
| | `spritesheet_split` | Split spritesheet by uniform grid |
| | `spritesheet_compose` | Compose frames into spritesheet + index |
| **Pixel Art** | `image_pixelate` | Proper pixel art: OpenCV mesh detection → downsample |
| | `image_pixelate_simple` | Simple uniform-grid pixelation (fast) |

---

## Project Structure

```
FrameRonin-MCP/
├── frame_ronin_mcp/
│   ├── server.py               # MCP server (21 tools)
│   ├── tools/
│   │   ├── generate/           # Multi-backend image generation
│   │   │   ├── gemini_web.py   #   Gemini free web app (Playwright)
│   │   │   ├── gemini_api.py   #   Gemini API (google-genai)
│   │   │   ├── dalle.py        #   OpenAI DALL-E 3
│   │   │   └── stability.py    #   Stability AI
│   │   ├── video.py            # FFmpeg + rembg pipeline
│   │   ├── matting.py          # AI/chroma/double-bg matting
│   │   ├── image.py            # Resize, crop, watermark removal
│   │   ├── gif_sprite.py       # GIF extraction, sprite sheet ops
│   │   └── pixelate.py         # Proper pixel art conversion
│   └── lib/                    # Core algorithms (pure Python)
│       ├── watermark.py        # Gemini watermark removal
│       ├── chroma_key.py       # Chroma key matting
│       ├── double_bg.py        # Double background matting
│       ├── mesh.py             # OpenCV grid detection
│       └── pixelate_core.py    # Proper pixel art algorithm
├── pyproject.toml
└── README.md
```

---

## Related

- [FrameRonin](https://github.com/systemchester/FrameRonin) — original web application with full UI
- [proper-pixel-art](https://github.com/KennethJAllen/proper-pixel-art) — pixel art downsampling algorithm
- [GeminiWatermarkTool](https://github.com/allenk/GeminiWatermarkTool) — watermark removal technique

## License

MIT © [FrameRonin](https://github.com/systemchester/FrameRonin)

---

<h1 id="中文" align="center">FrameRonin MCP</h1>

<p align="center">
  <strong>21个MCP工具。一个Server。完整的像素游戏素材AI管线。</strong><br>
  AI生成 → AI处理 → 游戏可用素材。全都通过一个MCP连接完成。
</p>

## 概述

FrameRonin MCP 将 [FrameRonin](https://github.com/systemchester/FrameRonin) 像素画工具集封装为MCP (Model Context Protocol) Server。AI助手可以直接通过工具调用：多后端生成精灵图、去背景、合成精灵表、转换GIF、像素化图片、提取视频帧。

> **原项目**: [systemchester/FrameRonin](https://github.com/systemchester/FrameRonin) — 带UI的全栈像素处理Web应用。本MCP Server提取了核心算法并加入了AI生成能力，让Claude、Gemini CLI、Copilot等MCP兼容的AI工具可以直接调用。

### AI能做什么？

```
"帮我生成一个像素风火法角色，做成RPG Maker格式"
  → generate_rpgmaker("火焰法师，红色法袍", rows=4, cols=4, width=48, height=48)
  → 16帧PNG，透明背景，无水印，可直接导入引擎

"把这张绿幕照片去背景"
  → image_chroma_key("actor_green_screen.png", key_color="green", tolerance=40)

"把这个走路视频转成精灵表"
  → video_to_spritesheet("walk_cycle.mp4", fps=12, columns=4)

"这张高清图转回像素风"
  → image_pixelate("artwork.png", num_colors=16, scale_result=4)
```

### 效果展示

### 产出什么

Gemini生成4×4精灵表，FrameRonin加工成可用的游戏素材：

<p align="center">
  <img src="docs/assets/pipeline-demo.png" alt="流程" width="100%">
</p>

**每行是一个动画方向，每列是该方向的一帧：**

<p align="center">
  <img src="docs/assets/01_warrior_anim.gif" width="144">  
  <img src="docs/assets/02_sword_anim.gif" width="144">  
  <img src="docs/assets/03_slime_anim.gif" width="144">
  <br><sub>战士行走 · 剑发光 · 史莱姆弹跳 — 从精灵表拆出的4帧循环动画</sub>
</p>

| 步骤 | 工具 | 效果 |
|---|---|---|
| 1. 生成 | `generate_gemini` | 提示词 → 大尺寸精灵表 |
| 2. 清洁 | `image_remove_gemini_watermark` | 去除AI水印 |
| 3. 抠图 | `image_remove_background` | 白底 → 透明背景 |
| 4. 缩放 | `image_resize` | 缩放到目标网格尺寸 |
| 5. 拆帧 | `spritesheet_split` | 精灵表 → 16个独立帧PNG |

**最终产出**: 16张48×48透明背景PNG — 可直接导入RPG Maker MV、Godot、Unity等引擎使用。

## 安装

```bash
pip install frame-ronin-mcp
```

> 需要 Python 3.11+、FFmpeg（视频工具）、Chrome（Gemini网页生成）。

## 配置

在MCP客户端配置中添加（如Claude Code的 `.claude/mcp.json`）：

```json
{
  "mcpServers": {
    "frame-ronin": {
      "command": "frame-ronin-mcp"
    }
  }
}
```

免费Gemini网页生成和所有后处理工具不需要任何环境变量。

## 工具列表（21个）

### 生成 — 5个

四种独立后端 + 一个统一管线。每个后端是独立模块，添加新后端只需新增一个 `.py` 文件。

| 工具 | 后端 | 认证 | 最适合 |
|---|---|---|---|
| `generate_gemini` | [Gemini](https://gemini.google.com) 免费网页版 | Google登录（一次） | 免费，零配置 |
| `generate_dalle` | [OpenAI DALL-E 3](https://platform.openai.com) | `OPENAI_API_KEY` | 自然语言理解，风格多样 |
| `generate_stability` | [Stability AI](https://platform.stability.ai) | `STABILITY_API_KEY` | 像素风精细控制 |
| `generate_gemini_api` | [Gemini API](https://aistudio.google.com) | `GOOGLE_API_KEY` + 付费 | 最快，纯程序化 |
| `generate_rpgmaker` | **任意后端** → 完整管线 | 按后端 | 一键：生成→去水印→抠图→缩放→拆帧 |

> **`generate_rpgmaker` 管线**: 生成 → 去Gemini水印 → AI去背景(rembg/U2Net) → 缩放到RPG Maker网格 → 拆分为独立帧PNG。一次调用搞定全部。

### 处理 — 16个

| 类别 | 工具 | 说明 |
|---|---|---|
| **视频** | `video_to_spritesheet` | 拆帧 → rembg抠图 → 精灵表 + 索引JSON |
| | `video_get_info` | 探针：时长、分辨率、帧率、总帧数 |
| | `video_remove_watermark` | 去Seedance/即梦水印（裁切底部180px） |
| **抠图** | `image_remove_background` | AI抠图 (rembg/U2Net) |
| | `image_chroma_key` | 绿幕/蓝幕抠图 + 溢色抑制 + 边缘侵蚀 |
| | `image_double_background_matte` | 黑底+白底差分提取Alpha |
| **图片** | `image_remove_gemini_watermark` | 反向Alpha混合去水印（内嵌48/96px mask） |
| | `image_resize` | 缩放 (lanczos/nearest/bilinear/bicubic) |
| | `image_crop` | 矩形裁切 |
| | `image_merge_grid` | 多图拼成网格图集 |
| **GIF/精灵表** | `gif_extract_frames` | GIF拆帧为PNG序列 |
| | `frames_to_gif` | PNG序列合成GIF动图 |
| | `spritesheet_split` | 精灵表网格拆分为单帧 |
| | `spritesheet_compose` | 单帧合成精灵表 + 索引元数据 |
| **像素化** | `image_pixelate` | 像素化: OpenCV网格检测 → 逐格下采样 |
| | `image_pixelate_simple` | 简单均匀网格像素化（快速） |

## 项目结构

```
FrameRonin-MCP/
├── frame_ronin_mcp/
│   ├── server.py               # MCP服务入口 (21个工具)
│   ├── tools/
│   │   ├── generate/           # 多后端图片生成
│   │   │   ├── gemini_web.py   #   Gemini免费网页版 (Playwright)
│   │   │   ├── gemini_api.py   #   Gemini API (google-genai)
│   │   │   ├── dalle.py        #   OpenAI DALL-E 3
│   │   │   └── stability.py    #   Stability AI
│   │   ├── video.py            # FFmpeg + rembg 管线
│   │   ├── matting.py          # AI/色度键/双背景抠图
│   │   ├── image.py            # 缩放、裁切、去水印
│   │   ├── gif_sprite.py       # GIF拆帧、精灵表操作
│   │   └── pixelate.py         # 像素化
│   └── lib/                    # 核心算法（纯Python）
│       ├── watermark.py        # Gemini水印去除
│       ├── chroma_key.py       # 色度键抠图
│       ├── double_bg.py        # 双背景抠图
│       ├── mesh.py             # OpenCV网格检测
│       └── pixelate_core.py    # proper-pixel-art 算法
├── pyproject.toml
└── README.md
```

## 相关链接

- [FrameRonin](https://github.com/systemchester/FrameRonin) — 原项目（带完整UI的Web应用）
- [proper-pixel-art](https://github.com/KennethJAllen/proper-pixel-art) — 像素画下采样算法
- [GeminiWatermarkTool](https://github.com/allenk/GeminiWatermarkTool) — 水印去除技术

## 许可证

MIT © [FrameRonin](https://github.com/systemchester/FrameRonin)
