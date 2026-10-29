"""Optional real-browser UI smoke; does not require local network access.

Exercises the separately labeled static showcase. The actual HTTP API is
covered by tests/test_studio.py. No live model requests are performed.

Run: PYTHONPATH=src python tests/browser_studio_optional.py
"""
from pathlib import Path
from playwright.sync_api import sync_playwright


def run():
    project=Path(__file__).resolve().parents[1]
    output=Path('/mnt/data')
    html=(project/'examples/interactive_showcase.html').read_text(encoding='utf-8')
    failures=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
        for width,height,label in [(1440,900,'desktop'),(390,844,'mobile'),(360,800,'smallmobile'),(768,900,'tablet'),(1024,768,'laptop')]:
            page=browser.new_page(viewport={'width':width,'height':height},device_scale_factor=1,accept_downloads=True)
            page.on('pageerror',lambda exc:failures.append(str(exc)))
            page.set_content(html,wait_until='load')
            page.wait_for_timeout(100)
            assert "Loading" not in page.locator("#root").inner_text()
            assert page.locator('#run').is_visible()
            assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), (label,page.evaluate('document.documentElement.scrollWidth'),width)
            if label in ('desktop','mobile'):
                page.screenshot(path=str(output/f'ConsensusTree_AI_v6_Studio_{label}.png'),full_page=True)
            page.locator('#demo').click()
            page.locator('#result-content').wait_for(state='visible')
            assert page.locator('#result-meta').inner_text().startswith('FICTIONAL OFFLINE DEMO')
            page.locator('[data-nav="workspace"]').click()
            page.locator('#preview').click()
            page.wait_for_timeout(100)
            assert page.locator("#file-list li").count()==3
            page.locator('#consent').check()
            page.locator('#run').click()
            page.wait_for_timeout(1350)
            assert "Northstar Tasks" in page.locator("#result-task").inner_text(), page.locator("#feedback").inner_text()
            assert page.locator('#result-meta').inner_text().startswith('FICTIONAL OFFLINE DEMO')
            assert page.evaluate('window.__injected === undefined')
            assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), label+' result overflow'
            if label in ('desktop','mobile'):
                page.screenshot(path=str(output/f'ConsensusTree_AI_v6_Results_{label}.png'),full_page=True)
            with page.expect_download() as info:
                page.locator('#export-json').click()
            assert info.value.suggested_filename=='consensustree-report.json'
            page.locator('#theme').click()
            assert page.locator('html').get_attribute('data-theme')=='light'
            if label=='desktop':page.screenshot(path=str(output/'ConsensusTree_AI_v6_Light_Preview.png'),full_page=True)
            page.locator('[data-nav="workspace"]').click()
            page.locator('#mode-ask').click()
            assert page.locator('#question').is_visible()
            assert page.locator('#role-1').inner_text()=='Pragmatist'
            page.close()
        browser.close()
    assert not failures, failures
    print('5 viewport UI checks passed; simulated demo, preview, exports, mode switching, CSP and theme.')

if __name__=='__main__':run()
