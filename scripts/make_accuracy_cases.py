"""Deterministic 50-case Python vulnerability corpus for validation development.

Cases are AUTHOR-LABELLED teaching fixtures, not externally adjudicated bugs.
Each vulnerable case has a safer matching counterpart. No code is executed.
"""
import json
from pathlib import Path

FAMILIES = [
 ('untrusted_eval',3,'code_execution',
  'def parse_{v}(user_text):\n    return eval(user_text)\n',
  'import ast\ndef parse_{v}(user_text):\n    return ast.literal_eval(user_text)\n'),
 ('untrusted_pickle',3,'deserialization',
  'import pickle\ndef load_{v}(client_bytes):\n    return pickle.loads(client_bytes)\n',
  'import json\ndef load_{v}(client_bytes):\n    return json.loads(client_bytes.decode("utf-8"))\n'),
 ('shell_injection',3,'command_injection',
  'import subprocess\ndef inspect_{v}(filename):\n    return subprocess.run("ls " + filename, shell=True, capture_output=True)\n',
  'import subprocess\ndef inspect_{v}(filename):\n    return subprocess.run(["ls", "--", filename], capture_output=True)\n'),
 ('sql_injection',3,'sql_injection',
  'def find_{v}(db, username):\n    return db.execute("SELECT * FROM users WHERE name = \'" + username + "\'")\n',
  'def find_{v}(db, username):\n    return db.execute("SELECT * FROM users WHERE name = ?", (username,))\n'),
 ('insecure_yaml',3,'deserialization',
  'import yaml\ndef config_{v}(untrusted_text):\n    return yaml.load(untrusted_text, Loader=yaml.Loader)\n',
  'import yaml\ndef config_{v}(untrusted_text):\n    return yaml.safe_load(untrusted_text)\n'),
 ('path_traversal',2,'path_traversal',
  'from pathlib import Path\ndef view_{v}(base, filename):\n    return (Path(base) / filename).read_text()\n',
  'from pathlib import Path\ndef view_{v}(base, filename):\n    root = Path(base).resolve()\n    target = (root / filename).resolve()\n    if not target.is_relative_to(root):\n        raise ValueError("Outside root")\n    return target.read_text()\n'),
 ('tls_verification',2,'tls_validation',
  'import requests\ndef fetch_{v}(url):\n    return requests.get(url, verify=False, timeout=10)\n',
  'import requests\ndef fetch_{v}(url):\n    return requests.get(url, verify=True, timeout=10)\n'),
 ('insecure_tempname',2,'filesystem_race',
  'import tempfile\ndef scratch_{v}():\n    name = tempfile.mktemp()\n    return open(name, "w")\n',
  'import tempfile\ndef scratch_{v}():\n    return tempfile.NamedTemporaryFile(mode="w", delete=True)\n'),
 ('debug_server',2,'configuration',
  'from flask import Flask\napp = Flask(__name__)\ndef start_{v}():\n    app.run(host="0.0.0.0", debug=True)\n',
  'from flask import Flask\napp = Flask(__name__)\ndef start_{v}():\n    app.run(host="127.0.0.1", debug=False)\n'),
 ('weak_password_hash',2,'password_hashing',
  'import hashlib\ndef digest_{v}(password, salt):\n    return hashlib.md5(password.encode()).hexdigest()\n',
  'import hashlib\ndef digest_{v}(password, salt):\n    return hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)\n'),
]

def build():
    cases=[]
    for family,count,category,bad,good in FAMILIES:
        for n in range(1,count+1):
            for expected,code in [(True,bad),(False,good)]:
                cases.append({'id':f'{family}-{n}-'+('unsafe' if expected else 'safe'),
                              'family':family,'category':category,
                              'expected_issue':expected, 'source':code.format(v=n)})
    return {'name':'ConsensusTree synthetic binary code-review accuracy cases',
            'origin':'Author-labelled synthetic examples: NOT independently adjudicated',
            'construction':'25 vulnerable/safe pairs across 10 defect families',
            'version':'1.0', 'cases':cases}

if __name__=='__main__':
    destination=Path(__file__).resolve().parents[1]/'benchmarks'/'accuracy_cases.json'
    destination.write_text(json.dumps(build(),indent=2)+'\n',encoding='utf-8')
    print('Wrote',len(build()['cases']),'author-labelled cases:',destination)
