"""Generate a stand-alone, plainly labeled fictional workbench showcase.

The file works with no local server or credentials. It never makes a network
request and is not the live AI app; `consensustree studio` is the live app.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
from pathlib import Path

from consensustree.cli import _demo

ROOT=Path(__file__).resolve().parents[1]

report={
  "mode":"review", "task":"Fictional code review: Northstar Tasks API",
  "created_utc":"2026-10-28T00:00:00+00:00", "demo":True,
  "agents":[
      {"role":"Architecture", "model":"illustrative-fixture", "duration_seconds":0,
       "content":"# Summary\nModular design is promising but error handling is spread across two layers.\n\n# Findings\nMedium · src/api.py:42 — Separate request validation from business logic.\n\n# Suggested fixes\nIntroduce a typed request schema and a single validation boundary.\n\n# Unknowns\nTraffic and latency constraints have not been measured."},
      {"role":"Security", "model":"illustrative-fixture", "duration_seconds":0,
       "content":"# Summary\nReview authentication and request validation before a public launch.\n\n# Findings\nHigh · src/auth.py:27 — Check authorization on resource ownership, not just login.\n\n# Suggested fixes\nAdd negative tests for cross-user resource access.\n\n# Unknowns\nNo live threat model or penetration test was performed."},
      {"role":"Reliability", "model":"illustrative-fixture", "duration_seconds":0,
       "content":"# Summary\nThe API lacks tests for failure paths and retries.\n\n# Findings\nMedium · tests/test_api.py:14 — Missing timeout/retry scenarios.\n\n# Suggested fixes\nIntroduce deterministic tests for transient errors.\n\n# Unknowns\nNo real code was executed in this illustrative fixture."}
  ],
  "chair_model":"illustrative-fixture",
  "synthesis":"# Final recommendation\nRun a focused hardening sprint before production release.\n\n# Areas of agreement\nThe specialists prioritize safer input boundaries, authorization checks and failure-path tests.\n\n# Disagreements / uncertainties\nSeverity labels are hypothetical. No actual repository has been reviewed.\n\n# Priority next steps\n1. Add ownership checks and negative tests.\n2. Centralize validation.\n3. Test timeout/retry handling.\n\n# Verification required\nThis is a fictional UI showcase, not a real security assessment.",
  "groups":[],"errors":[],"reviewed_files":["src/api.py","src/auth.py","tests/test_api.py"],
  "snapshot_truncated":False,"execution":{"source":"offline-showcase","metering":{"api_calls":0,"estimated_not_billed":True}}
}

def main():
    path=ROOT/'src/consensustree/studio_template.html'
    template=path.read_text(encoding='utf-8')
    samples=json.dumps({"demo":_demo().to_dict(),"review":report},ensure_ascii=True)
    mock='''async function api(path,body){\n  if(path==='/api/status') return {root:'fictional-project (offline preview)',version:'6.0.0rc1 · SHOWCASE',providers:providerDefaults,configured:{}};\n  if(path==='/api/preview') return {files:['src/api.py','src/auth.py','tests/test_api.py'],file_count:3,characters:4820,truncated:false,warnings:[],fingerprint:'fictional-demo-fingerprint'};\n  if(path==='/api/demo') return {report:SHOWCASE.demo,notice:'Fictional offline example'};\n  if(path==='/api/run')return {job_id:'fictional-session',status:'running'};\n  if(path.startsWith('/api/jobs/'))return {status:'completed',report:SHOWCASE.review,events:['Fictional preview: no model calls occurred.']};\n  throw Error('This is a static showcase, not a live backend');\n}\n'''
    inject='const SHOWCASE='+samples+';\n'+mock
    needle=r'async function api\(path,body\)\{.*?\}\nfunction make'
    template,count=re.subn(needle,lambda m:inject+'function make',template,flags=re.DOTALL)
    if count!=1:raise RuntimeError('Cannot locate API interface in studio template')
    template=template.replace('LOCAL &amp; PRIVATE','OFFLINE SHOWCASE')
    template=template.replace('LOCAL &amp; PRIVATE','OFFLINE SHOWCASE')
    template=template.replace('No telemetry · No cloud storage<br>Data leaves only after your approval.','Fictional UI preview only<br>No AI calls · No data transfer.')
    template=template.replace('This is a local single-user workbench, not a hosted multi-user SaaS.', 'This interactive preview uses fictional data. Download the Python package for real local reviews.')
    template=template.replace('I understand the selected code or question will be transmitted to my chosen model provider when I click <b>Run council</b>. Local Ollama stays on my configured local endpoint.', 'I understand this <b>showcase is simulated</b> and makes no AI provider calls. The real local app requires separate consent for sending data.')
    template=template.replace('API credentials stay on your machine.','All results shown in this preview are fictional.')
    template=template.replace('No model calls have been made in this session.','OFFLINE PREVIEW · No real model calls can be made here.')
    template=template.replace('Local-only server', 'Local-only app in real version')
    css=re.search(r'<style>(.*?)</style>',template,re.DOTALL)
    js=re.search(r'<script>(.*?)</script>',template,re.DOTALL)
    for placeholder,block in [('__STYLE_HASH__',css.group(1)),('__SCRIPT_HASH__',js.group(1))]:
        hash_='sha256-'+base64.b64encode(hashlib.sha256(block.encode('utf8')).digest()).decode('ascii')
        template=template.replace(placeholder,hash_)
    out=ROOT/'examples/interactive_showcase.html'
    out.write_text(template,encoding='utf-8')
    print(out)

if __name__=='__main__':main()
