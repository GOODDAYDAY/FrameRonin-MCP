"""
Godot 4.6 format tools — generate .tscn, .tres, project.godot files.
"""

import os
from pathlib import Path

from ..lib.godot_format import (
    generate_project_godot,
    generate_tscn,
    generate_sprite_frames_tres,
    generate_tileset_tres,
    Vector2, Rect2, Color, ExtResource, SubResource,
)
from ..lib.godot_runner import find_godot, validate_scene, validate_project
from ..lib.image_utils import load_image


def handle_godot_create_project(args: dict) -> dict:
    """Generate project.godot + directory tree for a new Godot 4.6 pixel art game."""
    project_name = args["project_name"]
    project_dir = Path(args["project_dir"])
    res_w = int(args.get("resolution_w", 480))
    res_h = int(args.get("resolution_h", 270))
    renderer = args.get("renderer", "gl_compatibility")

    if renderer not in ("gl_compatibility", "forward_plus", "mobile"):
        return {"error": f"Unknown renderer: {renderer}"}

    project_dir.mkdir(parents=True, exist_ok=True)

    # Directory tree
    dirs = ["scenes", "sprites", "tilesets", "scripts", "audio", "ui"]
    created_dirs = []
    for d in dirs:
        dp = project_dir / d
        dp.mkdir(parents=True, exist_ok=True)
        created_dirs.append(str(dp))

    # project.godot
    proj_content = generate_project_godot(project_name, res_w, res_h, renderer)
    (project_dir / "project.godot").write_text(proj_content, encoding="utf-8")

    # icon.svg placeholder
    icon_svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64">'
        '<rect width="64" height="64" fill="#2b2b2b"/>'
        '<rect x="16" y="20" width="32" height="24" rx="2" fill="#5b8c5a"/>'
        '<circle cx="24" cy="32" r="6" fill="#1a1a2e"/>'
        '<circle cx="40" cy="32" r="6" fill="#1a1a2e"/>'
        '<rect x="24" y="42" width="16" height="4" rx="1" fill="#3a6b3a"/>'
        '</svg>'
    )
    (project_dir / "icon.svg").write_text(icon_svg, encoding="utf-8")

    # main.tscn stub
    main_tscn = generate_tscn(
        scene_name="Main",
        node_type="Node2D",
        child_nodes=[
            {
                "name": "Camera",
                "type": "Camera2D",
                "properties": {
                    "enabled": True,
                    "zoom": Vector2(2, 2),
                    "anchor_mode": 1,  # DRAG_CENTER
                    "position_smoothing_enabled": True,
                },
            },
        ],
    )
    (project_dir / "scenes" / "main.tscn").write_text(main_tscn, encoding="utf-8")

    return {
        "project_dir": str(project_dir),
        "project_path": str(project_dir / "project.godot"),
        "scene_path": str(project_dir / "scenes" / "main.tscn"),
        "directories": created_dirs,
        "resolution": {"width": res_w, "height": res_h},
        "renderer": renderer,
    }


def handle_godot_create_scene(args: dict) -> dict:
    """Generate a .tscn scene file with specified node tree."""
    scene_name = args["scene_name"]
    output_dir = Path(args["output_dir"])
    node_type = args.get("node_type", "Node2D")
    child_nodes = args.get("child_nodes", [])
    ext_resources = args.get("ext_resources", [])
    sub_resources = args.get("sub_resources", [])

    output_dir.mkdir(parents=True, exist_ok=True)
    tscn = generate_tscn(scene_name, node_type, None, child_nodes, ext_resources, sub_resources)
    scene_path = output_dir / f"{scene_name}.tscn"
    scene_path.write_text(tscn, encoding="utf-8")

    return {
        "scene_path": str(scene_path),
        "scene_name": scene_name,
        "node_type": node_type,
        "node_count": 1 + len(child_nodes),
    }


def handle_godot_create_spriteframes(args: dict) -> dict:
    """Generate SpriteFrames .tres from a spritesheet."""
    spritesheet_path = Path(args["spritesheet_path"])
    output_path = Path(args["output_path"])
    cell_w = int(args["cell_width"])
    cell_h = int(args["cell_height"])
    rows = int(args["rows"])
    columns = int(args["columns"])
    animations = args.get("animation_defs", None)

    if not spritesheet_path.exists():
        return {"error": f"Spritesheet not found: {spritesheet_path}"}

    # Validate grid fits image
    img = load_image(spritesheet_path)
    if cell_w * columns > img.width or cell_h * rows > img.height:
        return {"error": f"Grid {columns}x{rows} ({cell_w*columns}x{cell_h*rows}) exceeds image {img.width}x{img.height}"}

    content = generate_sprite_frames_tres(str(spritesheet_path), cell_w, cell_h, rows, columns, animations)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")

    anim_names = [a["name"] for a in (animations or [])] if animations else []
    if not animations:
        for r in range(rows):
            d = ["down", "left", "right", "up"][r] if r < 4 else f"row{r}"
            anim_names.append(f"idle_{d}")

    return {
        "output_path": str(output_path),
        "spritesheet_path": str(spritesheet_path),
        "cell_size": {"width": cell_w, "height": cell_h},
        "grid": {"rows": rows, "columns": columns},
        "animations": anim_names,
    }


def handle_godot_create_tileset(args: dict) -> dict:
    """Generate TileSet .tres from a tilesheet."""
    tilesheet_path = Path(args["tilesheet_path"])
    output_path = Path(args["output_path"])
    tile_w = int(args["tile_width"])
    tile_h = int(args["tile_height"])
    columns = int(args["columns"])
    rows = int(args["rows"])
    collision_data = args.get("collision_data", None)

    if not tilesheet_path.exists():
        return {"error": f"Tilesheet not found: {tilesheet_path}"}

    img = load_image(tilesheet_path)
    if tile_w * columns > img.width or tile_h * rows > img.height:
        return {"error": f"Grid exceeds image dimensions"}

    content = generate_tileset_tres(str(tilesheet_path), tile_w, tile_h, columns, rows, collision_data)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")

    return {
        "output_path": str(output_path),
        "tilesheet_path": str(tilesheet_path),
        "tile_size": {"width": tile_w, "height": tile_h},
        "grid": {"rows": rows, "columns": columns},
        "tile_count": rows * columns,
    }


def handle_godot_export_character(args: dict) -> dict:
    """Export a complete Godot character: spritesheet → SpriteFrames.tres → CharacterBody2D.tscn."""
    spritesheet_path = Path(args["spritesheet_path"])
    character_name = args["character_name"]
    output_dir = Path(args["output_dir"])
    cell_w = args.get("cell_width")
    cell_h = args.get("cell_height")
    rows = int(args.get("rows", 4))
    columns = int(args.get("columns", 4))
    animations = args.get("animation_defs", None)

    if not spritesheet_path.exists():
        return {"error": f"Spritesheet not found: {spritesheet_path}"}

    # Auto-detect cell size
    img = load_image(spritesheet_path)
    if not cell_w:
        cell_w = img.width // columns
    if not cell_h:
        cell_h = img.height // rows
    cell_w, cell_h = int(cell_w), int(cell_h)

    char_dir = output_dir / character_name
    char_dir.mkdir(parents=True, exist_ok=True)

    # Copy spritesheet
    sheet_name = f"{character_name}_sheet.png"
    import shutil
    shutil.copy(spritesheet_path, char_dir / sheet_name)

    # Generate SpriteFrames .tres
    frames_content = generate_sprite_frames_tres(
        f"{character_name}/{sheet_name}", cell_w, cell_h, rows, columns, animations
    )
    frames_path = char_dir / f"{character_name}_frames.tres"
    frames_path.write_text(frames_content, encoding="utf-8")

    # Generate CharacterBody2D .tscn
    collision_w = cell_w * 0.7
    collision_h = cell_h * 0.5
    scene_content = generate_tscn(
        scene_name=character_name,
        node_type="CharacterBody2D",
        ext_resources=[
            {"type": "Texture2D", "path": f"{character_name}/{sheet_name}", "id": "1"},
        ],
        child_nodes=[
            {
                "name": "AnimatedSprite2D",
                "type": "AnimatedSprite2D",
                "properties": {
                    "sprite_frames": ExtResource("2"),
                    "centered": True,
                },
            },
            {
                "name": "CollisionShape2D",
                "type": "CollisionShape2D",
                "properties": {
                    "shape": SubResource("shape_1"),
                },
            },
            {
                "name": "Camera2D",
                "type": "Camera2D",
                "properties": {
                    "enabled": False,
                    "zoom": Vector2(2, 2),
                    "anchor_mode": 1,
                },
            },
        ],
        sub_resources=[
            {"type": "RectangleShape2D", "id": "shape_1",
             "properties": {"size": Vector2(int(collision_w), int(collision_h))}},
        ],
    )
    scene_path = char_dir / f"{character_name}.tscn"
    scene_path.write_text(scene_content, encoding="utf-8")

    # SpriteFrames needs separate ext_resource
    scene_text = scene_path.read_text(encoding="utf-8")
    scene_text = scene_text.replace(
        '[ext_resource type="Texture2D"',
        f'[ext_resource type="SpriteFrames" path="res://{character_name}/{character_name}_frames.tres" id="2"]\n[ext_resource type="Texture2D"',
        1,
    )
    scene_path.write_text(scene_text, encoding="utf-8")

    return {
        "character_name": character_name,
        "character_dir": str(char_dir),
        "spritesheet_path": str(char_dir / sheet_name),
        "spriteframes_path": str(frames_path),
        "scene_path": str(scene_path),
        "cell_size": {"width": cell_w, "height": cell_h},
        "collision_size": {"width": int(collision_w), "height": int(collision_h)},
    }


def handle_godot_validate(args: dict) -> dict:
    """Validate a Godot project or scene file."""
    project_path = args.get("project_path")
    scene_path = args.get("scene_path")

    result = {}

    if project_path:
        result["project_validation"] = validate_project(project_path)
    if scene_path:
        result["scene_validation"] = validate_scene(scene_path)
    if not project_path and not scene_path:
        return {"error": "Provide project_path or scene_path"}

    godot = find_godot()
    result["godot_available"] = godot is not None
    if godot:
        from ..lib.godot_runner import get_godot_version
        result["godot_version"] = get_godot_version(godot)

    return result
