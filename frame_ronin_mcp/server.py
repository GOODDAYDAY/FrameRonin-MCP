"""
FrameRonin MCP Server — all-in-one pixel art & game asset pipeline for AI.

  Generate: generate_gemini, generate_dalle, generate_stability,
            generate_gemini_api, generate_rpgmaker (multi-backend pipeline)
  Video:    video_to_spritesheet, video_get_info, video_remove_watermark
  Matting:  image_remove_background, image_chroma_key, image_double_background_matte
  Image:    image_remove_gemini_watermark, image_resize, image_crop, image_merge_grid
  GIF:      gif_extract_frames, frames_to_gif
  Sprite:   spritesheet_split, spritesheet_compose
  Pixel:    image_pixelate, image_pixelate_simple

Usage: pip install frame-ronin-mcp && frame-ronin-mcp
"""

import json
import asyncio

from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types

from .tools.video import (
    handle_video_to_spritesheet,
    handle_video_get_info,
    handle_video_remove_watermark,
)
from .tools.matting import (
    handle_image_remove_background,
    handle_image_chroma_key,
    handle_image_double_background_matte,
)
from .tools.image import (
    handle_image_remove_gemini_watermark,
    handle_image_resize,
    handle_image_crop,
    handle_image_merge_grid,
)
from .tools.gif_sprite import (
    handle_gif_extract_frames,
    handle_frames_to_gif,
    handle_spritesheet_split,
    handle_spritesheet_compose,
)
from .tools.pixelate import (
    handle_image_pixelate,
    handle_image_pixelate_simple,
)
from .tools.generate import (
    handle_generate_gemini,
    handle_generate_dalle,
    handle_generate_stability,
    handle_generate_gemini_api,
    handle_generate_rpgmaker,
)


# ── Tool definitions ──────────────────────────────────────────────────────

TOOLS = [
    # ── Phase 1: Video ──
    types.Tool(
        name="video_to_spritesheet",
        description=(
            "Extract frames from a video file, optionally remove the background "
            "from each frame using AI (rembg/U2Net), and compose them into a "
            "single sprite sheet image with an index JSON file. "
            "Useful for creating 2D game character animations from video footage."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "video_path": {
                    "type": "string",
                    "description": "Path to the input video file (mp4, mov, webm, avi, mkv).",
                },
                "output_dir": {
                    "type": "string",
                    "description": "Directory for output files (sprite.png + index.json). Default: video's directory/spritesheet_output.",
                },
                "fps": {
                    "type": "integer",
                    "description": "Target frames per second for extraction (1-60, default 12).",
                    "default": 12,
                },
                "start_sec": {
                    "type": "number",
                    "description": "Start time in seconds (default 0).",
                    "default": 0,
                },
                "end_sec": {
                    "type": "number",
                    "description": "End time in seconds (default: video duration).",
                },
                "max_frames": {
                    "type": "integer",
                    "description": "Maximum number of frames to extract (default 300).",
                    "default": 300,
                },
                "target_w": {
                    "type": "integer",
                    "description": "Target frame width in pixels (default 256).",
                    "default": 256,
                },
                "target_h": {
                    "type": "integer",
                    "description": "Target frame height in pixels (default 256).",
                    "default": 256,
                },
                "spacing": {
                    "type": "integer",
                    "description": "Spacing between frames in sprite sheet (default 4).",
                    "default": 4,
                },
                "columns": {
                    "type": "integer",
                    "description": "Number of columns in sprite sheet layout (default 12).",
                    "default": 12,
                },
                "remove_bg": {
                    "type": "boolean",
                    "description": "Whether to run AI background removal on each frame (default true).",
                    "default": True,
                },
            },
            "required": ["video_path"],
        },
    ),
    types.Tool(
        name="video_get_info",
        description="Probe a video file and return its metadata: duration, resolution, fps, frame count.",
        inputSchema={
            "type": "object",
            "properties": {
                "video_path": {
                    "type": "string",
                    "description": "Path to the video file.",
                },
            },
            "required": ["video_path"],
        },
    ),
    types.Tool(
        name="video_remove_watermark",
        description=(
            "Remove the 'AI生成' watermark from Seedance/Jiemeng videos "
            "by cropping the bottom ~180px. For local backend deployments."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "video_path": {
                    "type": "string",
                    "description": "Path to the video file with watermark.",
                },
                "output_path": {
                    "type": "string",
                    "description": "Path for the cleaned output video.",
                },
            },
            "required": ["video_path"],
        },
    ),

    # ── Phase 1: AI Matting ──
    types.Tool(
        name="image_remove_background",
        description=(
            "AI-powered background removal using rembg (U2Net model). "
            "Upload an image and get back a transparent PNG. "
            "First run downloads the ~176MB model, so it may be slow initially."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "image_path": {
                    "type": "string",
                    "description": "Path to the input image (png, jpg, webp).",
                },
                "output_path": {
                    "type": "string",
                    "description": "Path for the result PNG with transparent background.",
                },
            },
            "required": ["image_path"],
        },
    ),

    # ── Phase 2: Chroma Key & Double BG ──
    types.Tool(
        name="image_chroma_key",
        description=(
            "Remove a green or blue screen background from an image using chroma key. "
            "Parameters: key_color (green/blue/hex), tolerance, smoothness, spill suppression, "
            "and edge erosion."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "image_path": {
                    "type": "string",
                    "description": "Path to the input image.",
                },
                "output_path": {
                    "type": "string",
                    "description": "Path for the result PNG with transparent background.",
                },
                "key_color": {
                    "type": "string",
                    "description": "Key color: 'green', 'blue', or '#RRGGBB' hex (default 'green').",
                    "default": "green",
                },
                "tolerance": {
                    "type": "integer",
                    "description": "How strictly to match key color, 0-100 (default 35).",
                    "default": 35,
                },
                "smoothness": {
                    "type": "integer",
                    "description": "Transition band width, 0-100 (default 34).",
                    "default": 34,
                },
                "spill": {
                    "type": "integer",
                    "description": "Color spill suppression, 0-100 (default 75).",
                    "default": 75,
                },
                "erosion": {
                    "type": "integer",
                    "description": "Edge alpha erosion, 0-100 (default 0).",
                    "default": 0,
                },
            },
            "required": ["image_path"],
        },
    ),
    types.Tool(
        name="image_double_background_matte",
        description=(
            "Extract alpha channel from paired images of the same subject "
            "shot on pure black (#000000) and pure white (#FFFFFF) backgrounds. "
            "The difference between the two reveals the transparency of each pixel.\n\n"
            "IMPORTANT: Both images must have exactly the same dimensions and camera position. "
            "Only the background color should differ."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "black_image_path": {
                    "type": "string",
                    "description": "Path to the image with black background.",
                },
                "white_image_path": {
                    "type": "string",
                    "description": "Path to the image with white background.",
                },
                "output_path": {
                    "type": "string",
                    "description": "Path for the result PNG with transparent background.",
                },
                "tolerance": {
                    "type": "integer",
                    "description": "50-100, lower = more aggressive BG removal (default 70).",
                    "default": 70,
                },
                "edge_contrast": {
                    "type": "integer",
                    "description": "50-100, gamma on alpha for sharper edges (default 53).",
                    "default": 53,
                },
                "post_process": {
                    "type": "boolean",
                    "description": "Apply post-processing (composite boost, threshold, small-island removal).",
                    "default": False,
                },
                "erosion": {
                    "type": "integer",
                    "description": "Edge alpha erosion after post-processing, 0-100 (default 0).",
                    "default": 0,
                },
            },
            "required": ["black_image_path", "white_image_path"],
        },
    ),

    # ── Phase 2: Image Processing ──
    types.Tool(
        name="image_remove_gemini_watermark",
        description=(
            "Remove the Gemini AI watermark from images generated by Google Gemini. "
            "Uses reverse alpha blending with the embedded watermark mask. "
            "Works on both 48px (small images) and 96px (large >1024px) watermarks."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "image_path": {
                    "type": "string",
                    "description": "Path to the Gemini-generated image.",
                },
                "output_path": {
                    "type": "string",
                    "description": "Path for the cleaned image.",
                },
            },
            "required": ["image_path"],
        },
    ),
    types.Tool(
        name="image_resize",
        description=(
            "Resize an image to specified dimensions or by a scale factor. "
            "Provide one of: (width + height), width only (height auto), "
            "height only (width auto), or scale factor only."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "image_path": {
                    "type": "string",
                    "description": "Path to the input image.",
                },
                "output_path": {
                    "type": "string",
                    "description": "Path for the resized image.",
                },
                "width": {
                    "type": "integer",
                    "description": "Target width in pixels.",
                },
                "height": {
                    "type": "integer",
                    "description": "Target height in pixels.",
                },
                "scale": {
                    "type": "number",
                    "description": "Scale multiplier (e.g., 2.0 = double size, 0.5 = half).",
                },
                "method": {
                    "type": "string",
                    "enum": ["lanczos", "nearest", "bilinear", "bicubic"],
                    "description": "Resampling method (default 'lanczos'). Use 'nearest' for pixel art.",
                    "default": "lanczos",
                },
            },
            "required": ["image_path"],
        },
    ),
    types.Tool(
        name="image_crop",
        description="Crop an image to a specified rectangle.",
        inputSchema={
            "type": "object",
            "properties": {
                "image_path": {
                    "type": "string",
                    "description": "Path to the input image.",
                },
                "output_path": {
                    "type": "string",
                    "description": "Path for the cropped image.",
                },
                "x": {
                    "type": "integer",
                    "description": "Left coordinate (default 0).",
                    "default": 0,
                },
                "y": {
                    "type": "integer",
                    "description": "Top coordinate (default 0).",
                    "default": 0,
                },
                "width": {
                    "type": "integer",
                    "description": "Crop width in pixels.",
                },
                "height": {
                    "type": "integer",
                    "description": "Crop height in pixels.",
                },
            },
            "required": ["image_path"],
        },
    ),
    types.Tool(
        name="image_merge_grid",
        description=(
            "Merge multiple images into a single sprite/atlas arranged in a grid layout. "
            "Useful for creating sprite sheets from individual frames."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "image_paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of image file paths to merge.",
                },
                "columns": {
                    "type": "integer",
                    "description": "Number of columns in the grid layout.",
                },
                "output_path": {
                    "type": "string",
                    "description": "Path for the output merged image.",
                },
                "cell_w": {
                    "type": "integer",
                    "description": "Cell width in pixels (default: max image width).",
                },
                "cell_h": {
                    "type": "integer",
                    "description": "Cell height in pixels (default: max image height).",
                },
                "spacing": {
                    "type": "integer",
                    "description": "Spacing between cells (default 0).",
                    "default": 0,
                },
            },
            "required": ["image_paths", "columns"],
        },
    ),

    # ── Phase 2: GIF & Sprite Sheet ──
    types.Tool(
        name="gif_extract_frames",
        description="Extract all individual frames from an animated GIF as PNG files.",
        inputSchema={
            "type": "object",
            "properties": {
                "gif_path": {
                    "type": "string",
                    "description": "Path to the animated GIF file.",
                },
                "output_dir": {
                    "type": "string",
                    "description": "Directory to save extracted frame PNGs.",
                },
                "output_format": {
                    "type": "string",
                    "enum": ["png", "jpg"],
                    "description": "Output format (default 'png').",
                    "default": "png",
                },
            },
            "required": ["gif_path"],
        },
    ),
    types.Tool(
        name="frames_to_gif",
        description="Combine a sequence of images into an animated GIF.",
        inputSchema={
            "type": "object",
            "properties": {
                "frame_paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of image file paths in animation order.",
                },
                "output_path": {
                    "type": "string",
                    "description": "Path for the output GIF.",
                },
                "duration": {
                    "type": "integer",
                    "description": "Duration per frame in milliseconds (default 100).",
                    "default": 100,
                },
                "loop": {
                    "type": "integer",
                    "description": "Loop count (0 = infinite, default 0).",
                    "default": 0,
                },
            },
            "required": ["frame_paths"],
        },
    ),
    types.Tool(
        name="spritesheet_split",
        description=(
            "Split a sprite sheet into individual frame images by a uniform grid. "
            "Specify the number of columns and rows, and optionally margins/spacing."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "image_path": {
                    "type": "string",
                    "description": "Path to the sprite sheet image.",
                },
                "columns": {
                    "type": "integer",
                    "description": "Number of columns in the grid.",
                },
                "rows": {
                    "type": "integer",
                    "description": "Number of rows in the grid.",
                },
                "output_dir": {
                    "type": "string",
                    "description": "Directory to save individual frame PNGs.",
                },
                "margin_x": {
                    "type": "integer",
                    "description": "Left/right margin in pixels (default 0).",
                    "default": 0,
                },
                "margin_y": {
                    "type": "integer",
                    "description": "Top/bottom margin in pixels (default 0).",
                    "default": 0,
                },
                "spacing_x": {
                    "type": "integer",
                    "description": "Horizontal spacing between cells (default 0).",
                    "default": 0,
                },
                "spacing_y": {
                    "type": "integer",
                    "description": "Vertical spacing between cells (default 0).",
                    "default": 0,
                },
            },
            "required": ["image_path", "columns", "rows"],
        },
    ),
    types.Tool(
        name="spritesheet_compose",
        description=(
            "Compose individual frame images into a single sprite sheet. "
            "Frames are arranged in a grid layout with optional spacing. "
            "Each frame is centered in its cell. Returns frame index metadata."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "frame_paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of frame image file paths.",
                },
                "output_path": {
                    "type": "string",
                    "description": "Path for the output sprite sheet PNG.",
                },
                "columns": {
                    "type": "integer",
                    "description": "Number of columns (default: auto-square).",
                },
                "cell_w": {
                    "type": "integer",
                    "description": "Cell width in pixels (default: max frame width).",
                },
                "cell_h": {
                    "type": "integer",
                    "description": "Cell height in pixels (default: max frame height).",
                },
                "spacing": {
                    "type": "integer",
                    "description": "Spacing between cells (default 0).",
                    "default": 0,
                },
                "bg_color": {
                    "type": "string",
                    "description": "Background color: 'transparent' or '#RRGGBB' (default 'transparent').",
                    "default": "transparent",
                },
            },
            "required": ["frame_paths"],
        },
    ),

    # ── Phase 3: Pixel Art ──
    types.Tool(
        name="image_pixelate",
        description=(
            "Convert an image to pixel art using the proper-pixel-art algorithm. "
            "Uses OpenCV to detect the original pixel grid via Canny edge detection "
            "and Hough line transforms, then downsamples each grid cell to its most "
            "common color. Best for pixel art restoration and downscaling.\n\n"
            "For simpler/faster pixelation without mesh detection, use image_pixelate_simple."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "image_path": {
                    "type": "string",
                    "description": "Path to the input image.",
                },
                "output_path": {
                    "type": "string",
                    "description": "Path for the pixel art output PNG.",
                },
                "upscale": {
                    "type": "integer",
                    "description": "Nearest-neighbor scale before mesh detection, 1-7 (default 1).",
                    "default": 1,
                },
                "num_colors": {
                    "type": "integer",
                    "description": "Number of colors for quantization. Omit for no quantization.",
                },
                "scale_result": {
                    "type": "integer",
                    "description": "Nearest-neighbor output scale per logical pixel, 1-5 (default 1).",
                    "default": 1,
                },
                "transparent_background": {
                    "type": "boolean",
                    "description": "Make white-ish pixels transparent (default false).",
                    "default": False,
                },
            },
            "required": ["image_path"],
        },
    ),
    types.Tool(
        name="image_pixelate_simple",
        description=(
            "Convert an image to pixel art using a simple uniform grid. "
            "Divides the image into pixel_size×pixel_size blocks and takes "
            "the median color of each. Much faster than image_pixelate — no "
            "OpenCV mesh detection needed. Good for quick pixel art effects."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "image_path": {
                    "type": "string",
                    "description": "Path to the input image.",
                },
                "output_path": {
                    "type": "string",
                    "description": "Path for the pixel art output PNG.",
                },
                "pixel_size": {
                    "type": "integer",
                    "description": "Size of each pixel block (default 8).",
                    "default": 8,
                },
                "num_colors": {
                    "type": "integer",
                    "description": "Number of colors for quantization. Omit for no quantization.",
                },
            },
            "required": ["image_path"],
        },
    ),
    # ── Image Generation (multi-backend) ──
    types.Tool(
        name="generate_gemini",
        description=(
            "Generate an image using Gemini's FREE web app (gemini.google.com) via Playwright browser automation. "
            "No API key needed. First call opens Chrome for Google login — subsequent calls reuse the saved session. "
            "Best for: free, no setup required.\n"
            "For API-based backends, see: generate_dalle (OpenAI), generate_stability, generate_gemini_api."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "Image description. Be specific about style, format, background."},
                "output_path": {"type": "string", "description": "Save path (default: gemini_web.png)."},
                "headless": {"type": "boolean", "description": "Run browser invisibly. Needs prior login. Default false.", "default": False},
            },
            "required": ["prompt"],
        },
    ),
    types.Tool(
        name="generate_dalle",
        description=(
            "Generate an image using OpenAI DALL-E 3. Requires OPENAI_API_KEY env var or api_key parameter. "
            "Get key: https://platform.openai.com/api-keys\n"
            "Best for: high-quality, natural language understanding, diverse styles."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "Image description."},
                "output_path": {"type": "string", "description": "Save path (default: dalle.png)."},
                "api_key": {"type": "string", "description": "OpenAI API key (or set OPENAI_API_KEY env var)."},
                "size": {"type": "string", "description": "Image size: 1024x1024, 1792x1024, or 1024x1792 (default 1024x1024).", "default": "1024x1024"},
            },
            "required": ["prompt"],
        },
    ),
    types.Tool(
        name="generate_stability",
        description=(
            "Generate an image using Stability AI (Stable Diffusion). Requires STABILITY_API_KEY env var or api_key parameter. "
            "Get key: https://platform.stability.ai\n"
            "Best for: pixel art, game assets, fine-grained style control."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "Image description."},
                "output_path": {"type": "string", "description": "Save path (default: stability.png)."},
                "api_key": {"type": "string", "description": "Stability API key (or set STABILITY_API_KEY env var)."},
            },
            "required": ["prompt"],
        },
    ),
    types.Tool(
        name="generate_gemini_api",
        description=(
            "Generate an image using the Gemini API (google-genai SDK). Requires GOOGLE_API_KEY with billing enabled. "
            "Get key: https://aistudio.google.com/apikey — this is the PAID tier, not the free web app. "
            "For the free version, use generate_gemini instead."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "Image description."},
                "output_path": {"type": "string", "description": "Save path (default: gemini_api.png)."},
                "api_key": {"type": "string", "description": "Google API key (or set GOOGLE_API_KEY env var)."},
                "model": {"type": "string", "description": "Model name (default: gemini-2.5-flash-image).", "default": "gemini-2.5-flash-image"},
            },
            "required": ["prompt"],
        },
    ),
    types.Tool(
        name="generate_rpgmaker",
        description=(
            "FULL PIPELINE: generate a pixel art RPG Maker character sprite sheet using any backend, "
            "then automatically post-process: remove watermark → AI background removal → resize → split into individual frames.\n\n"
            "Choose backend with the 'backend' parameter:\n"
            "  gemini  — free Gemini web app, no key (default)\n"
            "  dalle   — DALL-E 3, needs OPENAI_API_KEY\n"
            "  stability — Stability AI, needs STABILITY_API_KEY\n"
            "  gemini_api — Gemini API, needs GOOGLE_API_KEY with billing\n\n"
            "The prompt is automatically enhanced with RPG Maker MV formatting (grid layout, white bg, pixel edges).\n"
            "Output: 01_raw.png, 02_clean.png, 03_nobg.png, 04_resized.png, and individual frame PNGs."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "Describe the character (e.g. 'fire mage with staff, red robes'). RPG Maker formatting auto-added."},
                "output_dir": {"type": "string", "description": "Output directory (default: rpgmaker_output).", "default": "rpgmaker_output"},
                "backend": {"type": "string", "description": "Generation backend: gemini, dalle, stability, gemini_api (default: gemini).", "default": "gemini"},
                "width": {"type": "integer", "description": "Frame width (default 48).", "default": 48},
                "height": {"type": "integer", "description": "Frame height (default 48).", "default": 48},
                "rows": {"type": "integer", "description": "Animation rows (default 4).", "default": 4},
                "columns": {"type": "integer", "description": "Frames per row (default 4).", "default": 4},
                "headless": {"type": "boolean", "description": "Run browser headless (gemini backend only, needs prior login).", "default": False},
                "api_key": {"type": "string", "description": "API key for the chosen backend (or set env var)."},
            },
            "required": ["prompt"],
        },
    ),
]

# ── Tool handler dispatch ─────────────────────────────────────────────────

_HANDLERS = {
    "video_to_spritesheet": handle_video_to_spritesheet,
    "video_get_info": handle_video_get_info,
    "video_remove_watermark": handle_video_remove_watermark,
    "image_remove_background": handle_image_remove_background,
    "image_chroma_key": handle_image_chroma_key,
    "image_double_background_matte": handle_image_double_background_matte,
    "image_remove_gemini_watermark": handle_image_remove_gemini_watermark,
    "image_resize": handle_image_resize,
    "image_crop": handle_image_crop,
    "image_merge_grid": handle_image_merge_grid,
    "gif_extract_frames": handle_gif_extract_frames,
    "frames_to_gif": handle_frames_to_gif,
    "spritesheet_split": handle_spritesheet_split,
    "spritesheet_compose": handle_spritesheet_compose,
    "image_pixelate": handle_image_pixelate,
    "image_pixelate_simple": handle_image_pixelate_simple,
    "generate_gemini": handle_generate_gemini,
    "generate_dalle": handle_generate_dalle,
    "generate_stability": handle_generate_stability,
    "generate_gemini_api": handle_generate_gemini_api,
    "generate_rpgmaker": handle_generate_rpgmaker,
}


# ── Server ─────────────────────────────────────────────────────────────────

server = Server("frame-ronin-mcp")


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    handler = _HANDLERS.get(name)
    if handler is None:
        return [types.TextContent(
            type="text",
            text=json.dumps({"error": f"Unknown tool: {name}"}, ensure_ascii=False),
        )]

    try:
        result = handler(arguments)
        text = json.dumps(result, indent=2, ensure_ascii=False, default=str)
        return [types.TextContent(type="text", text=text)]
    except Exception as e:
        error_msg = json.dumps({
            "error": str(e),
            "tool": name,
        }, ensure_ascii=False)
        return [types.TextContent(type="text", text=error_msg)]


async def main_async():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream)


def main():
    """Entry point for `frame-ronin-mcp` command."""
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
