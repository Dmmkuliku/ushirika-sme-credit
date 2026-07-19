"""Capture remaining admin / lender detail screenshots."""
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent / "screenshots"
BASE = "https://ushirika-sme-portal.vercel.app"


def shot(page, name, wait_ms=1500):
    page.wait_for_timeout(wait_ms)
    page.screenshot(path=str(OUT / f"{name}.png"), full_page=False)
    print(f"OK {name}")


def fill_login(page, login_id, pin):
    page.goto(f"{BASE}/#/login", wait_until="domcontentloaded", timeout=90000)
    page.wait_for_selector("#login_id, input[name='login_id'], input[type='text']", timeout=30000)
    page.wait_for_timeout(500)
    if page.locator("#login_id").count():
        page.fill("#login_id", login_id)
    else:
        page.locator("input[type='text']").first.fill(login_id)
    if page.locator("#pin").count():
        page.fill("#pin", pin)
    else:
        page.locator("input[type='password']").first.fill(pin)
    page.locator("#auth-submit, button[type='submit']").first.click(force=True)
    page.wait_for_timeout(5000)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=1.5,
        ).new_page()
        page.set_default_timeout(90000)

        fill_login(page, "EMP001", "1234")
        link = page.locator("a[href*='#/lender/sme/'], button:has-text('View'), a:has-text('View')").first
        if link.count():
            link.click(force=True)
            page.wait_for_timeout(2500)
            shot(page, "06_lender_sme_detail", 1500)
        else:
            shot(page, "06_lender_sme_detail", 1000)

        page.evaluate("() => { localStorage.clear(); sessionStorage.clear(); }")
        fill_login(page, "20031001121160000228", "1234")
        shot(page, "07_admin_accounts", 2500)
        page.goto(f"{BASE}/#/admin/create-lender", wait_until="domcontentloaded")
        shot(page, "08_admin_create", 2000)
        browser.close()
        print("DONE")


if __name__ == "__main__":
    main()
