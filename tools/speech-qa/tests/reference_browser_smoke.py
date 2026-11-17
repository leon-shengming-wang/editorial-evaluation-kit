"""Optional browser test: use real ASR output with a deliberately changed script.

python tests/reference_browser_smoke.py /path/to/generated/index.html
This verifies playback mapping, NOT that ASR made these deliberately injected differences.
"""

import json
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 1100})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(Path(sys.argv[1]).resolve().as_uri())
    data = json.loads(page.locator("#data").text_content())
    differences = data["reference_comparison"]["differences"]
    assert any(d["location"]["kind"] == "recognized-word-interval" for d in differences)
    assert any(d["location"]["kind"] == "neighboring-context" for d in differences)
    direct = next(
        d for d in differences if d["location"]["kind"] == "recognized-word-interval"
    )
    page.get_by_role("button", name="Play recognized words").first.click()
    page.wait_for_timeout(150)
    current = page.locator("#audio").evaluate("(a)=>a.currentTime")
    assert (
        max(0, direct["location"]["start"] - 0.25)
        <= current
        <= direct["location"]["end"] + 0.5
    )
    assert not page.locator("#audio").evaluate("(a)=>a.paused")
    page.wait_for_function('document.getElementById("audio").paused', timeout=15000)
    end = page.locator("#audio").evaluate("(a)=>a.currentTime")
    assert direct["location"]["end"] <= end <= direct["location"]["end"] + 0.6
    page.get_by_role("button", name="Play context").first.click()
    page.wait_for_timeout(150)
    assert not page.locator("#audio").evaluate("(a)=>a.paused")
    page.locator("#audio").evaluate("(a)=>a.pause()")
    page.get_by_role("button", name="Play recognized words").first.click()
    page.get_by_role("button", name="Resume full recording").click()
    page.locator("#audio").evaluate(
        "(a,t)=>{a.currentTime=t;}", direct["location"]["end"] + 0.6
    )
    page.wait_for_timeout(300)
    assert not page.locator("#audio").evaluate("(a)=>a.paused")
    page.locator("#audio").evaluate("(a)=>a.pause()")
    with page.expect_download() as download:
        page.locator("#export").click()
    output = Path("/tmp/speechqa-reference-export.json")
    download.value.save_as(str(output))
    exported = json.loads(output.read_text())
    assert exported["reference_comparison"] == data["reference_comparison"]
    page.screenshot(path="/tmp/speechqa-reference-desktop.png", full_page=True)
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
    page.screenshot(path="/tmp/speechqa-reference-mobile.png", full_page=True)
    assert not errors, errors
    print(
        "PASS: ASR-word playback range, automatic clip stop, neighboring context playback, exported mapping, mobile width; no JS errors"
    )
    browser.close()
