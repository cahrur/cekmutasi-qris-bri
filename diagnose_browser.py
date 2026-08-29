#!/usr/bin/env python3
"""
Diagnose why BRI Merchant's login page fails to render on this machine.

BRI Merchant sits behind the Imperva/Incapsula WAF. When the WAF dislikes the
browser, the HTML document still loads (title "BRImerchant") but every
/_nuxt/*.js asset is refused, so the Nuxt SPA never renders and no login field
ever appears.

This script tries several browser configurations and reports which ones the WAF
lets through. Run it on the machine where the scraper fails:

    python diagnose_browser.py
"""
import asyncio
import os
import sys

URL = "https://brimerchant.bri.co.id/auth/login"
UA_LINUX = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
UA_WIN = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

PROJECT_ARGS = [
    '--no-sandbox', '--disable-blink-features=AutomationControlled',
    '--disable-dev-shm-usage', '--disable-web-security',
    '--disable-features=VizDisplayCompositor', '--memory-pressure-off',
    '--max_old_space_size=256', '--no-zygote', '--no-first-run',
    '--disable-background-timer-throttling', '--disable-renderer-backgrounding',
    '--disable-backgrounding-occluded-windows', '--aggressive-cache-discard',
    '--disable-extensions', '--disable-plugins', '--disable-background-networking',
]
MINIMAL_ARGS = ['--no-sandbox', '--disable-dev-shm-usage']

from playwright.async_api import async_playwright


async def attempt(label, *, headless=True, channel="chromium", args=None, ua=UA_LINUX):
    line = f"{label:<46s}"
    try:
        async with async_playwright() as p:
            launch = {"headless": headless}
            if channel:
                launch["channel"] = channel
            if args is not None:
                launch["args"] = args
            browser = await p.chromium.launch(**launch)

            ctx_opts = {"timezone_id": "Asia/Jakarta", "locale": "id-ID",
                        "viewport": {"width": 1920, "height": 1080}}
            if ua:
                ctx_opts["user_agent"] = ua
            ctx = await browser.new_context(**ctx_opts)
            page = await ctx.new_page()

            asset_problems = []

            def on_response(r):
                if '/_nuxt/' in r.url and r.status >= 400:
                    asset_problems.append(f"{r.status}")

            page.on("response", on_response)
            page.on("requestfailed",
                    lambda r: asset_problems.append("failed") if '/_nuxt/' in r.url else None)

            resp = await page.goto(URL, wait_until="domcontentloaded", timeout=60000)
            doc_status = resp.status if resp else "?"

            try:
                await page.locator('input[type="tel"]').first.wait_for(state="visible", timeout=20000)
                ok = True
            except Exception:
                ok = False

            inputs = await page.evaluate("() => document.querySelectorAll('input').length")
            real_ua = await page.evaluate("() => navigator.userAgent")
            await browser.close()

            verdict = "LOLOS" if ok else "DIBLOKIR"
            print(f"{line} {verdict:<9s} doc={doc_status} inputs={inputs} "
                  f"aset_nuxt_gagal={len(asset_problems)}")
            if not ok and 'Headless' in real_ua:
                print(f"{'':<46s}   catatan: navigator.userAgent masih '{real_ua[:60]}...'")
            return ok
    except Exception as exc:
        print(f"{line} ERROR     {type(exc).__name__}: {str(exc)[:90]}")
        return False


async def main():
    print("=" * 96)
    print("DIAGNOSA BROWSER - BRI Merchant / Incapsula")
    print("=" * 96)
    try:
        from importlib.metadata import version
        print("playwright  :", version("playwright"))
    except Exception:
        pass
    print("platform    :", sys.platform)
    print("DISPLAY     :", os.environ.get("DISPLAY") or "(kosong - tidak ada X server)")
    async with async_playwright() as p:
        print("chromium    :", p.chromium.executable_path)
    print("-" * 96)

    results = {}
    results['A'] = await attempt("A. channel=chromium + args project (sekarang)",
                                 channel="chromium", args=PROJECT_ARGS)
    results['B'] = await attempt("B. channel=chromium + args minimal",
                                 channel="chromium", args=MINIMAL_ARGS)
    results['C'] = await attempt("C. channel=chromium + args default",
                                 channel="chromium", args=None)
    results['D'] = await attempt("D. bundled (tanpa channel) + args minimal",
                                 channel=None, args=MINIMAL_ARGS)
    results['E'] = await attempt("E. channel=chromium + UA Windows",
                                 channel="chromium", args=MINIMAL_ARGS, ua=UA_WIN)

    if os.environ.get("DISPLAY"):
        results['F'] = await attempt("F. headed (Xvfb) + args minimal",
                                     headless=False, channel="chromium", args=MINIMAL_ARGS)
    else:
        print(f"{'F. headed (Xvfb) + args minimal':<46s} DILEWATI  (jalankan lagi via: xvfb-run -a python diagnose_browser.py)")

    print("-" * 96)
    if any(results.values()):
        winners = [k for k, v in results.items() if v]
        print(f"HASIL: konfigurasi {', '.join(winners)} LOLOS. Pakai konfigurasi itu.")
    else:
        print("HASIL: semua konfigurasi headless diblokir.")
        print("       Kemungkinan IP server ini di-flag oleh WAF, atau butuh mode headed.")
        print("       Langkah berikutnya: sudo apt install -y xvfb")
        print("                           xvfb-run -a python diagnose_browser.py")
    print("=" * 96)


if __name__ == "__main__":
    asyncio.run(main())
