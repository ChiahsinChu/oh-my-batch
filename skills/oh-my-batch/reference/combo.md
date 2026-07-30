# `omb combo` — parameter-sweep generation

Source: `oh_my_batch/combo.py` (`ComboMaker`). A `combo` chain builds a set of
**variables** (axes), expands them into **combos**, and renders files/output per combo.

```bash
omb combo <add-methods…> - <render-methods…> - done
```

## Mental model: axes → combos

- Each `add_*` call registers a **variable** (an axis) holding a list of values.
- At expansion, axes are combined as a **cartesian product**: 2 data files × 3
  temperatures = 6 combos. A per-combo integer index `i` (0-based) is always available.
- `broadcast KEY` exempts a key from the product — it rides **one value per combo**
  (`combo[k] = values[i % len(values)]`), so it does not multiply the count.
- Expansion happens lazily the first time a render method runs (`_make_combos`), and it
  **consumes** the pending vars. Add all axes before the first render method in the chain.

## Adding variables (axes)

| Method | Signature | Effect |
| --- | --- | --- |
| `add_var` | `add_var KEY v1 v2 …` | one axis with the given literal values |
| `add_seq` | `add_seq KEY START STOP [STEP]` | axis from `range(start, stop, step)` (stop exclusive) |
| `add_randint` | `add_randint KEY -n N -a A -b B [--uniq] [--seed S]` | N random ints in `[A,B]`; `--uniq` samples distinct (errors if range too small) |
| `add_rand` | `add_rand KEY -n N -a A -b B [--seed S]` | N random floats in `[A,B)` |
| `add_files` | `add_files KEY 'glob' [--abs] [--raise_invalid]` | **one value per matching file** |
| `add_file_set` | `add_file_set KEY 'glob' [--sep ' '] [--format …] [--abs]` | **all matches joined into a single value** |

Details and gotchas:

- **`add_var`** appends to the axis if the key already exists (calling it twice extends
  the same axis). The name **`i` is reserved** and raises `ValueError`.
- **`add_files`** globs each pattern and adds one value per file. It **raises
  `ValueError: No files found`** when nothing matches — the failure you want, so an empty
  sweep can't silently render zero jobs. `--abs` makes each path absolute.
- **`add_file_set`** joins all matches into one string (default `--sep ' '`). Use for a
  model ensemble or any "pass all of them at once" value. `--format` is `None` (plain
  join), `json-list` (`["a","b"]`), or `json-item` (`"a", "b"` — list without brackets,
  handy for splicing into an existing JSON array). Also raises if nothing matches.
- `--seed` on a random method reseeds the global RNG at that point; you can also seed the
  whole chain with `omb combo --seed 42 …` (constructor arg).

## Reshaping axes

| Method | Signature | Effect |
| --- | --- | --- |
| `broadcast` | `broadcast KEY …` | ride one-per-combo instead of multiplying (see model above) |
| `set_broadcast` | `set_broadcast KEY …` | alias for `broadcast` |
| `compute` | `compute KEY 'expr'` | new key from a Python expr `eval`'d against the combo dict |
| `shuffle` | `shuffle KEY … [--seed S]` | shuffle a variable's values in place |
| `sort` | `sort KEY … [--reverse]` | sort a variable's values |

- **`compute`** expressions see the other combo keys as locals, e.g.
  `compute CELL 'A * 3'` or `compute NAME '"job_%03d" % i'`. Evaluated per combo after the
  product is formed. Uses `eval` — trusted input only.
- **`set_broadcast` is an alias for `broadcast`** (since 0.7.6). ⚠ In the released **0.7.5
  it is broken** — implemented as `self.broadcast(self, *keys)`, which passes the
  `ComboMaker` instance itself as a key and raises
  `ValueError: Variable <…ComboMaker object…> not found`. On 0.7.5 use `broadcast`; on
  0.7.6+ either name works.

## Rendering per combo

### `make_files` — render a template

```
make_files <dest> --template <tmpl> [--delimiter @] [--mode 755]
           [--encoding utf-8] [--extra_vars_from_file <json>] [--ignore_error]
```

- **Placeholders inside the template** are `@VAR` — `string.Template` with the delimiter
  swapped from `$` to `@`, so ordinary shell `$VAR` in a `run.sh` template passes through
  untouched. `--delimiter` changes it if `@` collides with your file format.
- **`dest` and `template` paths are `str.format` strings** (not `@`-templates): use `{i}`,
  `{i:03d}`, and any combo key by name — e.g. `tasks/{i:03d}-{TEMP}K/input.lmp`. Because
  the template path is also formatted, you can select a **different template per combo**.
- **Substitution is `safe_substitute`**: an `@VAR` the combo doesn't define is left in the
  file **verbatim, with no warning**. This is the most common way a sweep "succeeds" but
  produces a broken input — grep rendered files for stray `@[A-Z_]` (see
  [workflow-notes.md](workflow-notes.md)).
- Call `make_files` **once per file** a combo needs; each returns the chain so they stack
  (render `input.lmp`, `run.sh`, etc.). `--mode 755` for anything executable.
- `--extra_vars_from_file combos/{i}.json` loads extra substitution vars from a per-combo
  JSON file (pairs with `dump_combos`). `--ignore_error` logs and continues instead of raising.

### Other per-combo outputs

| Method | Signature | Effect |
| --- | --- | --- |
| `dump_combos` | `dump_combos '<pattern>' [--indent 2]` | write each combo to a JSON file |
| `print` | `print 'line' … [--file F] [--mode M]` | format lines per combo → stdout or a file |
| `run_cmd` | `run_cmd '<cmd>'` | run a shell command per combo; raises on non-zero exit |

- **`dump_combos`** pattern is per-combo, so it **must contain `{i}`** (e.g.
  `combos/{i:03d}.json`) or every combo overwrites the same file. Feed these back via
  `make_files --extra_vars_from_file`.
- **`print`** formats each given line for every combo. With `--file` it writes one file
  containing all combos' lines (not per-combo); without it, prints to stdout. Good for
  building a manifest.
- **`run_cmd`** formats the command per combo and runs it via the shell, e.g.
  `run_cmd 'cp {DATA} work/{i}/data.txt'`. Non-zero exit raises `RuntimeError`.

### Inspecting

- **`show_combos`** prints the expanded table (`@KEY: value` per combo). It **does not
  return the chain** — nothing may follow it, not even `done`.
- **`done`** ends the chain; **`done --debug`** prints the same table *and* still finishes,
  so you can inspect and render in one pass.

## Minimal example

```bash
omb combo \
    add_files DATA 'data/*.data' --abs - \
    add_var   TEMP 300 400 500 - \
    add_randint SEED -n 3 -a 1 -b 99999 - \
    broadcast SEED - \
    make_files 'tasks/{i:03d}-{TEMP}K/input.lmp' --template tmpl/input.lmp - \
    make_files 'tasks/{i:03d}-{TEMP}K/run.sh'    --template tmpl/run.sh --mode 755 - \
    done
```

3 data files × 3 temps = 9 combos, each with its own `SEED` (broadcast, so 9 not 27).
