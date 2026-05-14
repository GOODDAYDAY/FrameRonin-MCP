"""Gemini API (paid tier). Needs GOOGLE_API_KEY with billing enabled."""
import os
from pathlib import Path


def generate(prompt: str, output_path: str | Path | None = None, api_key: str = "", model: str = "gemini-2.5-flash-image") -> Path:
    from google import genai

    api_key = api_key or os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Set GOOGLE_API_KEY. Get key: https://aistudio.google.com/apikey")

    output_path = Path(output_path or "gemini_api.png")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=genai.types.GenerateContentConfig(response_modalities=["TEXT", "IMAGE"]),
    )

    for part in response.candidates[0].content.parts:
        if part.inline_data and "image" in (part.inline_data.mime_type or ""):
            output_path.write_bytes(part.inline_data.data)
            print(f"[Gemini-API] Saved: {output_path}")
            return output_path
        if part.text:
            print(f"[Gemini-API] Text: {part.text[:120]}...")

    raise RuntimeError("No image in Gemini API response")
