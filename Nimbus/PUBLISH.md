# Publish checklist — run ONLY after Nimbus has retired

HackTheBox does not permit public writeups for machines that are still active.
Once Nimbus shows as **Retired** on the HTB platform, the steps below make the repo
public and easy to find — copy-paste, one shot.

```bash
# 1. flip to public
gh repo edit bidnessnonya28/HTB --visibility public

# 2. searchable description
gh repo edit bidnessnonya28/HTB \
  --description "HackTheBox writeups — step-by-step walkthroughs & exploit code. Nimbus (Linux, Hard): SSRF → IMDS → SQS worker RCE → LocalStack/floci admin → privileged CodeBuild + core_pattern container escape to root."

# 3. global-search topics (drive GitHub topic search)
gh repo edit bidnessnonya28/HTB \
  --add-topic hackthebox --add-topic htb --add-topic ctf --add-topic writeup \
  --add-topic walkthrough --add-topic nimbus --add-topic ssrf --add-topic aws \
  --add-topic localstack --add-topic container-escape --add-topic privilege-escalation \
  --add-topic core-pattern --add-topic codebuild --add-topic penetration-testing
```

That's it — public + described + tagged in three commands. The writeup content
(`Nimbus.md`) is already written with the relevant terms in its headings, so it indexes
well on its own once the repo is public.
