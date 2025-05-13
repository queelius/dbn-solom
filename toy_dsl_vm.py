# toy_dsl_vm.py  – bounded‑Solomonoff VM with soft stack cap
"""Minimal stack‑based DSL + virtual machine, **rev 3**
====================================================
Changes from rev 2 → rev 3
-------------------------
* **Soft overflow sentinel** – pushing onto a full stack no longer raises; instead the
  top element is overwritten with the special value `'T'`.  Arithmetic involving `'T'`
  propagates the sentinel (`a ⊗ T  →  T`).  This guarantees execution never crashes
  even when randomly‑sampled bodies exceed `STACK_CAP`.
* Constants are left unchanged (`STACK_CAP = 4`) so the DBN state space is still
  finite and small.
"""
from __future__ import annotations

import random
import itertools
from typing import List, Dict, Tuple, Optional
from collections import defaultdict

# ----------------------------------------
# Configuration / caps
# ----------------------------------------
STACK_CAP = 4      # max items kept verbatim on data stack
CALL_CAP = 4       # max call‑stack depth
BODY_MAX_TOKENS = 12  # upper bound for any function body
SENTINEL = "T"      # symbol used when stack overflows or arithmetic touches unknowns

# ----------------------------------------
# Primitive token universe
# ----------------------------------------
PRIMITIVES = [
    "DUP",
    "ADD",
    "SUB",
    "MUL",
    "PRINT",
] + [f"PUSH {n}" for n in range(-2, 6)]  # small integer literals

# Global cache to deduplicate compiled bodies across VM instances
_GLOBAL_BODY_CACHE: Dict[Tuple[str, ...], List[str]] = {}


class VMError(Exception):
    """Raised on invalid instruction, call‑stack cap overflow, or step overflow."""


class VM:
    """Tiny stack‑based virtual machine with lazy library growth and soft caps."""

    _auto_uid_iter = itertools.count()

    def __init__(self, library: Optional[Dict[str, List[str]]] = None, *, rng: Optional[random.Random] = None):
        self.library: Dict[str, List[str]] = library.copy() if library else {}
        self.stack: List[object] = []          # may hold ints or SENTINEL
        self.output: List[object] = []
        self.frames: List[Tuple[List[str], int]] = []  # (program, ip)
        self.rng = rng or random.Random()

    # ----------------------------------------------------
    # Public API
    # ----------------------------------------------------
    def run(self, program: List[str], *, max_steps: int = 1000) -> List[object]:
        """Execute *program*; returns list of emitted outputs (ints or 'T')."""
        self.stack.clear()
        self.output.clear()
        self.frames = [(program, 0)]
        steps = 0
        while self.frames:
            if steps >= max_steps:
                raise VMError("Step limit exceeded")
            prog, ip = self.frames[-1]
            if ip >= len(prog):
                # return from function
                self.frames.pop()
                continue
            instr = prog[ip]
            self.frames[-1] = (prog, ip + 1)
            self._exec(instr)
            steps += 1
        return list(self.output)

    # ----------------------------------------------------
    # Internal helpers
    # ----------------------------------------------------
    def _exec(self, instr: str) -> None:
        parts = instr.split()
        op = parts[0]
        if op == "PUSH":
            if len(parts) != 2:
                raise VMError("PUSH expects one argument")
            self._push(int(parts[1]))
        elif op == "DUP":
            self._require_stack(1)
            self._push(self.stack[-1])
        elif op == "ADD":
            self._binary(lambda a, b: a + b)
        elif op == "SUB":
            self._binary(lambda a, b: a - b)
        elif op == "MUL":
            self._binary(lambda a, b: a * b)
        elif op == "PRINT":
            self._require_stack(1)
            self.output.append(self.stack[-1])
        elif op == "CALL":
            if len(parts) != 2:
                raise VMError("CALL expects function name")
            self._call(parts[1])
        else:
            raise VMError(f"Invalid instruction '{instr}'")

    # ---------------- internal stack helpers ----------------
    def _push(self, val: object):
        if len(self.stack) >= STACK_CAP:
            # overflow → overwrite top with SENTINEL
            self.stack[-1] = SENTINEL
        else:
            self.stack.append(val)

    def _binary(self, func):
        self._require_stack(2)
        b = self.stack.pop()
        a = self.stack.pop()
        if isinstance(a, int) and isinstance(b, int):
            self._push(func(a, b))
        else:
            # propagate uncertainty
            self._push(SENTINEL)

    def _require_stack(self, n: int):
        if len(self.stack) < n:
            raise VMError("Stack underflow")

    # ---------------- call / library handling ---------------
    def _call(self, fname: str):
        if len(self.frames) >= CALL_CAP:
            raise VMError("Call‑stack cap exceeded")

        if fname not in self.library:
            # Unknown → treat as wildcard → lazily sample & bind
            body = self._sample_body()
            self.library[fname] = body
        self.frames.append((self.library[fname], 0))

    def _sample_body(self) -> List[str]:
        length = self.rng.randint(1, BODY_MAX_TOKENS)
        body_src = [self.rng.choice(PRIMITIVES) for _ in range(length)]
        key = tuple(body_src)
        if key not in _GLOBAL_BODY_CACHE:
            _GLOBAL_BODY_CACHE[key] = body_src
        return _GLOBAL_BODY_CACHE[key]


# --------------------------------------------------------
# Example usage / smoke test
# --------------------------------------------------------
if __name__ == "__main__":
    rng = random.Random(0)  # deterministic sample

    main_program = [
        "PUSH 2",
        "PUSH 3",
        "CALL _",  # lazily samples a body that may exceed the stack cap
        "PRINT",
    ]

    vm = VM(rng=rng)
    out = vm.run(main_program)
    print("Output:", out)
    print("Library bindings:")
    for name, body in vm.library.items():
        print(f"  {name} -> {body}")
