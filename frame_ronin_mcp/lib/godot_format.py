"""
Godot 4.6 text-format generators — tscn, tres, project.godot.

All output is pure text. No Godot installation required to generate files.
"""

import secrets
import textwrap
from pathlib import Path


# ── Helpers ───────────────────────────────────────────────────────────────

def _fmt(v: float) -> str:
    """Format a number for Godot: integer if whole, else float."""
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        if v == int(v):
            return str(int(v))
        return f"{v:.1f}"
    return str(v)


def generate_uid() -> str:
    """Generate a Godot-compatible random uid: uid://<12-char token>."""
    tok = secrets.token_urlsafe(9)[:12].lower()
    return f"uid://{tok}"


# ── Godot value types ─────────────────────────────────────────────────────

def Vector2(x: float, y: float) -> dict:
    return {"_gd": "Vector2", "x": x, "y": y}


def Vector2i(x: int, y: int) -> dict:
    return {"_gd": "Vector2i", "x": x, "y": y}


def Rect2(x: float, y: float, w: float, h: float) -> dict:
    return {"_gd": "Rect2", "x": x, "y": y, "w": w, "h": h}


def Color(r: int, g: int, b: int, a: int = 255) -> dict:
    return {"_gd": "Color", "r": r, "g": g, "b": b, "a": a}


def NodePath(p: str) -> dict:
    return {"_gd": "NodePath", "path": p}


def ExtResource(rid: str) -> dict:
    return {"_gd": "ExtResource", "id": str(rid)}


def SubResource(rid: str) -> dict:
    return {"_gd": "SubResource", "id": str(rid)}


# ── Property serialization ─────────────────────────────────────────────────

def _serialize_value(v) -> str:
    """Serialize a single Python value to Godot text format."""
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        return _fmt(v)
    if isinstance(v, str):
        # Escape quotes and backslashes
        escaped = v.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    if isinstance(v, dict):
        gt = v.get("_gd")
        if gt == "Vector2":
            return f"Vector2({_fmt(v['x'])}, {_fmt(v['y'])})"
        if gt == "Vector2i":
            return f"Vector2i({int(v['x'])}, {int(v['y'])})"
        if gt == "Rect2":
            return f"Rect2({_fmt(v['x'])}, {_fmt(v['y'])}, {_fmt(v['w'])}, {_fmt(v['h'])})"
        if gt == "Color":
            return f"Color({v['r']}, {v['g']}, {v['b']}, {v['a']})"
        if gt == "NodePath":
            return f'^"{v["path"]}"'
        if gt == "ExtResource":
            return f'ExtResource("{v["id"]}")'
        if gt == "SubResource":
            return f'SubResource("{v["id"]}")'
        return _serialize_dict(v)
    if isinstance(v, (list, tuple)):
        items = ", ".join(_serialize_value(i) for i in v)
        return f"[{items}]"
    return str(v)


def _serialize_dict(d: dict) -> str:
    """Serialize a dict as a Godot dictionary literal."""
    parts = []
    for k, val in d.items():
        if k.startswith("_"):
            continue
        parts.append(f'"{k}": {_serialize_value(val)}')
    return "{" + ", ".join(parts) + "}"


def _serialize_props(props: dict) -> str:
    """Serialize a dict of property assignments, one per line."""
    lines = []
    for key, value in props.items():
        if value is None:
            continue
        if key.startswith("_"):
            continue
        lines.append(f"{key} = {_serialize_value(value)}")
    return "\n".join(lines)


# ── project.godot ──────────────────────────────────────────────────────────

# Common key mappings — USB HID physical_keycode values
_INPUT_EVENTS = {
    "move_left": [
        'Object(InputEventKey,"resource_local_to_scene":false,"device":-1,"physical_keycode":65)',
        'Object(InputEventKey,"resource_local_to_scene":false,"device":-1,"physical_keycode":4194319)',
    ],
    "move_right": [
        'Object(InputEventKey,"resource_local_to_scene":false,"device":-1,"physical_keycode":68)',
        'Object(InputEventKey,"resource_local_to_scene":false,"device":-1,"physical_keycode":4194321)',
    ],
    "move_up": [
        'Object(InputEventKey,"resource_local_to_scene":false,"device":-1,"physical_keycode":87)',
        'Object(InputEventKey,"resource_local_to_scene":false,"device":-1,"physical_keycode":4194320)',
    ],
    "move_down": [
        'Object(InputEventKey,"resource_local_to_scene":false,"device":-1,"physical_keycode":83)',
        'Object(InputEventKey,"resource_local_to_scene":false,"device":-1,"physical_keycode":4194322)',
    ],
    "attack": [
        'Object(InputEventKey,"resource_local_to_scene":false,"device":-1,"physical_keycode":32)',
        'Object(InputEventKey,"resource_local_to_scene":false,"device":-1,"physical_keycode":4194305)',
    ],
    "interact": [
        'Object(InputEventKey,"resource_local_to_scene":false,"device":-1,"physical_keycode":69)',
    ],
}


def generate_project_godot(
    project_name: str,
    resolution_w: int = 480,
    resolution_h: int = 270,
    renderer: str = "gl_compatibility",
) -> str:
    """Generate a complete project.godot file as a string."""
    renderer_title = {"gl_compatibility": "GL Compatibility", "forward_plus": "Forward+", "mobile": "Mobile"}[renderer]

    input_entries = []
    for action, events in _INPUT_EVENTS.items():
        ev_str = ", ".join(events)
        input_entries.append(f"""{action}={{
"deadzone": 0.5,
"events": [{ev_str}]
}}""")

    input_section = "\n".join(input_entries)

    return textwrap.dedent(f"""\
    ; Engine configuration file.
    ; Generated by FrameRonin-MCP

    [application]
    config/name="{project_name}"
    config/description=""
    config/features=PackedStringArray("4.6", "{renderer_title}")
    config/icon="res://icon.svg"

    [display]
    window/size/viewport_width={resolution_w}
    window/size/viewport_height={resolution_h}
    window/stretch/mode="canvas_items"
    window/stretch/scale_mode="integer"
    window/stretch/scale=1.0

    [rendering]
    renderer/rendering_method="{renderer}"
    textures/canvas_textures/default_texture_filter=0

    [input]
    {input_section}
    """)


# ── .tscn ──────────────────────────────────────────────────────────────────

def generate_tscn(
    scene_name: str,
    node_type: str = "Node2D",
    root_position: tuple | None = None,
    child_nodes: list[dict] | None = None,
    ext_resources: list[dict] | None = None,
    sub_resources: list[dict] | None = None,
) -> str:
    """Generate a Godot 4.x .tscn file (format=3)."""
    child_nodes = child_nodes or []
    ext_resources = ext_resources or []
    sub_resources = sub_resources or []

    # Count load steps
    load_steps = 1  # root node always counts
    if ext_resources:
        load_steps += len(ext_resources)
    if sub_resources:
        load_steps += len(sub_resources)
    # Count all child nodes recursively
    def count_nodes(nodes):
        c = 0
        for n in nodes:
            c += 1
            if n.get("children"):
                c += count_nodes(n["children"])
        return c
    load_steps += count_nodes(child_nodes)

    lines = []
    lines.append(f'[gd_scene load_steps={load_steps} format=3 uid="{generate_uid()}"]')
    lines.append("")

    # External resources
    for res in ext_resources:
        rtype = res.get("type", "Texture2D")
        rpath = res["path"]
        rid = res.get("id", str(ext_resources.index(res) + 1))
        lines.append(f'[ext_resource type="{rtype}" path="res://{rpath}" id="{rid}"]')
    if ext_resources:
        lines.append("")

    # Sub-resources
    for sub in sub_resources:
        stype = sub["type"]
        sid = sub.get("id", f"sub_{sub_resources.index(sub) + 1}")
        lines.append(f'[sub_resource type="{stype}" id="{sid}"]')
        if "properties" in sub:
            lines.append(_serialize_props(sub["properties"]))
        lines.append("")

    # Root node
    lines.append(f'[node name="{scene_name}" type="{node_type}"]')
    if root_position:
        lines.append(f"position = Vector2({_fmt(root_position[0])}, {_fmt(root_position[1])})")

    # Children
    _write_child_nodes(lines, child_nodes, parent_name=scene_name)

    return "\n".join(lines) + "\n"


def _write_child_nodes(lines: list[str], nodes: list[dict], parent_name: str = ""):
    """Recursively write node entries."""
    for node in nodes:
        name = node["name"]
        ntype = node["type"]
        parent_clause = f' parent="{parent_name}"' if parent_name else ""
        lines.append(f'[node name="{name}" type="{ntype}"{parent_clause}]')

        props = node.get("properties", {})
        if props:
            prop_str = _serialize_props(props)
            if prop_str:
                lines.append(prop_str)

        # Children of this node
        kids = node.get("children", [])
        child_parent = f"{parent_name}/{name}" if parent_name else name
        _write_child_nodes(lines, kids, child_parent)


# ── SpriteFrames .tres ─────────────────────────────────────────────────────

def generate_sprite_frames_tres(
    spritesheet_path: str,
    cell_width: int,
    cell_height: int,
    rows: int,
    columns: int,
    animations: list[dict] | None = None,
) -> str:
    """
    Generate a SpriteFrames .tres resource from a spritesheet.

    Each cell becomes an AtlasTexture sub-resource.
    animations: [{"name": "walk", "row": 0, "speed": 5.0, "loop": True}, ...]
    If None, auto-generates one idle animation per row.
    """
    uid = generate_uid()
    total = rows * columns

    lines = []
    lines.append(f'[gd_resource type="SpriteFrames" format=3 uid="{uid}"]')
    lines.append("")

    # ExtResource for the spritesheet
    lines.append(f'[ext_resource type="Texture2D" path="res://{spritesheet_path}" id="spritesheet"]')
    lines.append("")

    # AtlasTexture sub-resources for each cell
    for idx in range(total):
        row = idx // columns
        col = idx % columns
        x, y = col * cell_width, row * cell_height
        lines.append(f'[sub_resource type="AtlasTexture" id="atlas_{idx}"]')
        lines.append(f'atlas = ExtResource("spritesheet")')
        lines.append(f"region = Rect2({x}, {y}, {cell_width}, {cell_height})")
        lines.append(f"filter_clip = true")
        lines.append("")

    # Build animations
    if not animations:
        animations = []
        for row in range(rows):
            direction = ["down", "left", "right", "up"][row] if row < 4 else f"row{row}"
            animations.append({"name": f"idle_{direction}", "row": row, "speed": 5.0, "loop": True})

    # Resource section
    lines.append("[resource]")
    anim_entries = []
    for anim in animations:
        name = anim["name"]
        row = anim.get("row", 0)
        speed = anim.get("speed", 5.0)
        loop = anim.get("loop", True)

        frames_json = []
        for col in range(columns):
            idx = row * columns + col
            frames_json.append({
                "duration": 1.0,
                "texture": {"_gd": "SubResource", "id": f"atlas_{idx}"},
            })

        anim_json = {
            "frames": frames_json,
            "loop": loop,
            "name": f'&"{name}"',
            "speed": speed,
        }
        anim_entries.append(_serialize_dict(anim_json))

    lines.append(f"animations = [{', '.join(anim_entries)}]")
    return "\n".join(lines) + "\n"


# ── TileSet .tres ──────────────────────────────────────────────────────────

def generate_tileset_tres(
    tilesheet_path: str,
    tile_width: int,
    tile_height: int,
    columns: int,
    rows: int,
    collision_data: list[dict] | None = None,
) -> str:
    """
    Generate a TileSet .tres resource from a tilesheet.

    collision_data: [{"tile_id": 0, "rect": (x, y, w, h)}, ...]
    Rect is relative (0-1) within the tile.
    """
    uid = generate_uid()

    lines = []
    lines.append(f'[gd_resource type="TileSet" format=3 uid="{uid}"]')
    lines.append("")
    lines.append(f'[ext_resource type="Texture2D" path="res://{tilesheet_path}" id="tilesheet"]')
    lines.append("")

    # Single TileSetAtlasSource
    total = rows * columns
    source_id = "tileset_source_0"
    lines.append(f'[sub_resource type="TileSetAtlasSource" id="{source_id}"]')
    lines.append(f'texture = ExtResource("tilesheet")')
    lines.append(f"texture_region_size = Vector2i({tile_width}, {tile_height})")
    lines.append(f'"0:0/0" = 0')
    lines.append(f'"0:0/0/physics_layer_0/polygon_0/points" = PackedVector2Array()')

    # Per-tile entries
    for i in range(total):
        row = i // columns
        col = i % columns
        x, y = col * tile_width, row * tile_height
        lines.append(f'"{col}:{row}/0" = {i}')

    lines.append(f'"0:0/0" = 0')  # reset to first tile
    lines.append(f'"{columns-1}:{rows-1}/0" = {total-1}')
    lines.append("")

    lines.append("[resource]")
    lines.append(f'sources = [SubResource("{source_id}")]')
    return "\n".join(lines) + "\n"
