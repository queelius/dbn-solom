# Toy DSL + Bounded‑Solomonoff Playground

A **minimal sandbox** for experimenting with resource‑bounded Solomonoff induction, DreamCoder‑style library growth, and DBN/particle‑filter inference, all inside a tiny stack‑based language.

---

## Modules

- `dsl_vm.py`: The stack‑based VM (soft caps, lazy wildcard sampling, `ARGk`, `SELECT`, `EQ`, sentinel overflow).
  
- `search.py`: Enumerative/beam synthesiser for multi‑example IO tasks; effectively the **bounded Solomonoff prior + exact MAP search**.

- `test_vm.py`: Unit tests & live cookbook: run with `python -m unittest -v`.

---

## Quick start

```bash
# Install nothing; pure std‑lib.
python -m unittest test_vm.py -v          # run & watch sample programs

# Synthesis: f(x)=x²+1 for x∈{2,3}
python search.py \
    --examples "[[2]->[5]] [[3]->[10]]" \
    --max-tokens 8 --beam 200 --no-wildcards
```

`search.py` flags:

* `--examples "[in]->[out] …"`  multiple pairs separated by spaces
* `--max-tokens N`               program length cap (defaults 12)
* `--beam K`                     prune queue to K states per depth (omit = DFS)
* `--no-wildcards`               forbid `CALL _` so every solution is deterministic
* `--seed S`                     make wildcard sampling repeatable

---

## Current DSL (rev 5)

| Category   | Tokens                       | Notes                                    |
| ---------- | ---------------------------- | ---------------------------------------- |
| Stack ops  | `DUP`, `SELECT`, `EQ`        | `SELECT` is ternary (cond a b ⇒ a/ b)    |
| Arithmetic | `ADD`, `SUB`, `MUL`, `NEG`\* | Plain 32‑bit ints; overflow → Python int |
| Literals   | `PUSH k` for k ∈ \[-2…5]     | Extend as needed                         |
| Inputs     | `ARG0…ARG{MAX_ARGS-1}`       | `MAX_ARGS` in `dsl_vm.py` (default 2)    |
| I/O        | `PRINT`                      | Output list equals observations          |
| Control    | `CALL f`, `CALL _`           | `_` lazily samples a body ≤12 tokens     |

*`NEG` not yet added; easy one‑liner if useful.*

Soft caps: stack ≤6, call depth ≤6 (editable constants).

---

## What works / what’s missing

* ✔ Deterministic VM & sentinel semantics keep state finite.
* ✔ Enumerative MAP search over bounded program space.
* ✔ Lazy wildcard sampling ≈ stochastic prior over libraries.
* ✔ Unit tests double as examples.
* ✘ **DBN / particle filter** posterior tracking is *not yet implemented*.
* ✘ No wake–sleep library learning (DreamCoder loop).
* ✘ No static analysis pruning / cost heuristics.
* ✘ No real evaluation of generalisation beyond given examples.

---

## Breadcrumbs / next milestones

1. **Particle filter prototype**
   *Dynamic latent*: `(Program P, VM config Cₜ)`
   *Observation*: token emitted at `PRINT`.
   Implement importance‑weight + resample every `PRINT`.
2. **Rao‑Blackwellise library**
   Integrate out unused wildcard bodies with CRP prior to cut variance.
3. **Wake–sleep library mining**
   After solving N tasks, compress frequent AST sub‑trees into named functions; update prior.
4. **Static pruning**
   Cheap computed bounds on max stack depth, impossible literals, etc., to kill huge parts of the search tree early.
5. **Extended primitives on demand**
   `NEG`, `SWAP`, `DIV`, etc.—only when an actual benchmark needs them.
6. **Benchmark suite**
   JSON/TOML file with \<inputs,out> pairs + timeouts to track progress.

---

### Design mantras

*Keep the DSL small.*  Every new opcode multiplies the search & inference cost.

*Bound everything.*  Soft caps + sentinel keep the DBN first‑order Markov.

*Iterate from MAP → SMC → wake‑sleep.*  Each stage feeds the next.

*Only add features when a task demands them.*  Premature generality is the enemy here.
