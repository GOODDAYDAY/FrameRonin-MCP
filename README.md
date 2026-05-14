# FrameRonin MCP Server

MCP (Model Context Protocol) server wrapping [FrameRonin](https://github.com/systemchester/FrameRonin)'s pixel art and sprite sheet processing tools — enabling AI assistants to directly perform video frame extraction, background removal, GIF manipulation, sprite sheet composition, and pixel art conversion.

## Tools (14)

### Video
| Tool | Description |
|---|---|
| `video_to_spritesheet` | Extract frames → AI matting → sprite sheet + index JSON |
| `video_get_info` | Probe video metadata (duration, resolution, fps) |
| `video_remove_watermark` | Remove Seedance/Jiemeng "AI生成" watermark |

### Image Matting
| Tool | Description |
|---|---|
| `image_remove_background` | AI matting via rembg (U2Net) |
| `image_chroma_key` | Green/blue screen removal with spill suppression |
| `image_double_background_matte` | Black+white background differential alpha extraction |

### Image Processing
| Tool | Description |
|---|---|
| `image_remove_gemini_watermark` | Remove Gemini AI watermark via reverse alpha blending |
| `image_resize` | Scale image (lanczos/nearest/bilinear) |
| `image_crop` | Crop to rectangle |
| `image_merge_grid` | Merge multiple images into grid atlas |

### GIF & Sprite Sheet
| Tool | Description |
|---|---|
| `gif_extract_frames` | Extract all frames from animated GIF |
| `frames_to_gif` | Combine image sequence into animated GIF |
| `spritesheet_split` | Split sprite sheet by uniform grid |
| `spritesheet_compose` | Compose frames into sprite sheet with index |

### Pixel Art
| Tool | Description |
|---|---|
| `image_pixelate` | Proper pixel art conversion (OpenCV mesh detection) |
| `image_pixelate_simple` | Simple uniform-grid pixelation (fast) |

## Requirements

- Python 3.11+
- FFmpeg (in PATH, for video tools)
- rembg models auto-download on first use (~176MB)

## Install

```bash
pip install frame-ronin-mcp
```

Or from source:

```bash
git clone https://github.com/systemchester/FrameRonin-MCP.git
cd FrameRonin-MCP
pip install -e .
```

## Configure Claude Code

Add to `.claude/mcp.json`:

```json
{
  "mcpServers": {
    "frame-ronin": {
      "command": "python",
      "args": ["-m", "frame_ronin_mcp.server"]
    }
  }
}
```

Or after `pip install`:

```json
{
  "mcpServers": {
    "frame-ronin": {
      "command": "frame-ronin-mcp"
    }
  }
}
```

## Usage Examples

### Extract sprite sheet from video

```
> Use frame-ronin to convert video.mp4 to a sprite sheet at 12fps, 256x256 frames
```

### Remove green screen

```
> Remove the green screen from actor.png with tolerance 40 and smoothness 30
```

### Pixelate an image

```
> Convert artwork.png to pixel art with 16 colors and 4x output scale
```

### Remove Gemini watermark

```
> Clean the Gemini watermark from generated_image.png
```

## Project Structure

```
FrameRonin-MCP/
├── src/frame_ronin_mcp/
│   ├── server.py              # MCP server entry point
│   ├── tools/                 # Tool handlers
│   │   ├── video.py           # Video processing
│   │   ├── matting.py         # Background removal
│   │   ├── image.py           # Image operations
│   │   ├── gif_sprite.py      # GIF & sprite sheet
│   │   └── pixelate.py        # Pixel art conversion
│   └── lib/                   # Core algorithms
│       ├── watermark.py       # Gemini watermark removal
│       ├── chroma_key.py      # Chroma key matting
│       ├── double_bg.py       # Double background matting
│       ├── mesh.py            # OpenCV grid detection
│       └── pixelate_core.py   # Proper pixel art algorithm
├── pyproject.toml
└── requirements.txt
```

## License

MIT — see [LICENSE](LICENSE).

## Related

- [FrameRonin](https://github.com/systemchester/FrameRonin) — web application with UI
- [proper-pixel-art](https://github.com/KennethJAllen/proper-pixel-art) — pixel art algorithm
- [GeminiWatermarkTool](https://github.com/allenk/GeminiWatermarkTool) — watermark removal
