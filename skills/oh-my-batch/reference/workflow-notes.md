# Operational gotchas (SLURM / drivers)

These are runtime pitfalls that the CLI reference won't warn you about — they come from
how `omb batch` scripts actually behave under a scheduler. General to `omb`; not specific
to any one workflow.

## The guarded-generation / unguarded-submission pattern

Generation is expensive to redo and should be **guarded**; submission is cheap and should
be **idempotent**, so a re-run of the driver resumes instead of restarting:

```bash
[ -f $STAGE_DIR/setup.done ] && echo "skip setup" || {
    omb combo … done
    omb batch … make …
    touch $STAGE_DIR/setup.done
}

omb job slurm submit "$STAGE_DIR/*.slurm" \
    --max_tries 2 --wait --recovery $STAGE_DIR/recovery.json
```

`setup.done` means "the job dirs are rendered." Submission re-runs every time and is made
safe by two things: the `--recovery` file (won't resubmit tracked jobs) and `.done` markers
**inside each job's `run.sh`** (a resubmitted script no-ops the already-finished work):

```bash
#!/bin/bash
set -e
[ -f md.done ] || {
    lmp -in input.lmp
    touch md.done
}
```

## Header rules that bite under `--concurrency`

The header you pass to `omb batch add_header_files` is copied **verbatim** into a plain
`#!/bin/bash` (non-login) script. That has consequences:

- **No `#SBATCH --export NONE`.** The Lmod `module` shell function reaches the job only by
  being inherited from the submitting environment. `--export NONE` drops it, and every
  `module load` dies with "command not found" — under `set -e` that kills the job before
  the software is ever on `PATH`. (`unset SLURM_EXPORT_ENV` does not help; it only affects
  what `srun` forwards, not the batch script's own environment.)

- **No `#SBATCH --output` / `--error` when using `--concurrency`.** Those paths are relative
  to the *submission* directory, not the per-job dir, so parallel scripts all write the same
  two files and clobber one another. Let SLURM's default `slurm-%j.out` keep them separate;
  move the clutter to `logs/` after the run.

- **Put thread pinning in the header**, not in `run.sh`: `OMP_NUM_THREADS`,
  `OMP_PLACES=cores`, `OMP_PROC_BIND=close`. Set `MKL_NUM_THREADS=1` where a threaded MKL
  FFT is known to corrupt results (e.g. LAMMPS PPPM long-range electrostatics returning
  garbage while other energy terms look fine).

- **Activate exactly one environment** in the header, and never the orchestration/omb env
  itself. If a software stack ships its own `env.sh`, source it whole rather than
  cherry-picking lines.

## `set -e` and the sequential loop

`omb batch` runs the work dirs in one script **sequentially** (`pushd … popd`). A `set -e`
in the header therefore **aborts the whole script on the first failing dir**, and the
remaining dirs in that script never run. That is fine *if* every job is `.done`-guarded and
you submit with `--max_tries ≥ 2`: the resubmit skips the finished dirs and retries from the
one that died. Without the guards, a resubmit restarts completed work.

## Checks worth running

**Catch an `@VAR` that survived rendering** (`make_files` uses `safe_substitute`, which
leaves unknown placeholders in the file silently):

```bash
grep -rho '@[A-Z_][A-Z0-9_]*' <rendered-job-dirs>/ | sort -u
```

**Confirm the driver sets every placeholder the templates use** — the two lists should
match:

```bash
# placeholders the templates reference
grep -rho '@[A-Z_][A-Z0-9_]*' <template-dir>/ | sort -u
# keys the driver defines
grep -ho 'add_var [A-Z_][A-Z0-9_]*\|add_files [A-Z_][A-Z0-9_]*\|add_randint [A-Z_][A-Z0-9_]*' \
    <driver>.sh | awk '{print "@"$2}' | sort -u
```

A template using a variable the driver never sets is a **silent** failure at job runtime,
not at generation time. Diff these before a new stage goes live.
