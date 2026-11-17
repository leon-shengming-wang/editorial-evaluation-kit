# Optional integration smoke: install Playwright, fetch your authorized fixture, start server first.
from playwright.sync_api import sync_playwright
import json
import os
from pathlib import Path

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 1080})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(os.environ.get("SPEECHQA_URL", "http://127.0.0.1:8765"))
    page.screenshot(path="/tmp/speechqa-import.png", full_page=True)
    page.locator("input[type=file]").set_input_files(
        str(Path(__file__).resolve().parent / "fixtures" / "jfk.flac")
    )
    page.locator("select[name=model]").select_option("tiny.en")
    page.locator("textarea[name=reference]").fill(
        "And so my fellow Americans ask not what your country can do for you ask what you can do for your country"
    )
    page.get_by_role("button", name="Transcribe & analyze locally").click()
    page.wait_for_selector("#transcript .segment", timeout=180000)
    page.locator("#audio").evaluate("(a)=>a.play()")
    page.wait_for_timeout(1200)
    assert page.locator("#audio").evaluate("(a)=>a.currentTime") > 0.2
    page.locator("#audio").evaluate("(a)=>a.pause()")
    t = page.locator("#audio").evaluate("(a)=>a.currentTime")
    page.wait_for_timeout(300)
    assert abs(page.locator("#audio").evaluate("(a)=>a.currentTime") - t) < 0.05
    page.locator(".word").nth(8).click()
    page.wait_for_timeout(200)
    assert page.locator("#audio").evaluate("(a)=>a.currentTime") > 1
    assert page.locator(".word.active").count() >= 1
    page.locator("#speed").select_option("1.5")
    assert page.locator("#audio").evaluate("(a)=>a.playbackRate") == 1.5
    page.locator("details").first.locator("summary").click()
    page.locator("#edit-0").fill("My test correction, not the original.")
    with page.expect_download() as download:
        page.locator("#export").click()
    target = "/tmp/speechqa-browser-export.json"
    download.value.save_as(target)
    d = json.loads(Path(target).read_text())
    assert d["review"]["edits"]["0"] == "My test correction, not the original."
    assert d["segments"][0]["text"] != "My test correction, not the original."
    page.screenshot(path="/tmp/speechqa-report.png", full_page=True)
    page.set_viewport_size({"width": 390, "height": 844})
    page.screenshot(path="/tmp/speechqa-mobile.png", full_page=True)
    assert page.evaluate("document.documentElement.scrollWidth<=window.innerWidth")
    assert not errors, errors
    print(
        "PASS: actual upload/inference, playback, pause, seek/highlight, rate, correction export, mobile width; no JS errors"
    )
    browser.close()
