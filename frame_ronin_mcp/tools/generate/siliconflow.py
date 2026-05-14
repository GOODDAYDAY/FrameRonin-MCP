"""SiliconFlow (硅基流动) image generation backend. Needs SILICONFLOW_API_KEY."""
import os
import base64
import requests
from pathlib import Path


API_BASE = "https://api.siliconflow.cn/v1"


def generate(
    prompt: str,
    output_path: str | Path | None = None,
    api_key: str = "",
    model: str = "Qwen/Qwen-Image",
    negative_prompt: str = "",
    image_size: str = "1024x1024",
    batch_size: int = 1,
    num_inference_steps: int = 20,
    guidance_scale: float = 7.5,
) -> Path:
    api_key = api_key or os.environ.get("SILICONFLOW_API_KEY") or os.environ.get("SF_API_KEY")
    if not api_key:
        raise RuntimeError("Set SILICONFLOW_API_KEY. Get key: https://cloud.siliconflow.cn/account/ak")

    output_path = Path(output_path or "siliconflow_gen.png")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "model": model,
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "image_size": image_size,
        "batch_size": batch_size,
        "num_inference_steps": num_inference_steps,
        "guidance_scale": guidance_scale,
    }

    resp = requests.post(
        f"{API_BASE}/image/generations",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()

    images = data.get("images", [])
    if not images:
        raise RuntimeError(f"No images in response: {data}")

    img = images[0]
    url = img.get("url", "")
    b64 = img.get("b64_json", img.get("image", ""))

    if url:
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        output_path.write_bytes(r.content)
    elif b64:
        output_path.write_bytes(base64.b64decode(b64))
    else:
        raise RuntimeError(f"No url or b64 in image: {img}")

    print(f"[SiliconFlow] Saved: {output_path} ({output_path.stat().st_size:,} bytes)")
    return output_path
