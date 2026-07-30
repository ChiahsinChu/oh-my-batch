# `omb job` — submitting and tracking scheduler jobs

Source: `oh_my_batch/job.py`. Three schedulers share one interface (`BaseJobManager`):

```
omb job slurm   <submit|wait> …
omb job lsf     <submit|wait> …
omb job openpbs <submit|wait> …
```

> The command is **`openpbs`**, not `pbs`. `lsf` also answers to the class alias `LFS`.
> Each scheduler's constructor takes binary-path overrides you can pass before the
> sub-command, e.g. `omb job slurm --sbatch /path/sbatch --squeue … submit …`
> (slurm: `sbatch/sacct/squeue`; lsf: `bsub/bjobs`; openpbs: `qsub/qstat`).

## `submit`

```
omb job <scheduler> submit <script-globs…> \
    [--recovery FILE] [--wait] [--max_tries N] [--interval SEC] \
    [--timeout SEC] [--opts '…'] [--fast_fail]
```

| Flag | Default | Meaning |
| --- | --- | --- |
| `<script…>` | — | script files/globs to submit (**raises if a glob matches nothing**) |
| `--recovery FILE` | off | JSON file that records job id/state/tries; makes re-runs resumable |
| `--wait` | `False` | block, polling every `--interval`, until all jobs are terminal |
| `--max_tries N` | `1` | resubmit a non-completed script up to N times total |
| `--interval SEC` | `10` | poll interval while waiting |
| `--timeout SEC` | none | stop waiting after this many seconds (logs, doesn't raise on its own) |
| `--opts '…'` | `''` | extra flags passed straight to the submit binary (`sbatch`/`bsub`/`qsub`) |
| `--fast_fail` | `False` | stop waiting and error as soon as any job has failed with tries exhausted |

Behaviour:

- Without `--wait`, `submit` does **one** submit/poll pass and returns.
- With `--wait`, it loops until every job is terminal *and* none is still eligible to
  (re)submit; then it **raises `RuntimeError`** if any job did not complete. This raise is
  what makes `--wait` usable as a hard gate in a linear driver script — but the process
  must survive for the whole run (use `nohup`/`tmux`).
- **Retry / idempotency:** a script is (re)submitted while it is terminal-but-not-completed
  and `tries < max_tries`. Combined with `.done`-guarded work inside each job, a resubmit
  re-runs only the unfinished parts. `--fast_fail` short-circuits the wait once a script is
  `FAILED`/`CANCELLED` with no tries left.

## `wait`

```
omb job <scheduler> wait <job-ids…> [--timeout SEC] [--interval SEC]
```

Polls **already-submitted** job ids (not scripts) until all are terminal or `--timeout`
elapses. No submission, no recovery file. Use it to block on jobs launched elsewhere.

## The recovery file

`--recovery jobs.json` stores a list of job records, rewritten after every poll:

```json
[{"id": "123456", "script": "/abs/batch-0.slurm", "state": 4, "tries": 1}]
```

`state` is the integer `JobState` (`0 NULL, 1 PENDING, 2 RUNNING, 3 CANCELLED,
4 COMPLETED, 5 FAILED, 6 UNKNOWN`). On a re-run with the **same command**, existing records
are loaded and only scripts not already tracked get fresh records — so completed/running
jobs are **not resubmitted**. Pass one recovery file per stage; it is the mechanism that
lets a crashed driver reattach instead of duplicating jobs.

## How job state is resolved (why `.exitcode` exists)

Before submitting, omb **appends exit-code logging** to the script
(`util.inject_exit_code_logging`) — a trailer that writes `$?` to `<script>.exitcode` and
re-exits. This file is the ground-truth fallback when the scheduler no longer reports a job
(e.g. it aged out of the accounting DB). State is resolved in order, first hit wins:

| Scheduler | Resolution order |
| --- | --- |
| slurm | `sacct -X -P` → `squeue` → `<script>.exitcode` |
| lsf | `bjobs` → `<script>.exitcode` |
| openpbs | `qstat -x -F json` → `<script>.exitcode` |

- If the *query command itself* fails (not just "job unknown"), the `.exitcode` fallback is
  **skipped** for that pass and retried next interval — a transient `squeue` outage won't be
  misread as a failure.
- A stale `.exitcode` from a previous run is deleted at submit time to avoid confusion.
- Exit code `0` → `COMPLETED`; anything else → `FAILED`; missing file with the job gone
  everywhere → `FAILED`.

## Example

```bash
omb job slurm submit 'stage/*.slurm' \
    --max_tries 2 --wait --interval 30 --recovery stage/recovery.json
```

Submits every matching script, retries a failed one once, blocks until all finish, and
records state in `recovery.json` so re-running the same line resumes rather than restarts.
