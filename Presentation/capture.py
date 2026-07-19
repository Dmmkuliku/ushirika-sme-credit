"""Provision demos if needed; capture authenticated UI via init_script session."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)
BASE = "https://ushirika-sme-portal.vercel.app"
API = "https://ushirika-api.onrender.com/api"

ADMIN_ID = "20031001121160000228"
ADMIN_PIN = "1234"
SME_NIDA = "19900101123456789012"
LENDER_ID = "EMP001"
PIN = "1234"


def req(method: str, path: str, token: str | None = None, data: dict | None = None):
    body = None if data is None else json.dumps(data).encode()
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(f"{API}{path}", data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=120) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else None
    except HTTPError as e:
        err = e.read().decode(errors="replace")
        raise RuntimeError(f"{method} {path} -> {e.code}: {err}") from e


def login(login_id: str, pin: str) -> dict:
    return req("POST", "/auth/login", data={"login_id": login_id, "pin": pin})


def ensure_demos():
    admin = login(ADMIN_ID, ADMIN_PIN)
    token = admin["access_token"]
    accounts = req("GET", "/admin/accounts", token=token) or []
    by_login = {a.get("login_id"): a for a in accounts}
    print(f"Accounts: {len(accounts)}")

    if LENDER_ID not in by_login:
        req(
            "POST",
            "/admin/accounts/lender",
            token=token,
            data={
                "membership_number": LENDER_ID,
                "full_name": "James Mwangi",
                "gender": "Male",
                "organization": "CRDB",
                "work_email": "james.mwangi@crdb.co.tz",
                "phone": "+255712000001",
                "pin": PIN,
            },
        )
        print("Created lender")

    if SME_NIDA not in by_login:
        req(
            "POST",
            "/admin/accounts/sme",
            token=token,
            data={
                "nida": SME_NIDA,
                "phone": "+255712345001",
                "full_name": "Grace Mwangi",
                "email": "grace@demo.local",
                "location": "Dar es Salaam, Kinondoni",
                "business_type": "Entrepreneur",
                "gender": "Female",
                "nationality": "Tanzanian",
                "date_of_birth": "1990-01-01",
                "pin": PIN,
            },
        )
        print("Created SME")

    sme = login(SME_NIDA, PIN)
    sme_token = sme["access_token"]
    try:
        existing = req("GET", "/transactions", token=sme_token) or []
    except Exception:
        existing = []
    if isinstance(existing, dict):
        existing = existing.get("items") or existing.get("transactions") or []
    if len(existing) < 5:
        now = datetime.now(timezone.utc)
        names = [
            "Kilimanjaro Traders",
            "Dar Fresh Produce",
            "Mwanza Logistics",
            "Arusha Agro",
            "Coastal Retail",
            "Lake Zone Exporters",
        ]
        for i, name in enumerate(names):
            tx_date = now - timedelta(days=12 * (i + 1))
            due = tx_date + timedelta(days=14)
            paid = due - timedelta(days=1)
            try:
                req(
                    "POST",
                    "/transactions",
                    token=sme_token,
                    data={
                        "transaction_ref": f"TXN-DEMO-{i+1:03d}",
                        "counterparty_name": name,
                        "counterparty_type": "buyer",
                        "order_type": "goods",
                        "amount_tzs": 850000 + i * 125000,
                        "currency": "TZS",
                        "payment_status": "paid",
                        "due_date": due.isoformat(),
                        "paid_date": paid.isoformat(),
                        "days_delayed": 0,
                        "compliance_flag": True,
                        "default_flag": False,
                        "completion_rate": 1.0,
                        "notes": "Presentation seed",
                        "transaction_date": tx_date.isoformat(),
                    },
                )
            except Exception as e:
                print(f"tx skip: {e}")
        print("Seeded transactions")


def shot(page, name, wait_ms=1800):
    page.wait_for_timeout(wait_ms)
    page.screenshot(path=str(OUT / f"{name}.png"), full_page=False)
    print(f"OK {name}  {page.evaluate('() => location.hash')}")


def open_as(context, payload: dict, hash_path: str):
    """New page with session baked in before app JS runs."""
    token = payload["access_token"]
    user = payload["user"]
    script = f"""
        sessionStorage.setItem('ushirika_token', {json.dumps(token)});
        sessionStorage.setItem('ushirika_user', {json.dumps(json.dumps(user))}.replace(/^"|"$/g,'') ? null : null);
    """
    # Safer: pass via JSON.stringify in JS
    init = (
        "(() => {"
        f"sessionStorage.setItem('ushirika_token', {json.dumps(token)});"
        f"sessionStorage.setItem('ushirika_user', {json.dumps(json.dumps(user))});"
        "})();"
    )
    context.clear_cookies()
    # Remove previous init scripts by using a fresh context ideally;
    # Playwright can't remove init scripts, so we use a new context each time.
    page = context.new_page()
    page.add_init_script(init)
    page.goto(f"{BASE}/{hash_path}", wait_until="networkidle", timeout=120000)
    page.wait_for_timeout(2000)
    return page


def capture():
    ensure_demos()
    sme = login(SME_NIDA, PIN)
    lender = login(LENDER_ID, PIN)
    admin = login(ADMIN_ID, ADMIN_PIN)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # Login (anonymous)
        ctx0 = browser.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=1.5)
        p0 = ctx0.new_page()
        p0.goto(f"{BASE}/#/login", wait_until="networkidle", timeout=120000)
        shot(p0, "01_login")
        ctx0.close()

        def authed_context(payload):
            ctx = browser.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=1.5)
            token = payload["access_token"]
            user = payload["user"]
            ctx.add_init_script(
                f"sessionStorage.setItem('ushirika_token', {json.dumps(token)});"
                f"sessionStorage.setItem('ushirika_user', {json.dumps(json.dumps(user))});"
            )
            return ctx

        # SME
        ctx = authed_context(sme)
        page = ctx.new_page()
        page.goto(f"{BASE}/#/sme", wait_until="networkidle", timeout=120000)
        shot(page, "02_sme_dashboard", 2500)
        page.goto(f"{BASE}/#/sme/transactions", wait_until="networkidle")
        shot(page, "03_sme_transactions", 2200)
        page.goto(f"{BASE}/#/sme/upload", wait_until="networkidle")
        shot(page, "04_sme_upload", 1800)
        ctx.close()

        # Lender
        ctx = authed_context(lender)
        page = ctx.new_page()
        page.goto(f"{BASE}/#/lender", wait_until="networkidle", timeout=120000)
        shot(page, "05_lender_portfolio", 2500)
        link = page.locator("a[href*='#/lender/sme/']").first
        if link.count():
            href = link.get_attribute("href") or "#/lender"
            page.goto(f"{BASE}/{href}", wait_until="networkidle")
            page.wait_for_timeout(2000)
        shot(page, "06_lender_sme_detail", 2000)
        ctx.close()

        # Admin
        ctx = authed_context(admin)
        page = ctx.new_page()
        page.goto(f"{BASE}/#/admin", wait_until="networkidle", timeout=120000)
        shot(page, "07_admin_accounts", 2500)
        page.goto(f"{BASE}/#/admin/create-lender", wait_until="networkidle")
        shot(page, "08_admin_create", 1800)
        ctx.close()

        browser.close()
        print("DONE")


if __name__ == "__main__":
    capture()
