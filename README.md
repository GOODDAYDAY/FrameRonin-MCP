# FrameRonin MCP Server

One MCP server. 21 tools. Complete pixel art game asset pipeline — generation, processing, export.

AI can: generate sprites via Gemini/DALL-E/Stability → remove watermarks/backgrounds → resize → split frames → compose sprite sheets → convert GIFs → pixelate images → extract video frames.

## Quick Start

```bash
pip install frame-ronin-mcp
frame-ronin-mcp
```

`.claude/mcp.json`:

```json
{
  "mcpServers": {
    "frame-ronin": {
      "command": "frame-ronin-mcp"
    }
  }
}
```

## Tools (21)

### Generation (5 tools — multi-backend, high cohesion low coupling)

Each backend lives in its own file under `tools/generate/`. Add a new backend by dropping in a module with a `generate(prompt, output_path, **kw) -> Path` function.

| Tool | Backend | Auth | Notes |
|---|---|---|---|
| `generate_gemini` | Gemini free web app | Google login (once) | Playwright, no key, free |
| `generate_dalle` | OpenAI DALL-E 3 | `OPENAI_API_KEY` | Best language understanding |
| `generate_stability` | Stability AI | `STABILITY_API_KEY` | Best for pixel art control |
| `generate_gemini_api` | Gemini API | `GOOGLE_API_KEY` + billing | Fastest, programmatic |
| `generate_rpgmaker` | **Any backend** → full pipeline | per backend | Generate → watermark → matte → resize → split frames, one call |

### Video (3 tools)

| Tool | Description |
|---|---|
| `video_to_spritesheet` | Extract frames → rembg matting → sprite sheet + index JSON |
| `video_get_info` | Probe video metadata (duration, resolution, fps, frame count) |
| `video_remove_watermark` | Remove Seedance/Jiemeng watermark (crop bottom 180px) |

### Matting (3 tools)

| Tool | Description |
|---|---|
| `image_remove_background` | AI matting via rembg/U2Net (first run downloads 176MB model) |
| `image_chroma_key` | Green/blue screen removal with spill suppression + edge erosion |
| `image_double_background_matte` | Black+white background differential alpha extraction (no green screen needed) |

### Image Processing (4 tools)

| Tool | Description |
|---|---|
| `image_remove_gemini_watermark` | Remove Gemini watermark via reverse alpha blending (embedded 48/96px mask) |
| `image_resize` | Scale image: specify w/h/scale, methods: lanczos/nearest/bilinear/bicubic |
| `image_crop` | Crop to rectangle (x, y, width, height) |
| `image_merge_grid` | Merge multiple images into grid atlas (sprite sheet from loose frames) |

### GIF & Sprite Sheet (4 tools)

| Tool | Description |
|---|---|
| `gif_extract_frames` | Extract all frames from animated GIF as PNG sequence |
| `frames_to_gif` | Combine PNG sequence into animated GIF (configurable duration/loop) |
| `spritesheet_split` | Split sprite sheet by uniform grid (specify rows, cols, margins, spacing) |
| `spritesheet_compose` | Compose individual frames into sprite sheet with index metadata |

### Pixel Art (2 tools)

| Tool | Description |
|---|---|
| `image_pixelate` | Proper pixel art conversion: OpenCV Canny+HoughLinesP mesh detection → per-cell most-common-color downsampling |
| `image_pixelate_simple` | Simple uniform-grid pixelation: pixel_size blocks → median color (fast, no OpenCV needed) |

## Typical Pipeline

```
generate_gemini("pixel warrior with shield, white background")
  → image_remove_gemini_watermark
  → image_remove_background
  → image_resize(width=192, height=192, method="nearest")
  → spritesheet_split(rows=4, columns=4)
  → 16 frame PNGs ready for RPG Maker
```

Or one call:

```
generate_rpgmaker(
  prompt="fire mage, red robes, casting stance",
  backend="gemini",     # or dalle, stability, gemini_api
  rows=4, columns=4,
  width=48, height=48
)
  → 01_raw.png, 02_clean.png, 03_nobg.png, 04_resized.png, 16 frame PNGs
```

## Project Structure

```
FrameRonin-MCP/
├── pyproject.toml
├── frame_ronin_mcp/
│   ├── server.py                # MCP entry point (21 tools)
│   ├── tools/
│   │   ├── generate/            # Multi-backend image generation
│   │   │   ├── gemini_web.py    #   Gemini free web app (Playwright)
│   │   │   ├── gemini_api.py    #   Gemini API (google-genai)
│   │   │   ├── dalle.py         #   OpenAI DALL-E 3
│   │   │   └── stability.py     #   Stability AI
│   │   ├── video.py             # Video processing
│   │   ├── matting.py           # Background removal
│   │   ├── image.py             # Image operations
│   │   ├── gif_sprite.py        # GIF & sprite sheet
│   │   └── pixelate.py          # Pixel art conversion
│   └── lib/                     # Core algorithms (all local, no network)
│       ├── watermark.py         # Gemini watermark removal
│       ├── chroma_key.py        # Chroma key matting
│       ├── double_bg.py         # Double background matting
│       ├── mesh.py              # OpenCV grid detection
│       └── pixelate_core.py     # Proper pixel art algorithm
```

## Requirements

- Python 3.11+
- FFmpeg (in PATH, for video tools)
- Chrome (for Gemini web generation — auto-installed by Playwright)

## Environment Variables

| Variable | Used by | Needed? |
|---|---|---|
| `GOOGLE_API_KEY` | `generate_gemini_api` | Only for Gemini API (paid) |
| `OPENAI_API_KEY` | `generate_dalle` | Only for DALL-E |
| `STABILITY_API_KEY` | `generate_stability` | Only for Stability AI |
| `FRAMERONIN_BROWSER_DIR` | `generate_gemini` | Override browser data dir |

No env vars needed for free Gemini web generation or any post-processing tools.

## License

MIT
