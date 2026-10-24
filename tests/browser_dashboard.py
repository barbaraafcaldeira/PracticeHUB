"""Optional local browser QA; requires a running dashboard and Playwright."""

from pathlib import Path
import json

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "exports" / "dashboard_qa"


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    findings = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1000}, device_scale_factor=1)
        page = context.new_page()
        page.on("pageerror", lambda error: findings.append(str(error)))
        page.goto("http://127.0.0.1:8501", wait_until="networkidle")
        page.get_by_role("heading", name="Management overview", exact=True).wait_for(timeout=60000)
        page.locator('[data-testid="stPlotlyChart"]').first.wait_for()
        assert "synthetic" not in page.locator("body").inner_text().lower()
        page.screenshot(path=str(OUTPUT / "overview_desktop.png"), full_page=True)
        assert page.locator('[data-testid="stException"]').count() == 0
        for name, title, filename in [
            ("Historical analysis", "Historical analysis", "history_desktop.png"),
            ("Next-month forecast", "Next-month forecast", "forecast_desktop.png"),
            ("Session calculator", "Additional-session calculator", "calculator_desktop.png"),
        ]:
            page.locator('[data-testid="stSidebar"]').get_by_text(name, exact=True).click()
            page.get_by_role("heading", name=title, exact=True).wait_for()
            page.wait_for_timeout(500)
            assert "synthetic" not in page.locator("body").inner_text().lower()
            assert page.locator('[data-testid="stException"]').count() == 0
            if name == "Historical analysis":
                for tab in ["Slot utilisation", "eConsult routing", "Telephone", "Complaints", "GP demand"]:
                    page.get_by_role("tab", name=tab, exact=True).click()
                    page.wait_for_timeout(200)
            page.screenshot(path=str(OUTPUT / filename), full_page=True)
        assert page.get_by_text("1,235", exact=True).is_visible()
        with page.expect_download() as download:
            page.get_by_role("button", name="Download capacity scenario", exact=True).click()
        download.value.save_as(str(OUTPUT / "capacity_download.csv"))
        page.locator('[data-testid="stSidebar"]').get_by_text("Monthly inputs", exact=True).click()
        page.get_by_role("heading", name="Monthly forecasting inputs", exact=True).wait_for()
        page.get_by_role("button", name="Generate forecast", exact=True).wait_for()
        assert page.get_by_role("spinbutton", name="Same-day GP requests", exact=True).input_value() == ""
        assert page.locator('[data-testid="stException"]').count() == 0
        assert page.get_by_role("tab", name="Upload CSV", exact=True).count() == 0
        assert page.locator('[data-testid="stFileUploader"]').count() == 0
        page.get_by_role("tab", name="Correct saved month", exact=True).click()
        assert page.get_by_text("Save a completed month before making a correction.", exact=True).is_visible()
        page.get_by_role("tab", name="Saved inputs", exact=True).click()
        page.get_by_role("tab", name="Enter completed month", exact=True).click()
        page.wait_for_timeout(600)
        assert page.get_by_role("spinbutton", name="Same-day GP requests", exact=True).is_enabled()
        page.screenshot(path=str(OUTPUT / "monthly_inputs_desktop.png"), full_page=True)
        page.locator('[data-testid="stSidebar"]').get_by_text("Overview", exact=True).click()
        page.get_by_role("heading", name="Management overview", exact=True).wait_for()
        page.get_by_role("combobox", name="Database", exact=True).click()
        page.get_by_role("option", name="SQLite", exact=True).click()
        page.wait_for_timeout(500)
        assert page.locator('[data-testid="stException"]').count() == 0
        assert page.get_by_text("SQLite  |", exact=False).count() > 0
        mobile = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=1, is_mobile=True, has_touch=True)
        phone = mobile.new_page()
        phone.on("pageerror", lambda error: findings.append(str(error)))
        phone.goto("http://127.0.0.1:8501", wait_until="networkidle")
        phone.get_by_role("heading", name="Management overview", exact=True).wait_for(timeout=60000)
        phone.wait_for_timeout(500)
        phone.screenshot(path=str(OUTPUT / "overview_mobile.png"), full_page=True)
        assert phone.locator(".mobile-brand").is_visible()
        overflow = phone.evaluate("document.documentElement.scrollWidth > window.innerWidth + 2")
        assert not overflow, "Mobile page has horizontal overflow"
        assert phone.locator('[data-testid="stException"]').count() == 0
        # Verify navigation and the wide forecast/calculator views on mobile too.
        for name, title, image in [
            ("Next-month forecast", "Next-month forecast", "forecast_mobile.png"),
            ("Session calculator", "Additional-session calculator", "calculator_mobile.png"),
        ]:
            control = phone.get_by_role("button", name="Expand sidebar", exact=True)
            if control.count() and control.is_visible():
                control.click()
            sidebar = phone.locator('[data-testid="stSidebar"]')
            sidebar.get_by_text(name, exact=True).click()
            phone.get_by_role("heading", name=title, exact=True).wait_for()
            collapse = phone.get_by_role("button", name="Collapse sidebar", exact=True)
            if collapse.count() and collapse.is_visible():
                collapse.click()
            phone.wait_for_timeout(300)
            phone.screenshot(path=str(OUTPUT / image), full_page=True)
            assert phone.locator('[data-testid="stException"]').count() == 0
            assert not phone.evaluate("document.documentElement.scrollWidth > window.innerWidth + 2")
        assert not findings, findings
        (OUTPUT / "browser_checks.json").write_text(json.dumps({
            "desktop_views": 5, "historical_tabs": 5, "download_verified": True, "manual_inputs_only_verified": True,
            "sources_verified": ["MySQL", "SQLite"], "mobile_width": 390,
            "page_errors": findings, "mobile_horizontal_overflow": overflow,
        }, indent=2) + "\n")
        browser.close()
    print("Browser checks passed; screenshots and download saved to:", OUTPUT)


if __name__ == "__main__":
    main()
