"""
Gemini generation MCP tools — uses Playwright to automate the free web app.

- gemini_generate_image: Generate an image, return path.
- gemini_generate_rpgmaker: Generate + full RPG Maker pipeline.
"""

from pathlib import Path

from ..lib.gemini_generator import generate
from ..lib.watermark import remove_gemini_watermark
from ..lib.image_utils import load_image, save_image


def handle_gemini_generate(args: dict) -> dict:
    """
    Generate an image using Gemini (free web app via Playwright).

    First call opens a browser for Google login.
    Subsequent calls reuse the saved session (headless if requested).

    Required: prompt (str)
    Optional: output_path (str), headless (bool, default false)
    """
    prompt = args["prompt"]
    output_path = args.get("output_path")
    headless = bool(args.get("headless", False))

    result_path = generate(
        prompt=prompt,
        output_path=output_path,
        headless=headless,
    )

    return {
        "output_path": str(result_path),
        "size": result_path.stat().st_size,
    }


def handle_gemini_generate_rpgmaker(args: dict) -> dict:
    """
    Generate pixel art RPG Maker character sprite sheet via Gemini,
    then automatically: remove watermark → AI background removal → resize → split frames.

    Required: prompt (str) — describe the character
    Optional: output_dir (str), width/height (default 48),
              rows/columns (default 4), headless (bool)

    Returns: paths to raw, clean, nobg, resized images, and frame list.
    """
    import io
    from rembg import remove, new_session

    prompt = args["prompt"]
    output_dir = Path(args.get("output_dir", "rpgmaker_output"))
    output_dir.mkdir(parents=True, exist_ok=True)

    headless = bool(args.get("headless", False))
    target_w = int(args.get("width", 48))
    target_h = int(args.get("height", 48))
    rows = int(args.get("rows", 4))
    cols = int(args.get("columns", 4))

    # Enhance prompt for RPG Maker sprite sheet
    full_prompt = (
        f"{prompt}\n\n"
        f"Generate as a pixel art RPG Maker MV sprite sheet: "
        f"exactly {rows} rows × {cols} columns of {target_w}x{target_h} pixel frames. "
        f"White background. Clean pixel edges, no anti-aliasing. "
        f"Each frame should show different poses/animations."
    )

    result = {"steps": []}

    # Step 1: Generate
    raw_path = output_dir / "01_raw.png"
    gen_path = generate(prompt=full_prompt, output_path=raw_path, headless=headless)
    result["raw_path"] = str(gen_path)
    result["steps"].append("generate")

    img = load_image(gen_path)
    w, h = img.size
    result["generated_size"] = {"width": w, "height": h}

    # Step 2: Remove Gemini watermark
    clean_path = output_dir / "02_clean.png"
    img = remove_gemini_watermark(img)
    save_image(img, clean_path)
    result["clean_path"] = str(clean_path)
    result["steps"].append("dewatermark")

    # Step 3: AI Background removal
    nobg_path = output_dir / "03_nobg.png"
    session = new_session("u2net")
    buf = io.BytesIO()
    img.save(buf, "PNG")
    data = remove(buf.getvalue(), session=session)
    img = load_image(data)
    save_image(img, nobg_path)
    result["nobg_path"] = str(nobg_path)
    result["steps"].append("matte")

    # Step 4: Resize to sheet size
    sheet_w = cols * target_w
    sheet_h = rows * target_h
    resized = img.resize((sheet_w, sheet_h), __import__("PIL.Image").Image.Resampling.LANCZOS)
    resized_path = output_dir / "04_resized.png"
    save_image(resized, resized_path)
    result["resized_path"] = str(resized_path)
    result["sheet_size"] = {"width": sheet_w, "height": sheet_h}
    result["steps"].append("resize")

    # Step 5: Split into individual frames
    frames_dir = output_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    frame_paths = []
    for row in range(rows):
        for col in range(cols):
            x, y = col * target_w, row * target_h
            frame = resized.crop((x, y, x + target_w, y + target_h))
            fp = frames_dir / f"frame_r{row:02d}_c{col:02d}.png"
            frame.save(fp, "PNG")
            frame_paths.append(str(fp))
    result["frames"] = frame_paths
    result["frame_count"] = len(frame_paths)
    result["steps"].append("split_frames")

    return result
