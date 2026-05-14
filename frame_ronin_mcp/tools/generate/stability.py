"""Stability AI image generation. Needs STABILITY_API_KEY."""
import os, requests
from pathlib import Path


def generate(prompt: str, output_path: str | Path | None = None, api_key: str = "") -> Path:
    api_key = api_key or os.environ.get("STABILITY_API_KEY")
    if not api_key:
        raise RuntimeError("Set STABILITY_API_KEY. Get key: https://platform.stability.ai")

    output_path = Path(output_path or "stability.png")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    resp = requests.post(
        "https://api.stability.ai/v2beta/stable-image/generate/core",
        headers={"authorization": f"Bearer {api_key}"},
        files={"none": ("", "")},
        data={"prompt": prompt, "output_format": "png"},
        timeout=120,
    )

    if resp.status_code == 200:
        output_path.write_bytes(resp.content)
        print(f"[Stability] Saved: {output_path}")
        return output_path
    raise RuntimeError(f"Stability API error {resp.status_code}: {resp.text[:300]}")
