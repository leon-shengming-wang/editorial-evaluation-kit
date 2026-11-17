"""Optional real browser test. Start local server first; live discovery is opt-in here."""

from playwright.sync_api import sync_playwright, expect
import json, os, re
from pathlib import Path

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 1100})
    errors = []
    requests = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("request", lambda r: requests.append(r.url))
    page.goto(os.environ.get("CLAIMCHECK_URL", "http://127.0.0.1:8771"))
    page.locator("#example").click()
    expect(page.locator("#response")).to_have_value(re.compile("NASA"))
    page.locator("#analyze").click()
    page.wait_for_selector(".claim")
    assert page.locator(".claim").count() == 5
    assert not any("/discover" in u for u in requests)
    assert "1959" in page.locator(".claim").first.inner_text()
    assert "not proof of contradiction" in page.locator(".claim").first.inner_text()
    page.screenshot(path="/tmp/claim-evidence-desktop.png", full_page=True)
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
    page.screenshot(path="/tmp/claim-evidence-mobile.png", full_page=True)
    page.set_viewport_size({"width": 1440, "height": 1100})
    # Review gate: no final conclusion without rationale and related evidence.
    page.get_by_label("Conclusion claim-001", exact=True).select_option("contradicted")
    dialogs = []
    page.on("dialog", lambda d: (dialogs.append(d.message), d.accept()))
    page.locator("#export").click()
    assert dialogs and "rationale" in dialogs[-1]
    page.get_by_label("Rationale claim-001", exact=True).fill(
        "Automated UI test on deliberately wrong demo year, not an independent human audit."
    )
    page.locator("#export").click()
    assert "contradicting evidence" in dialogs[-1]
    page.get_by_label(
        "Evidence relation claim-001 passage-0001", exact=True
    ).select_option("contradicts")
    with page.expect_download() as download:
        page.locator("#export").click()
    path = Path("/tmp/claim-evidence-test-export.json")
    download.value.save_as(str(path))
    result = json.loads(path.read_text())
    assert result["human_review"]["claims"]["claim-001"]["verdict"] == "contradicted"
    assert result["claims"][0]["verdict"] == "unreviewed"

    # Input edits during analysis cannot make an old result exportable.
    def race(route):
        response = route.fetch()
        page.locator("#response").evaluate(
            "e=>{e.value='Changed input is not the previous response.';e.dispatchEvent(new Event('input'));}"
        )
        route.fulfill(response=response)

    page.route("**/analyze", race, times=1)
    page.locator("#analyze").click()
    expect(page.locator("#input-status")).to_contain_text("Result discarded")
    assert page.locator("#export").is_disabled()
    page.locator("#example").click()
    page.locator("#analyze").click()
    page.wait_for_selector(".claim")
    expect(page.locator("#input-status")).to_contain_text("Local analysis complete")
    details = page.locator(".claim").first.locator("details")
    details.locator("summary").click()
    details.get_by_role("button", name="Search Wikimedia").click()
    assert "Approve" in details.inner_text()
    assert not any("/discover" in u for u in requests)
    details.locator("input[type=checkbox]").check()
    details.locator("input.query").fill("NASA operations 1958")
    assert not details.locator("input[type=checkbox]").is_checked()
    details.locator("input[type=checkbox]").check()
    details.get_by_role("button", name="Search Wikimedia").click()
    details.get_by_role("button", name="Add source to corpus").first.wait_for(
        timeout=180000
    )
    assert "NASA" in details.inner_text()
    details.get_by_role("button", name="Add source to corpus").first.click()
    assert page.locator("#export").is_disabled()
    last = page.locator(".source-editor").last
    metadata = last.evaluate("(e)=>e.sourceMetadata")
    assert "retrieved automatically" in metadata["origin"]
    assert metadata["last_modified_at"]
    assert metadata["license"]
    last.locator("textarea").fill("User changed this source text.")
    metadata = last.evaluate("(e)=>e.sourceMetadata")
    assert "User-edited" in metadata["origin"]
    assert metadata["retrieved_at"] is None
    assert metadata["last_modified_at"] is None
    assert metadata["original_source"]["license"]
    assert metadata["license"] == metadata["original_source"]["license"]
    page.locator("#analyze").click()
    expect(page.locator("#input-status")).to_contain_text("Local analysis complete")
    with page.expect_download() as download:
        page.locator("#export").click()
    download.value.save_as(str(path))
    final = json.loads(path.read_text())
    assert final["sources"][-1]["original_source"]["license"]
    assert final["sources"][-1]["retrieved_at"] is None
    assert not errors, errors
    assert all(
        u.startswith(os.environ.get("CLAIMCHECK_URL", "http://127.0.0.1:8771"))
        for u in requests
    )
    print(
        "PASS: extraction/retrieval, exact evidence, review/export gates, input race, consent/query reset, live Wikimedia discovery, provenance reset, mobile width; no JS errors"
    )
    browser.close()
