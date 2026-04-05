# DTU HPC No-Brainer Workflow

Use this file when you want the shortest possible instructions for pushing code to DTU HPC and running experiments.

## Host split

Use two DTU endpoints:

- **login / submit host**: `dtu-hpc`
- **transfer host**: `s232278@transfer.gbar.dtu.dk`

Why:
- use `ssh dtu-hpc` for interactive login and `bsub`
- use `rsync` / `scp` via `transfer.gbar.dtu.dk` for file transfer

## Recommended SSH config

Put something like this in `~/.ssh/config` on your Mac:

```ssh-config
Host dtu-hpc
    HostName hpc.dtu.dk
    User s232278

Host dtu-transfer
    HostName transfer.gbar.dtu.dk
    User s232278
```

If your school gave you a different login hostname than `hpc.dtu.dk`, replace it accordingly.
The scripts already default to the explicit transfer endpoint `s232278@transfer.gbar.dtu.dk`, so they still work without the alias; the SSH config just makes manual use easier.

## Off-campus authentication rule

When working off campus, DTU may still require one interactive password step even if SSH keys are configured.

The standard rule is:

1. the user first opens another local terminal window
2. manually pre-authenticates with DTU there
3. keeps that session open
4. then lets the agent run the normal scripts

Recommended pre-auth commands:

```bash
ssh dtu-hpc
ssh s232278@transfer.gbar.dtu.dk
```

Agent rule:
- do not store or inject passwords
- assume the user may pre-authenticate manually first
- after that, continue with the normal scripted workflow

## The only 3 commands you really need

### 1. Push source to HPC

```bash
./local_sync_to_hpc.sh
```

This sends the source-focused thesis workspace to:

```text
/zhome/2a/1/202283/thesis/
```

It intentionally excludes heavy runtime-state folders.

### 2. Push source and submit an LSF job

```bash
./push_and_submit_lsf.sh \
  --job 22.03controller_line/jobs/submit_exp01.sh \
  --smoke-cmd "python -m pytest 22.03controller_line/tests -q"
```

What it does:
1. run local smoke test
2. rsync source to DTU via `s232278@transfer.gbar.dtu.dk`
3. ssh to `dtu-hpc`
4. run `bsub < ...`

### 3. Pull big results back from HPC

```bash
./pull_hpc_results.sh \
  --remote-path 22.03controller_line/data/results/EXP_EXP01 \
  --local-subdir hpc-pulls/exp01
```

This pulls into:

```text
~/thesis-local-state/dtu-sem6/hpc-pulls/exp01/
```

## Default paths and defaults

Default remote thesis root:

```text
/zhome/2a/1/202283/thesis/
```

Default transfer host:

```text
s232278@transfer.gbar.dtu.dk
```

Default login host:

```text
dtu-hpc
```

## Manual DTU commands if needed

### Login

```bash
ssh dtu-hpc
```

### Copy one file from DTU to local

```bash
scp s232278@transfer.gbar.dtu.dk:/path/to/file .
```

### Copy one directory from DTU to local

```bash
rsync -av s232278@transfer.gbar.dtu.dk:/path/to/directory .
```

### Copy local directory to DTU

```bash
rsync -av local-directory/ s232278@transfer.gbar.dtu.dk:/zhome/2a/1/202283/thesis/
```

## Recommended everyday workflow

### Algorithm iteration

```bash
cd "/Users/zhangjiajia/Life-OS/20-29 Study/22 DTU Semester 6"

git status
git add .
git commit -m "describe change"

./push_and_submit_lsf.sh \
  --job 22.03controller_line/jobs/submit_exp01.sh \
  --smoke-cmd "python -m pytest 22.03controller_line/tests -q"
```

### Check jobs

```bash
ssh dtu-hpc
bjobs
```

## Rules

- use Git for version history
- use the scripts for DTU sync / submit
- off campus, the user may manually pre-authenticate in another terminal window first to satisfy DTU's password gate
- do not store or inject DTU passwords in scripts or docs
- the transfer host may still prompt for DTU password / 2FA if pre-authentication has not happened yet; that is normal on your own terminal
- do not rsync heavy runtime-state folders through ad hoc commands unless you really mean to
- do not pull giant results back into the iCloud repository root
- large pulled outputs belong under `~/thesis-local-state/dtu-sem6/hpc-pulls/`

## For agents

If an agent needs the canonical workflow, tell it to read:

- `DTU_HPC_NO_BRAINER.md`
- `DROID_AI_WORKSPACE_GUIDE.md`
- `DROID_AI_ALGORITHM_HANDOFF.md`
- `WORKSPACE_MAP.md`
