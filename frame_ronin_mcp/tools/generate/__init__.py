"""
Multi-backend image generation MCP tools.

Backends:
  gemini_web   — Gemini free web app (Playwright), no key needed
  gemini_api   — Gemini API (google-genai), needs GOOGLE_API_KEY + billing
  dalle        — OpenAI DALL-E 3, needs OPENAI_API_KEY
  stability    — Stability AI, needs STABILITY_API_KEY

Each backend is self-contained in its own file. Add new backends by
creating a new module with a `generate(prompt, output_path, **kw) -> Path` function.

All prompts are automatically expanded to 2000+ chars with pixel art
technical requirements (palette, anti-aliasing rules, sprite sheet layout, etc.)
unless the user prompt is already detailed enough.

MCP tools:
  generate_gemini      — Gemini free web app
  generate_dalle        — DALL-E 3
  generate_stability    — Stability AI
  generate_gemini_api   — Gemini API (paid)
  generate_siliconflow  — SiliconFlow (Qwen/FLUX)
  generate_rpgmaker     — any backend → full RPG Maker pipeline
"""

from pathlib import Path

from . import gemini_web, gemini_api, dalle, stability, siliconflow

# Backend registry — maps backend name to module
BACKENDS = {
    "gemini": gemini_web,
    "gemini_api": gemini_api,
    "dalle": dalle,
    "stability": stability,
    "siliconflow": siliconflow,
}

DEFAULT_BACKEND = "gemini"  # free, no key needed

# ── Prompt expansion ──────────────────────────────────────────────────────

_PIXEL_ART_SPEC = """
PIXEL ART TECHNICAL REQUIREMENTS:
- True pixel art style, absolutely NO anti-aliasing, NO blur, NO gradients between colors
- Each pixel must be a single solid color with hard edges
- Use a limited, well-chosen color palette with distinct shades for highlights and shadows
- Every pixel intentionally placed — no random noise, no AI smear
- Clean silhouette with clear readable shapes at small scale
- Dithering (checkerboard pattern) for color transitions where needed
- Consistent light source from top-left across all frames
- 1px dark outline on character/enemy silhouettes for game readability

SPRITE SHEET LAYOUT:
- Exactly 4 rows and 4 columns = 16 frames total
- White background (#FFFFFF) for every frame
- Each row = one animation direction or state, each column = one frame
- Top row: facing down / idle animation
- Second row: facing left / walk or action cycle
- Third row: facing right / walk or action cycle (mirror of row 2)
- Bottom row: facing up / alternate state
- Frames within a row must form a smooth animation loop when played in sequence
- Clear visual separation between frame cells

OUTPUT FORMAT:
- Single PNG image, white background
- Sprite sheet fills most of the image canvas
- Frames arranged as a clean grid
"""

_RPGMAKER_SPEC = """
RPG MAKER MV FORMAT REQUIREMENTS:
- The sprite sheet must follow RPG Maker MV character sheet conventions
- 4 rows (directions: down, left, right, up) × 4 columns (animation frames)
- Each character frame cell should be exactly 48×48 pixels in the final output
- The engine reads row 0 as facing-down, row 1 as facing-left, row 2 as facing-right, row 3 as facing-up
- File naming: prefix with $ for single-character sheets (e.g. $hero.png)
- Transparent or white background accepted — white is preferred for clarity
"""


def expand_prompt(prompt: str, style: str = "pixel_art") -> str:
    """
    Expand a short user prompt into a detailed 2000+ char prompt
    with professional pixel art / RPG Maker specifications.

    If the prompt is already detailed enough (1000+ chars), pass through as-is.
    """
    if len(prompt) >= 1000:
        return prompt

    spec = _PIXEL_ART_SPEC
    if style == "rpgmaker":
        spec = _RPGMAKER_SPEC + _PIXEL_ART_SPEC

    expanded = f"{prompt}\n\n{spec}"
    return expanded


def _rpgmaker_pipeline(
    prompt: str,
    output_dir: Path,
    backend: str,
    target_w: int,
    target_h: int,
    rows: int,
    cols: int,
    headless: bool,
    api_key: str,
) -> dict:
    """Full pipeline: generate → watermark → white-to-alpha → resize(nearest) → split."""
    from PIL import Image as PILImage
    from ...lib.watermark import remove_gemini_watermark
    from ...lib.image_utils import load_image, save_image, white_to_alpha

    mod = BACKENDS.get(backend, gemini_web)

    # Build RPG Maker prompt with expansion
    prompt = expand_prompt(prompt, style="rpgmaker")
    full_prompt = (
        f"{prompt}\n"
        f"Generate as a pixel art RPG Maker MV sprite sheet: "
        f"exactly {rows} rows x {cols} columns of {target_w}x{target_h} pixel frames. "
        f"White background. Clean pixel edges, no anti-aliasing. "
        f"Each frame should be a distinct pose/animation step."
    )

    result = {"backend": backend, "steps": []}

    # Step 1: Generate
    raw = output_dir / "01_raw.png"
    kwargs = {"output_path": raw}
    if backend == "gemini":
        kwargs["headless"] = headless
    else:
        kwargs["api_key"] = api_key
    mod.generate(prompt=full_prompt, **kwargs)
    result["raw_path"] = str(raw)
    result["steps"].append("generate")

    # Step 2: Watermark
    img = load_image(raw)
    w, h = img.size
    result["generated_size"] = {"width": w, "height": h}
    clean = output_dir / "02_clean.png"
    save_image(remove_gemini_watermark(img), clean)
    result["clean_path"] = str(clean)
    result["steps"].append("dewatermark")

    # Step 3: White → transparent (pixel-art-safe, no AI blur)
    nobg = output_dir / "03_nobg.png"
    img = load_image(clean)
    img = white_to_alpha(img)
    save_image(img, nobg)
    result["nobg_path"] = str(nobg)
    result["steps"].append("white_to_alpha")

    # Step 4: Resize with NEAREST (preserves pixel art)
    sheet_w, sheet_h = cols * target_w, rows * target_h
    resized = img.resize((sheet_w, sheet_h), PILImage.Resampling.NEAREST)
    rp = output_dir / "04_resized.png"
    save_image(resized, rp)
    result["resized_path"] = str(rp)
    result["sheet_size"] = {"width": sheet_w, "height": sheet_h}
    result["steps"].append("resize")

    # Step 5: Split frames
    fd = output_dir / "frames"
    fd.mkdir(parents=True, exist_ok=True)
    frames = []
    for row in range(rows):
        for col in range(cols):
            x, y = col * target_w, row * target_h
            f = resized.crop((x, y, x + target_w, y + target_h))
            fp = fd / f"frame_r{row:02d}_c{col:02d}.png"
            f.save(fp, "PNG")
            frames.append(str(fp))
    result["frames"] = frames
    result["frame_count"] = len(frames)
    result["steps"].append("split_frames")
    return result


# ── MCP tool handlers ────────────────────────────────────────────────────

def _make_generate_handler(backend_name: str):
    """Factory: create a handler for a specific backend."""
    mod = BACKENDS[backend_name]

    def handler(args: dict) -> dict:
        prompt = args["prompt"]
        prompt = expand_prompt(prompt, style="pixel_art")
        output_path = args.get("output_path")
        kwargs = {"prompt": prompt, "output_path": output_path}

        if backend_name == "gemini":
            kwargs["headless"] = bool(args.get("headless", False))
        else:
            key = args.get("api_key", "")
            if not key:
                env_map = {"gemini_api": "GOOGLE_API_KEY", "dalle": "OPENAI_API_KEY", "stability": "STABILITY_API_KEY", "siliconflow": "SILICONFLOW_API_KEY"}
                import os
                key = os.environ.get(env_map.get(backend_name, ""), "")
            kwargs["api_key"] = key

        p = mod.generate(**kwargs)
        return {"output_path": str(p), "backend": backend_name, "size": p.stat().st_size}

    return handler


def handle_generate_gemini(args: dict) -> dict:
    return _make_generate_handler("gemini")(args)


def handle_generate_dalle(args: dict) -> dict:
    return _make_generate_handler("dalle")(args)


def handle_generate_stability(args: dict) -> dict:
    return _make_generate_handler("stability")(args)


def handle_generate_gemini_api(args: dict) -> dict:
    return _make_generate_handler("gemini_api")(args)


def handle_generate_siliconflow(args: dict) -> dict:
    return _make_generate_handler("siliconflow")(args)


def handle_generate_rpgmaker(args: dict) -> dict:
    """Full RPG Maker pipeline using any backend."""
    prompt = args["prompt"]
    output_dir = Path(args.get("output_dir", "rpgmaker_output"))
    output_dir.mkdir(parents=True, exist_ok=True)
    backend = args.get("backend", "gemini")
    target_w = int(args.get("width", 48))
    target_h = int(args.get("height", 48))
    rows = int(args.get("rows", 4))
    cols = int(args.get("columns", 4))
    headless = bool(args.get("headless", False))
    api_key = args.get("api_key", "")

    return _rpgmaker_pipeline(prompt, output_dir, backend, target_w, target_h, rows, cols, headless, api_key)
