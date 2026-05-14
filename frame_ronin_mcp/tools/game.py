"""
Game pipeline orchestration tools for FrameRonin-MCP.
Chain generation → processing → Godot export → verification.
"""

import shutil
from pathlib import Path

from ..lib.godot_format import (
    generate_project_godot, generate_tscn, generate_sprite_frames_tres,
    Vector2, Rect2, ExtResource, SubResource,
)
from ..lib.godot_runner import validate_project
from ..lib.image_utils import load_image, save_image, white_to_alpha
from ..lib.watermark import remove_gemini_watermark


def handle_game_create_blank(args: dict) -> dict:
    """Create a complete blank Godot 4.6 pixel art game project."""
    game_name = args["game_name"]
    output_dir = Path(args["output_dir"])
    res_w = int(args.get("resolution_w", 480))
    res_h = int(args.get("resolution_h", 270))
    game_title = args.get("game_title", game_name)
    renderer = args.get("renderer", "gl_compatibility")

    output_dir.mkdir(parents=True, exist_ok=True)

    # Directory tree
    for d in ["scenes", "sprites", "tilesets", "scripts", "audio", "ui"]:
        (output_dir / d).mkdir(parents=True, exist_ok=True)

    # project.godot
    proj = generate_project_godot(game_title, res_w, res_h, renderer)
    (output_dir / "project.godot").write_text(proj, encoding="utf-8")

    # icon.svg
    (output_dir / "icon.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64">'
        '<rect width="64" height="64" fill="#2b2b2b"/>'
        '<rect x="16" y="20" width="32" height="24" rx="2" fill="#5b8c5a"/>'
        '<circle cx="24" cy="32" r="6" fill="#1a1a2e"/>'
        '<circle cx="40" cy="32" r="6" fill="#1a1a2e"/>'
        '<rect x="24" y="42" width="16" height="4" rx="1" fill="#3a6b3a"/>'
        '</svg>', encoding="utf-8")

    # main.tscn
    main_tscn = generate_tscn("Main", "Node2D", child_nodes=[
        {"name": "Camera", "type": "Camera2D",
         "properties": {"enabled": True, "zoom": Vector2(2, 2), "anchor_mode": 1,
                         "position_smoothing_enabled": True}},
        {"name": "PlayerPlaceholder", "type": "CharacterBody2D",
         "properties": {"position": Vector2(res_w // 2, res_h // 2)}},
    ])
    (output_dir / "scenes" / "main.tscn").write_text(main_tscn, encoding="utf-8")

    # Autoload stubs
    (output_dir / "scripts" / "globals.gd").write_text(
        "extends Node\n\n# Global state and signals\n", encoding="utf-8")
    (output_dir / "scripts" / "game_manager.gd").write_text(
        "extends Node\n\n# Game state management\n", encoding="utf-8")

    files = [
        str(output_dir / "project.godot"),
        str(output_dir / "scenes" / "main.tscn"),
        str(output_dir / "icon.svg"),
        str(output_dir / "scripts" / "globals.gd"),
        str(output_dir / "scripts" / "game_manager.gd"),
    ]

    return {
        "project_dir": str(output_dir),
        "project_path": str(output_dir / "project.godot"),
        "scene_path": str(output_dir / "scenes" / "main.tscn"),
        "game_name": game_name,
        "game_title": game_title,
        "resolution": {"width": res_w, "height": res_h},
        "files": files,
    }


def handle_game_add_character(args: dict) -> dict:
    """
    Add a complete character to a Godot project.
    Either from an existing spritesheet or by generating one via Gemini.
    """
    project_dir = Path(args["project_dir"])
    character_name = args["character_name"]
    spritesheet_path = args.get("spritesheet_path")
    prompt = args.get("prompt")
    backend = args.get("generate_backend", "gemini")
    api_key = args.get("api_key", "")
    rows = int(args.get("rows", 4))
    columns = int(args.get("columns", 4))

    if not (project_dir / "project.godot").exists():
        return {"error": f"No project.godot found in {project_dir}. Create a project first."}

    if not spritesheet_path and not prompt:
        return {"error": "Provide either spritesheet_path or prompt"}

    char_dir = project_dir / "sprites" / character_name
    char_dir.mkdir(parents=True, exist_ok=True)
    steps = []

    # Generate or copy spritesheet
    if prompt and not spritesheet_path:
        from .generate import BACKENDS, expand_prompt, DEFAULT_BACKEND
        mod = BACKENDS.get(backend, BACKENDS[DEFAULT_BACKEND])
        full_prompt = expand_prompt(prompt, style="rpgmaker")
        raw_path = char_dir / f"{character_name}_raw.png"
        kwargs = {"prompt": full_prompt, "output_path": raw_path}
        if backend == "gemini":
            kwargs["headless"] = bool(args.get("headless", False))
        else:
            kwargs["api_key"] = api_key
        mod.generate(**kwargs)
        spritesheet_path = raw_path
        steps.append("generate")

        # Watermark removal
        clean_path = char_dir / f"{character_name}_clean.png"
        img = load_image(spritesheet_path)
        save_image(remove_gemini_watermark(img), clean_path)
        steps.append("dewatermark")

        # White to alpha
        nobg_path = char_dir / f"{character_name}_nobg.png"
        img = load_image(clean_path)
        save_image(white_to_alpha(img), nobg_path)
        steps.append("white_to_alpha")
        spritesheet_path = nobg_path
    else:
        # Copy existing spritesheet
        src = Path(spritesheet_path)
        dst = char_dir / f"{character_name}_sheet.png"
        shutil.copy(src, dst)
        spritesheet_path = dst

    spritesheet_path = Path(spritesheet_path)

    # Auto-detect cell size
    img = load_image(spritesheet_path)
    cell_w = img.width // columns
    cell_h = img.height // rows

    # Resize to exact grid (NEAREST)
    from PIL import Image as PILImage
    sheet_w, sheet_h = columns * cell_w, rows * cell_h
    resized = img.resize((sheet_w, sheet_h), PILImage.Resampling.NEAREST)
    final_sheet = char_dir / f"{character_name}_sheet.png"
    save_image(resized, final_sheet)
    steps.append("resize")

    # Generate SpriteFrames
    rel_path = f"sprites/{character_name}/{character_name}_sheet.png"
    frames_tres = generate_sprite_frames_tres(rel_path, cell_w, cell_h, rows, columns)
    frames_path = char_dir / f"{character_name}_frames.tres"
    frames_path.write_text(frames_tres, encoding="utf-8")
    steps.append("spriteframes")

    # Generate CharacterBody2D scene
    collision_w = int(cell_w * 0.7)
    collision_h = int(cell_h * 0.5)
    scene_tscn = generate_tscn(
        scene_name=character_name,
        node_type="CharacterBody2D",
        ext_resources=[
            {"type": "SpriteFrames", "path": f"sprites/{character_name}/{character_name}_frames.tres", "id": "frames"},
            {"type": "Texture2D", "path": f"sprites/{character_name}/{character_name}_sheet.png", "id": "tex"},
        ],
        child_nodes=[
            {"name": "AnimatedSprite2D", "type": "AnimatedSprite2D",
             "properties": {"sprite_frames": ExtResource("frames"), "centered": True}},
            {"name": "CollisionShape2D", "type": "CollisionShape2D",
             "properties": {"shape": SubResource("shape")}},
        ],
        sub_resources=[
            {"type": "RectangleShape2D", "id": "shape",
             "properties": {"size": Vector2(collision_w, collision_h)}},
        ],
    )
    scene_path = project_dir / "scenes" / f"{character_name}.tscn"
    scene_path.parent.mkdir(parents=True, exist_ok=True)
    scene_path.write_text(scene_tscn, encoding="utf-8")
    steps.append("scene")

    return {
        "character_name": character_name,
        "spritesheet_path": str(final_sheet),
        "spriteframes_path": str(frames_path),
        "scene_path": str(scene_path),
        "cell_size": {"width": cell_w, "height": cell_h},
        "collision_size": {"width": collision_w, "height": collision_h},
        "steps": steps,
    }


def handle_game_build_and_verify(args: dict) -> dict:
    """Full project build and verification."""
    project_path = args["project_path"]
    return validate_project(project_path)
