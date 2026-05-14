"""
Godot CLI wrapper — find, run headless, validate.

Works offline (file-structure validation) even without Godot installed.
"""

import os
import shutil
import subprocess
from pathlib import Path


def find_godot() -> str | None:
    """Find the godot executable. Returns path or None."""
    # Try PATH first
    exe = shutil.which("godot") or shutil.which("godot.exe") or shutil.which("Godot")
    if exe:
        return exe

    # Common install locations
    candidates = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Godot" / "godot.exe",
        Path(os.environ.get("ProgramFiles", "")) / "Godot" / "godot.exe",
        Path("/Applications/Godot.app/Contents/MacOS/Godot"),
        Path("/usr/bin/godot"),
        Path("/usr/local/bin/godot"),
    ]
    for c in candidates:
        if c.exists():
            return str(c)

    return None


def get_godot_version(godot_path: str | None = None) -> str | None:
    """Get godot version string. Returns None if not found."""
    godot = godot_path or find_godot()
    if not godot:
        return None
    try:
        r = subprocess.run([godot, "--version"], capture_output=True, text=True, timeout=15)
        if r.returncode == 0:
            return r.stdout.strip().split("\n")[0]
    except Exception:
        pass
    return None


def run_headless(project_path: str, check_only: bool = True) -> dict:
    """
    Run godot --headless. If check_only, also pass --check-only.

    Returns: {"exit_code": int, "stdout": str, "stderr": str,
              "errors": [...], "warnings": [...]}
    """
    godot = find_godot()
    if not godot:
        return {"error": "godot executable not found on PATH", "exit_code": -1}

    cmd = [godot, "--headless", "--path", str(project_path)]
    if check_only:
        cmd.append("--check-only")

    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        errors, warnings = [], []
        for line in r.stderr.split("\n"):
            low = line.lower()
            if "error" in low or " err " in low or low.startswith("err"):
                errors.append(line.strip())
            elif "warn" in low:
                warnings.append(line.strip())
        return {
            "exit_code": r.returncode,
            "stdout": r.stdout,
            "stderr": r.stderr,
            "errors": errors,
            "warnings": warnings,
        }
    except subprocess.TimeoutExpired:
        return {"error": "godot timed out after 120s", "exit_code": -2}
    except OSError as e:
        return {"error": f"Failed to run godot: {e}", "exit_code": -3}


def validate_scene(scene_path: str) -> dict:
    """Offline validation of a single .tscn file."""
    scene_path = Path(scene_path)
    if not scene_path.exists():
        return {"valid": False, "errors": [f"File not found: {scene_path}"]}

    errors = []
    nodes = 0
    ext_resources = 0
    fmt = 0
    has_header = False
    has_root = False

    try:
        for line in scene_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("[gd_scene"):
                has_header = True
                if "format=3" in line:
                    fmt = 3
                elif "format=2" in line:
                    fmt = 2
            if line.startswith("[node "):
                nodes += 1
                if not has_root and 'parent=' not in line:
                    has_root = True
            if line.startswith("[ext_resource "):
                ext_resources += 1
    except Exception as e:
        errors.append(f"Failed to read file: {e}")

    if not has_header:
        errors.append("Missing [gd_scene] header")
    if not has_root:
        errors.append("No root node found")
    if fmt == 0:
        errors.append("Could not determine format version")

    return {
        "valid": len(errors) == 0,
        "format": fmt,
        "node_count": nodes,
        "ext_resources": ext_resources,
        "errors": errors,
    }


def validate_project(project_path: str) -> dict:
    """
    Validate a complete Godot project directory.
    Does offline file validation + optional Godot CLI check.
    """
    project_path = Path(project_path)
    if not project_path.exists():
        return {"error": f"Project path not found: {project_path}"}

    # Find project.godot
    proj_file = project_path / "project.godot"
    if not proj_file.exists():
        return {"error": f"No project.godot found in {project_path}"}

    errors = []
    scenes = []
    resources = []

    # Find all .tscn and .tres files
    for ext in ["*.tscn", "*.tres"]:
        for f in project_path.rglob(ext):
            if ext == "*.tscn":
                r = validate_scene(str(f))
                scenes.append({"path": str(f), **r})
            else:
                resources.append(str(f))

    # Check for broken ext_resource references
    broken_refs = []
    for scene in scenes:
        if scene.get("ext_resources", 0) > 0:
            try:
                content = Path(scene["path"]).read_text(encoding="utf-8")
                for line in content.splitlines():
                    if 'path="res://' in line:
                        ref_path = line.split('path="res://')[1].split('"')[0]
                        full_path = project_path / ref_path
                        if not full_path.exists():
                            broken_refs.append({"file": scene["path"], "missing": ref_path})
            except Exception:
                pass

    result = {
        "has_project_godot": True,
        "project_path": str(project_path),
        "total_scenes": len(scenes),
        "total_resources": len(resources),
        "scenes": scenes,
        "broken_references": broken_refs,
        "errors": errors,
    }

    # Try Godot CLI
    godot_ver = get_godot_version()
    if godot_ver:
        cli = run_headless(str(project_path), check_only=True)
        result["godot_cli"] = cli
        result["godot_version"] = godot_ver
    else:
        result["godot_cli"] = None
        result["godot_version"] = None
        result["godot_warning"] = "godot CLI not found on PATH, engine-level validation skipped"

    return result
