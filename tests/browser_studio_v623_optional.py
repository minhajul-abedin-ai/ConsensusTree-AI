"""Optional real Chromium smoke for v6.2 live-workbench UI with MOCK HTTP endpoints.

Does not run a live backend or make provider calls. Python HTTP tests cover the
backend separately. This verifies the actual browser JS/HTML and responsiveness.

Run: python tests/browser_studio_v62_optional.py
"""
from pathlib import Path
import json
from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT/'src'))
from consensustree.studio import _studio_template
PAGE = _studio_template()
OUT = Path('/mnt/data/ConsensusTree_AI_v6.2.3_Previews')
OUT.mkdir(parents=True, exist_ok=True)
REPORT = {
  "mode":"review", "task":"Review the user-approved source-file excerpts.",
  "created_utc":"2026-10-28T21:30:00+00:00", "agents":[
    {"role":r,"model":f"ollama:{m}","content":"## Finding\nExample path `app.py:2`; this is a test fixture, not a real defect.","duration_seconds":0.1}
    for r,m in [('Architecture','first'),('Security','second'),('Reliability','third')]],
  "synthesis":"## Final recommendation\nCheck line-level references before acting.",
  "groups":[], "errors":[], "execution":{"reference_audit":{"checked_references":3,"in_snapshot":3,"outside_snapshot":0,"agents_without_line_references":0,"fact_checked":False}}
}


def run():
  failures=[]
  with sync_playwright() as playwright:
    browser=playwright.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
    for width,height,label in [(360,800,'small'),(390,844,'mobile'),(768,1000,'tablet'),(1024,768,'laptop'),(1440,900,'desktop')]:
      context=browser.new_context(viewport={'width':width,'height':height},accept_downloads=True)
      page=context.new_page();page.on('pageerror',lambda err:failures.append(str(err)))
      page.evaluate("""(report) => {
        window.__mockReport=report;
        window.__sentBody=null;
        window.fetch=async (url,opts={}) => {
          const path=String(url).split('?')[0];
          let body={};
          if(path==='/api/status') body={root:'/local/approved/repository',providers:{ollama:'llama3.2',openai:'gpt-4.1-mini',gemini:'gemini-2.5-flash',anthropic:'claude-sonnet-4-5'},configured:{openai:true,anthropic:true,gemini:true},version:'6.2.3rc1',local_only:true};
          if(path==='/api/preview') body={files:['app.py'],file_count:1,characters:152,source_excerpt:'\\n--- FILE: app.py ---\\n   1 | x=1\\n   2 | print(x)\\n--- END FILE: app.py ---',truncated:false,fingerprint:'0'.repeat(64),warnings:[]};
          if(path==='/api/run'){window.__sentBody=JSON.parse(opts.body);body={job_id:'mock-job',status:'running'}}
          if(path==='/api/jobs/mock-job') body={status:'completed',report:window.__mockReport,events:['Completed mock task'],error:null};
          if(path==='/api/demo') body={report:{...window.__mockReport,demo:true},notice:'Fixture only'};
          return new Response(JSON.stringify(body),{status:200,headers:{'Content-Type':'application/json'}});
        };
      }""", REPORT)
      page.set_content(PAGE,wait_until='load')
      page.locator('#root').wait_for(state='visible')
      assert 'approved' in page.locator('#root').inner_text()
      assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), label
      if label=='desktop':page.screenshot(path=str(OUT/'ConsensusTree_AI_v6.2.3_Studio_Desktop.png'),full_page=True)
      if label=='mobile':page.screenshot(path=str(OUT/'ConsensusTree_AI_v6.2.3_Studio_Mobile.png'),full_page=True)
      page.locator('#custom-models').check()
      page.locator('#reviewer-options').wait_for(state='visible')
      for idx,name in enumerate(['first','second','third'],1):
        page.locator(f'#reviewer-model-{idx}').fill(name)
      page.locator('#preview').click()
      page.locator('#file-list li').first.wait_for(state='visible',timeout=3000)
      assert page.locator('#file-list li').count()==1
      page.locator('#preview-excerpts').wait_for(state='visible')
      assert 'print(x)' in page.locator('#preview-source').text_content()
      page.locator('#consent').check()
      page.locator('#run').click()
      page.locator('#result-content').wait_for(state='visible',timeout=6000)
      assert page.evaluate('window.__sentBody.reviewers.length')==3
      assert page.evaluate('window.__sentBody.reviewers.map(r=>r.model)')==['first','second','third']
      assert '3 file:line references' in page.locator('#reference-checks').inner_text()
      assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), label+' results overflow'
      if label=='desktop':page.screenshot(path=str(OUT/'ConsensusTree_AI_v6.2.3_Results_Desktop.png'),full_page=True)
      if label=='mobile':page.screenshot(path=str(OUT/'ConsensusTree_AI_v6.2.3_Results_Mobile.png'),full_page=True)
      with page.expect_download() as download:
        page.locator('#export-json').click()
      assert download.value.suggested_filename=='consensustree-report.json'
      page.locator('#theme').click()
      assert page.locator('html').get_attribute('data-theme')=='light'
      page.locator('[data-nav="workspace"]').click()
      page.locator('#mode-ask').click()
      assert page.locator('#reviewer-label-1').inner_text()=='Pragmatist provider'
      if label=='desktop':
        page.evaluate("""() => {window.__mockReport.execution.completion={status:'partial',expected_specialists:3,successful_specialists:2,chair_required:true,chair_completed:true,failed_steps:1};window.__mockReport.errors=['Security reviewer failed'];}""")
        page.locator('#mode-review').click()
        page.locator('#preview').click()
        page.locator('#consent').check()
        page.locator('#run').click()
        page.locator('#result-content').wait_for(state='visible',timeout=6000)
        assert 'INCOMPLETE COUNCIL' in page.locator('#result-meta').inner_text()
        assert 'INCOMPLETE COUNCIL' in page.locator('#result-errors').inner_text()

      context.close()
    browser.close()
  assert not failures,failures
  print('5 Chromium browser viewport checks passed with mocked API; no live model or real server calls.')


if __name__=='__main__':run()
