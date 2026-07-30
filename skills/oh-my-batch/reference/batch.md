# `omb batch` — packing work dirs into scheduler scripts

Source: `oh_my_batch/batch.py` (`BatchMaker`). A `batch` chain collects **work
directories**, attaches a header / body commands / bottom, and emits one or more shell
scripts that loop over the dirs. The chain **ends with `make`**.

```bash
omb batch \
    add_work_dirs 'tasks/*' - \
    add_header_files header.sh - \
    add_cmds 'bash ./run.sh' - \
    make 'batch-{i}.slurm' --concurrency 5
```

## Building blocks

| Method | Signature | Effect |
| --- | --- | --- |
| `add_work_dirs` | `add_work_dirs 'glob' … [--abs]` | collect work dirs from globs (deduped); `--abs` absolutises |
| `filter` | `filter '<expr>'` | keep only dirs where a Python expr is truthy |
| `add_header_files` | `add_header_files file … [--encoding]` | header from file contents (the `#SBATCH` block, module loads) |
| `add_headers` | `add_headers 'line' …` | header from inline strings |
| `add_cmd_files` | `add_cmd_files file …` | body commands from file contents |
| `add_cmds` | `add_cmds 'cmd' …` | body commands from inline strings (run inside each dir) |
| `add_bottom_files` | `add_bottom_files file …` | trailing content from file contents |
| `add_bottoms` | `add_bottoms 'line' …` | trailing content from inline strings |
| `make` | `make '<path>' [--concurrency 0] [--mode 755] [--purge] [--encoding]` | emit the script(s) |

- **`filter`** exposes the dir path as `{workdir}` / `{work_dir}` / `{w}` and the index as
  `{index}` / `{i}`, formatted into the expr and then `eval`'d (so `os` is in scope):
  `filter 'os.path.exists("{workdir}/input.json")'` keeps only dirs that have that file.
  Uses `eval` — trusted input only.
- `add_header_files` / `add_cmd_files` / `add_bottom_files` expand globs and concatenate
  the file **contents** (via `load_files`); the inline `add_headers` / `add_cmds` /
  `add_bottoms` take literal strings. Header, commands, and bottom accumulate across calls.

## `make` and `--concurrency`

`--concurrency N` = **N scripts**, with the work dirs split across them by `split_list`
(contiguous, balanced chunks). It is **not parallelism**: within one script the dirs run
**sequentially** in a `pushd … popd` loop under a single allocation.

- `--concurrency 0` (default) → **one script per work dir**
  (internally set to `len(work_dirs)`).
- `--concurrency 5` over 6 dirs → 5 scripts; one of them runs 2 dirs back to back.
- `path` uses `{i}` for the script index: `make 'batch-{i}.slurm'`.
- `--purge` deletes pre-existing files matching the pattern (`path.format(i='*')`) before
  writing, so a re-run with fewer scripts doesn't leave stale ones behind.
- `--mode` sets the script file mode (default `755`).

## Anatomy of an emitted script

```bash
<header lines, verbatim — e.g. #!/bin/bash and the #SBATCH block>
[ -n "$PBS_O_WORKDIR" ] && cd $PBS_O_WORKDIR  # fix PBS
WORK_DIRS=(/abs/path/tasks/001
/abs/path/tasks/002)

for WORK_DIR in "${WORK_DIRS[@]}"; do
pushd $WORK_DIR
<your add_cmds / add_cmd_files lines>
popd
done
<bottom lines, verbatim>
```

- The header is copied **verbatim and never templated** — put only static facts there
  (`#SBATCH`, module loads, thread exports), no per-job values.
- Work-dir paths are `shlex.quote`d individually; the leading `PBS_O_WORKDIR` line makes
  the same script usable under OpenPBS (which starts jobs in `$HOME`).
- Body commands run **inside** each work dir (after `pushd`), so they reference files by
  their in-dir names (`bash ./run.sh`, `lmp -in input.lmp`).

See [workflow-notes.md](workflow-notes.md) for header rules that bite under `--concurrency`
(`--export NONE` breaking `module`, `--output/--error` clobbering across scripts, `set -e`
aborting a whole batch).
