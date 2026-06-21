# Nimbus — chronological log

(IPs redacted: `ATTACKER_IP`, `TARGET_IP`. All other values are real lab artifacts.)

1. `nmap` → 22 (OpenSSH 9.6p1), 80 (nginx 1.24.0 → `nimbus.htb`).
2. Web app "Internal Job Scheduler" v1.4.2; `/jobs/preview` fetches URLs / parses YAML;
   `/api/v1/health` leaks `aws.nimbus.htb`; `/login` says the submitter is unauthenticated.
3. `aws.nimbus.htb` = AWS-API emulator (STS error when hit directly).
4. SSRF in `/jobs/preview` `url=` confirmed (full response reflection).
5. Filters: must end `.yaml` (bypass `?x=.yaml`); internal-IP string block.
   No redirect-follow. **Bypass: decimal IP `2852039166` for 169.254.169.254.**
6. IMDS → role `nimbus-web-role` →
   `ASIAQX4PG7L2K9M3N5R8` / `bXJ7K8mP/q2Hf+vN9wT4LcRe5Y1Aoz3DhU6gKjQs` / session token.
7. `aws --endpoint-url http://aws.nimbus.htb sts get-caller-identity` works.
   `sqs list-queues` → `http://floci:4566/847219365028/nimbus-jobs`.
8. Worker executes job `script` (Python) from the queue. `sqs send-message` → RCE as
   `uid=1000(worker)` in a container.
9. **user.txt = `c1be2e41e830b0125e55798d65fc97df`** (`/home/worker/user.txt`, group-readable).
10. Worker env leaks `nimbus-worker-role` static keys (`AKIA7P3R9X4K8M2L5VHN` / `dM4nV/...`) — not more privileged.
11. **`http://floci:4566` direct = unauthenticated admin** (`test`/`test` → `iam::root`).
    Emulator = **floci** (LocalStack fork), all services running.
12. S3 bucket `nimbus-dev-artifacts` holds a prior solver's leftover gadget YAMLs + `source/worker.py`.
13. Container-escape analysis:
    - Lambda: root but default-cap, RO `/proc/sys`, device-cgroup → no escape.
    - ECS: root + entrypoint/cmd override, but **ignores privileged + host volumes**.
    - Batch: no privileged.
    - **CodeBuild: honours `privilegedMode` (real `--privileged`)** — intended primitive.
    - **EC2/EKS: unconditionally privileged**; EC2 runs UserData as root via `docker exec`.
14. **Blocker:** host is offline (DNS to 8.8.8.8 times out). Only pre-pulled images run.
    Present: `public.ecr.aws/lambda/python:3.11` (root, bad entrypoint),
    `floci/floci:latest` (exec-as-root, but keepalive `mkdir` fails as uid 1001),
    `nimbus_worker:latest` (non-root). EC2/EKS catalog images all absent; no `RegisterImage`.
15. Documented route to root: get a present root/entrypoint-less image into a privileged
    service (ECR-push for CodeBuild, or EC2-UserData via `floci/floci:latest`), then
    `mount /dev/sda4` (or `core_pattern`+overlay `upperdir`) to read `/root/root.txt`
    and plant an SSH key.

## Root — exhaustive empirical verification (every privileged primitive vs. this instance)

The host is **offline** (DNS to 8.8.8.8 times out), so floci-spawned containers can only
use **pre-pulled** images. Confirmed present (via ECS `stoppedReason`): exactly
`public.ecr.aws/lambda/python:3.11`, `floci/floci:latest`, `nimbus_worker:latest`.
Confirmed **absent** (CannotPull): amazonlinux:2, amazonlinux:2023, ubuntu:20.04/22.04/24.04,
debian:12, alpine, busybox, python:3.x-slim, registry:2, floci/floci-ui, floci/floci-duck,
floci/floci:1.5.17, eclipse-temurin.

| Primitive | Result on this instance |
|---|---|
| Lambda | root, but **unprivileged** (`CapEff=a80425fb`, RO `/proc/sys`, device-cgroup). `mknod`+read `/dev/sda4` → EPERM. No escape. |
| ECS | root + entrypoint/cmd override, but **ignores `privileged` and host bind-volumes** (`describe-task-definition` shows `volumes:null`; raw-JSON confirms). |
| Batch | no `privileged` field at all. |
| EC2 | launches **privileged** + runs UserData as root — but resolves AMIs only to catalog images, **all absent** → every instance `terminated`. No `RegisterImage` to point an AMI at a present image. |
| EKS | **privileged**, but uses `rancher/k3s:latest` (absent) and runs only `k3s server` (no command control). |
| CodeBuild | honours `privilegedMode` (→ `--privileged`), but its keepalive `mkdir -p /codebuild/output/src/src && tail -f /dev/null` runs as the image's default user. floci image → `mkdir /codebuild: Permission denied` (gosu→uid 1001); lambda image → `entrypoint requires the handler name` (3-arg CMD); worker image → non-root. No present image is root + entrypoint-less. |
| ECR push (custom image) | blocked — the `registry:2` backing image is absent and can't be pulled offline, so the registry never starts. |
| Lambda hot-reload (RW host bind-mount of arbitrary host path → root container) | **disabled** (`FLOCI_SERVICES_LAMBDA_HOT_RELOAD_ENABLED` not set). |
| SSM `SendCommand` (`AWS-RunShellScript`) | `docker exec`s into an EC2-instance container — none can run (EC2 images absent). |

**Conclusion:** every privileged / host-mount primitive is gated by an image that is not
present on this offline instance (or by a disabled feature). Root is not reachable through
the floci AWS-service container-escape paths in this state without a present, root-capable
image. The running build reports version `1.5.17`, which differs from the floci HEAD source
analysed here (e.g. ECS host-volume handling differs) — so the intended root step may rely
on a 1.5.17-specific behaviour or a pre-pulled image not present on this particular spawn.

Remaining untried leads: kernel LPE from the unprivileged root container (host kernel
`6.8.0-124-generic`); deeper local enumeration of the `worker` container; or a present
root-capable image that wasn't enumerated.

## ROOT — solved

The missing piece: bypass the `floci/floci` entrypoint's `gosu` privilege-drop with a
Shellshock-style exported bash function. The entrypoint checks `id` to decide whether to
drop from root; setting `BASH_FUNC_id%%=() { echo uid=1000; }` via CodeBuild
`start-build environmentVariablesOverride` makes `id` lie, so the entrypoint skips the drop
and the keepalive (`mkdir -p /codebuild/... && tail -f /dev/null`) runs as **real root**.
That keeps the present `floci/floci:latest` image alive in a real `--privileged` CodeBuild
container, from which the `core_pattern` + overlay-`upperdir` escape runs a script as root
on the host: copy `/root/root.txt` into the container's upperdir and plant an SSH key in
`/root/.ssh/authorized_keys`.

- **user.txt = `c1be2e41e830b0125e55798d65fc97df`**
- **root.txt = `40fed8986aecd3dc5ee8346a2a82c582`**
- Verified full interactive host root via `ssh root@TARGET_IP` (uid=0, host `nimbus`).
