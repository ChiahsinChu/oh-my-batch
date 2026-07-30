# `omb shell` — small guards for driver scripts

Source: `oh_my_batch/shell.py` (`Shell`). Two helpers that make a driver fail fast and
loudly on a missing input or env var. Both **exit non-zero** on failure, so they compose
with `set -e`.

> Naming note: the README's feature list still calls this group `omb misc`, but the actual
> command registered in `cli.py` is **`omb shell`**.

## `try_file`

```
omb shell try_file <path> [<path> …]
```

Prints the **first** argument that exists — as a file, a directory, or a glob with at least
one match (`glob.glob(..., recursive=True)`, so `**` works). If none exist, prints an error
to stderr and exits `1`.

Use it to pick whichever of several candidate locations is present:

```bash
MODEL=$(omb shell try_file model.pt checkpoints/best.pt 'runs/**/final.pt') || exit 1
```

Note it returns the **pattern/path you passed**, not the expanded match — so for a glob
argument you get the glob string back, not the file it matched.

## `require_env`

```
omb shell require_env VAR1 [VAR2 …]
```

Checks each named environment variable is set and non-empty. For each present var it prints
`VAR=value`; if any are missing/blank it lists them on stderr and exits `1`.

```bash
omb shell require_env WORK_DIR CONFIG_DIR SLURM_ACCOUNT || exit 1
```

Put this at the top of a driver so it stops immediately instead of failing deep inside a
stage with an empty path.
