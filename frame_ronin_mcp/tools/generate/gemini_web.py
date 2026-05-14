"""Gemini free web app (gemini.google.com) via Playwright. No API key needed."""
import os, time, base64, asyncio
from pathlib import Path

BROWSER_DIR = Path(os.environ.get("FRAMERONIN_BROWSER_DIR", Path.home() / ".frame-ronin-browser"))


async def _run(prompt: str, output_path: Path, headless: bool, timeout: int) -> Path:
    from playwright.async_api import async_playwright
    BROWSER_DIR.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(str(BROWSER_DIR), headless=headless)
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        await page.goto("https://gemini.google.com/app", wait_until="domcontentloaded", timeout=30000)

        if "accounts.google.com" in page.url:
            if headless:
                raise RuntimeError("Login required. Run with headless=False first.")
            print("[Gemini-Web] Login required — please log in via the browser window...")
            await page.wait_for_url("https://gemini.google.com/**", timeout=300_000)
            print("[Gemini-Web] Login saved.")

        await asyncio.sleep(2)
        tb = page.get_by_role("textbox").first
        await tb.wait_for(state="visible", timeout=15000)
        await tb.fill(prompt)
        await tb.press("Enter")
        print(f"[Gemini-Web] Generating: {prompt[:80]}...")

        start = time.time()
        while time.time() - start < timeout:
            await asyncio.sleep(2)
            try:
                dl = page.locator('[data-test-id="download-generated-image-button"]').last
                if await dl.is_visible():
                    async with page.expect_download(timeout=30000) as di:
                        await dl.click()
                    await (await di.value).save_as(str(output_path))
                    await ctx.close()
                    return output_path
            except Exception:
                pass
            try:
                b64 = await page.evaluate("""async () => {
                    const imgs=[...document.querySelectorAll('img')].filter(i=>i.src.startsWith('blob:'));
                    if(!imgs.length)return null;
                    const c=document.createElement('canvas');
                    c.width=imgs[0].naturalWidth;c.height=imgs[0].naturalHeight;
                    c.getContext('2d').drawImage(imgs[0],0,0);
                    return c.toDataURL('image/png');
                }""")
                if b64:
                    output_path.write_bytes(base64.b64decode(b64.split(",", 1)[1]))
                    await ctx.close()
                    return output_path
            except Exception:
                pass
        raise TimeoutError(f"Gemini generation timed out ({timeout}s)")


def generate(prompt: str, output_path: str | Path | None = None, headless: bool = False, timeout: int = 180) -> Path:
    output_path = Path(output_path or "gemini_web.png")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    return asyncio.run(_run(prompt, output_path, headless, timeout))
