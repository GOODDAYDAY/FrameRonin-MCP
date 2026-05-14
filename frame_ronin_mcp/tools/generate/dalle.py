"""OpenAI DALL-E 3 image generation. Needs OPENAI_API_KEY."""
import os, time, urllib.request
from pathlib import Path


def generate(prompt: str, output_path: str | Path | None = None, api_key: str = "", size: str = "1024x1024") -> Path:
    from openai import OpenAI

    api_key = api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Set OPENAI_API_KEY. Get key: https://platform.openai.com/api-keys")

    output_path = Path(output_path or "dalle.png")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    client = OpenAI(api_key=api_key)
    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size=size,
        quality="standard",
        n=1,
    )

    url = response.data[0].url
    urllib.request.urlretrieve(url, str(output_path))
    print(f"[DALL-E] Saved: {output_path}")
    return output_path
