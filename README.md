# FrameRonin MCP Server

One MCP server for the complete pixel art game asset pipeline — Gemini generation → post-processing → game-ready assets.

18 tools in one server.

## Quick Start

```bash
pip install frame-ronin-mcp
frame-ronin-mcp
```

Then add to `.claude/mcp.json`:

```json
{
  "mcpServers": {
    "frame-ronin": {
      "command": "frame-ronin-mcp"
    }
  }
}
```

## Tools (18)

### Gemini Generation
| Tool | Description |
|---|---|
| `gemini_generate` | Generate image via Gemini free web app (Playwright — login once, reuse forever) |
| `gemini_generate_rpgmaker` | Full pipeline: generate → watermark removal → AI matting → resize → split frames |

### Video
| Tool | Description |
|---|---|
| `video_to_spritesheet` | Extract frames → AI matting → sprite sheet + index JSON |
| `video_get_info` | Probe video metadata |
| `video_remove_watermark` | Remove Seedance watermark |

### Matting
| Tool | Description |
|---|---|
| `image_remove_background` | AI matting via rembg (U2Net) |
| `image_chroma_key` | Green/blue screen removal |
| `image_double_background_matte` | Black+white differential matting |

### Image Processing
| Tool | Description |
|---|---|
| `image_remove_gemini_watermark` | Remove Gemini watermark |
| `image_resize` | Scale image |
| `image_crop` | Crop to rectangle |
| `image_merge_grid` | Merge images into grid atlas |

### GIF & Sprite Sheet
| Tool | Description |
|---|---|
| `gif_extract_frames` | Extract frames from animated GIF |
| `frames_to_gif` | Combine frames into GIF |
| `spritesheet_split` | Split sprite sheet by grid |
| `spritesheet_compose` | Compose frames into sprite sheet |

### Pixel Art
| Tool | Description |
|---|---|
| `image_pixelate` | Proper pixel art conversion (OpenCV mesh detection) |
| `image_pixelate_simple` | Simple uniform-grid pixelation (fast) |

## Project Structure

```
FrameRonin-MCP/
├── pyproject.toml
├── frame_ronin_mcp/
│   ├── server.py              # MCP entry point (18 tools)
│   ├── tools/
│   │   ├── gemini.py          # Gemini web app generation
│   │   ├── video.py           # Video processing
│   │   ├── matting.py         # Background removal
│   │   ├── image.py           # Image operations
│   │   ├── gif_sprite.py      # GIF & sprite sheet
│   │   └── pixelate.py        # Pixel art conversion
│   └── lib/
│       ├── gemini_generator.py  # Playwright Gemini client
│       ├── watermark.py         # Gemini watermark removal
│       ├── chroma_key.py        # Chroma key matting
│       ├── double_bg.py         # Double background matting
│       ├── mesh.py              # OpenCV grid detection
│       └── pixelate_core.py     # Proper pixel art algorithm
```

## Requirements

- Python 3.11+
- FFmpeg (for video tools)
- Chrome (for Gemini generation — installed automatically by Playwright)

## License

MIT
