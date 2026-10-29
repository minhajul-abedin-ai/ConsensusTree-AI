"""Optional, non-CI Chromium UI smoke check.

Requires ``pip install playwright`` and locally available Chromium:

    python tests/browser_smoke_optional.py examples/showcase_preview.html

The normal Python unittest suite does not depend on Playwright.
"""
from pathlib import Path
import sys
import shutil
from playwright.sync_api import sync_playwright


def smoke(path: Path) -> None:
    html = path.read_text(encoding='utf-8')
    with sync_playwright() as pw:
        binary = shutil.which("chromium") or shutil.which("google-chrome")
        browser = pw.chromium.launch(headless=True, **({"executable_path": binary} if binary else {}))
        try:
            for width in (360, 390, 414, 768, 1024, 1440):
                page = browser.new_page(viewport={'width': width, 'height': 860})
                errors, requests = [], []
                page.on('pageerror', lambda exc: errors.append(str(exc)))
                page.on('request', lambda request: requests.append(request.url))
                page.set_content(html)
                assert page.locator('#page-overview').is_visible()
                assert page.evaluate('document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1')
                page.locator('button[data-view=council]').click()
                assert page.locator('#page-council').is_visible()
                page.locator('button[data-view=evidence]').click()
                assert page.locator('#page-evidence').is_visible()
                page.locator('button[data-view=raw]').click()
                assert page.locator('#raw-json').inner_text().strip().startswith('{')
                page.locator('#theme').click()
                assert page.locator('html').get_attribute('data-theme') == 'light'
                assert not errors, errors
                assert not requests, requests
                print(f'PASS width={width}, controls, no overflow, no requests')
                page.close()
        finally:
            browser.close()


if __name__ == '__main__':
    path = Path(sys.argv[1] if len(sys.argv) > 1 else 'examples/showcase_preview.html')
    smoke(path)
