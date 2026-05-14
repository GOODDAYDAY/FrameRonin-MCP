"""
Gemini image generation via Playwright (free web app, gemini.google.com).

Uses persistent browser context — login once, reuse forever.
Session saved to ~/.frame-ronin-browser/.
"""

import os
import time
import base64
import asyncio
from pathlib import Path


def _browser_dir() -> Path:
    d = Path(os.environ.get("FRAMERONIN_BROWSER_DIR", Path.home() / ".frame-ronin-browser"))
    d.mkdir(parents=True, exist_ok=True)
    return d


async def _generate_async(
    prompt: str,
    output_path: Path,
    headless: bool = False,
    timeout_sec: int = 180,
) -> Path:
    from playwright.async_api import async_playwright

    udd = _browser_dir()

    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=str(udd),
            headless=headless,
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()

        await page.goto("https://gemini.google.com/app", wait_until="domcontentloaded", timeout=30_000)

        # Handle login
        if "accounts.google.com" in page.url:
            if headless:
                # Try direct navigation with cookies
                await page.goto("https://gemini.google.com/app", wait_until="domcontentloaded", timeout=30_000)
                if "accounts.google.com" in page.url:
                    raise RuntimeError(
                        "Login required. Run once with headless=False to authenticate."
                    )
            print("[Gemini] Login required — please log in to Google in the browser window...")
            try:
                await page.wait_for_url("https://gemini.google.com/**", timeout=300_000)
                print("[Gemini] Login OK, session saved.")
            except Exception:
                raise RuntimeError("Login timed out (5 min)")

        await asyncio.sleep(2)

        # Type and submit
        textbox = page.get_by_role("textbox").first
        await textbox.wait_for(state="visible", timeout=15_000)
        await textbox.fill(prompt)
        await textbox.press("Enter")
        print(f"[Gemini] Prompt sent: {prompt[:100]}...")

        # Wait for image
        start = time.time()
        while time.time() - start < timeout_sec:
            await asyncio.sleep(2)

            # Check for download button (new images)
            try:
                dl = page.locator('[data-test-id="download-generated-image-button"]').last
                if await dl.is_visible():
                    async with page.expect_download(timeout=30_000) as dl_info:
                        await dl.click()
                    download = await dl_info.value
                    await download.save_as(str(output_path))
                    print(f"[Gemini] Downloaded: {output_path}")
                    await ctx.close()
                    return output_path
            except Exception:
                pass

            # Check for blob image (edited/regenerated images)
            try:
                img_data = await page.evaluate("""async () => {
                    const imgs = [...document.querySelectorAll('img')].filter(i => i.src.startsWith('blob:'));
                    if (!imgs.length) return null;
                    const best = imgs.reduce((a, b) => b.naturalWidth > a.naturalWidth ? b : a);
                    const c = document.createElement('canvas');
                    c.width = best.naturalWidth; c.height = best.naturalHeight;
                    c.getContext('2d').drawImage(best, 0, 0);
                    return c.toDataURL('image/png');
                }""")
                if img_data:
                    _, b64 = img_data.split(",", 1)
                    output_path.write_bytes(base64.b64decode(b64))
                    print(f"[Gemini] Extracted: {output_path}")
                    await ctx.close()
                    return output_path
            except Exception:
                pass

            # Check for errors
            body = await page.evaluate("() => document.body.innerText")
            if "could not" in body.lower() and "generate" in body.lower():
                raise RuntimeError(f"Gemini refused: {body[body.lower().find('could not'):][:200]}")

        raise TimeoutError(f"Generation timed out ({timeout_sec}s)")


def generate(
    prompt: str,
    output_path: str | Path | None = None,
    headless: bool = False,
) -> Path:
    """Generate an image via Gemini web app. Synchronous."""
    output_path = Path(output_path or "gemini_generated.png")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    return asyncio.run(_generate_async(prompt, output_path, headless))
