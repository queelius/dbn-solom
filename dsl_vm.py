# toy_dsl_vm.py – bounded‑Solomonoff VM with ARG tokens (rev 4)
"""Minimal stack‑based DSL + VM.
New in **rev 4**
----------------
* Supports **function inputs** via `ARG0`, `ARG1`, … tokens.
* `VM.run()` now accepts an `inputs` list.  Each `ARGk` pushes `inputs[k]` (or 0
  if missing) onto the data stack.
* Retains soft stack cap, lazy wildcard sampling, and sentinel semantics.
"""
from __future__ import annotations
import random, itertools
from typing import List, Dict, Tuple, Optional

# ------------------------------- Config -------------------------------
STACK_CAP = 6     # data‑stack depth cap
CALL_CAP  = 6     # call‑stack depth cap
BODY_MAX_TOKENS = 12
MAX_ARGS  = 2     # expose ARG0‑ARG2
SENTINEL  = "T"   # overflow / unknown value marker

# ------------------------------ Primitives ---------------------------
PRIMITIVES = (
    ["DUP", "ADD", "SUB", "MUL", "PRINT", "SELECT", "EQ"] +
    [f"PUSH {n}" for n in range(-2, 6)] +
    [f"ARG{i}" for i in range(MAX_ARGS)]
)

_GLOBAL_BODY_CACHE: Dict[Tuple[str, ...], List[str]] = {}

class VMError(Exception):
    pass

# --------------------------- Virtual Machine -------------------------
class VM:
    """Tiny stack‑based VM with soft caps and lazy library growth."""

    _auto_uid = itertools.count()

    def __init__(self, library: Optional[Dict[str, List[str]]] = None, *, rng: Optional[random.Random] = None):
        self.library: Dict[str, List[str]] = library.copy() if library else {}
        self.rng   = rng or random.Random()
        self.stack: List[object] = []
        self.output: List[object] = []
        self.frames: List[Tuple[List[str], int]] = []
        self.inputs: List[int]  = []  # current call inputs

    # --------------------------- Public API ---------------------------
    def run(self, program: List[str], *, inputs: Optional[List[int]] = None, max_steps: int = 1000) -> List[object]:
        self.stack.clear(); self.output.clear(); self.frames = [(program, 0)]
        self.inputs = list(inputs or [])
        steps = 0
        while self.frames:
            if steps >= max_steps:
                raise VMError("Step limit exceeded")
            prog, ip = self.frames[-1]
            if ip >= len(prog):
                self.frames.pop(); continue
            instr = prog[ip]; self.frames[-1] = (prog, ip + 1)
            self._exec(instr); steps += 1
        return list(self.output)

    # -------------------------- Instruction set -----------------------
    def _exec(self, instr: str):
        parts = instr.split(); op = parts[0]
        if op == "PUSH":
            self._push(int(parts[1]))
        elif op == "DUP":
            self._require_stack(1); self._push(self.stack[-1])
        elif op in {"ADD", "SUB", "MUL"}:
            fn = {"ADD": lambda a,b:a+b, "SUB": lambda a,b:a-b, "MUL": lambda a,b:a*b}[op]
            self._binary(fn)
        elif op == "PRINT":
            self._require_stack(1); self.output.append(self.stack[-1])
        elif op == "CALL":
            self._call(parts[1])
        elif op.startswith("ARG"):
            idx = int(op[3:])
            val = self.inputs[idx] if idx < len(self.inputs) else 0
            self._push(val)
        elif op == "SELECT":
            self._require_stack(3)
            b = self.stack.pop()
            a = self.stack.pop()
            cond = self.stack.pop()
            self._push(a if (isinstance(cond,int) and cond!=0) else b)
        elif op == "EQ":
            self._require_stack(2)
            b = self.stack.pop()
            a = self.stack.pop()
            self._push(1 if (isinstance(a,int) and isinstance(b,int) and a==b) else 0)
        else:
            raise VMError(f"Bad op {op}")

    # --------------------------- Helpers ------------------------------
    def _push(self, val):
        if len(self.stack) >= STACK_CAP:
            self.stack[-1] = SENTINEL
        else:
            self.stack.append(val)

    def _binary(self, func):
        self._require_stack(2)
        b=self.stack.pop(); a=self.stack.pop()
        self._push(func(a,b) if isinstance(a,int) and isinstance(b,int) else SENTINEL)

    def _require_stack(self, n):
        if len(self.stack) < n:
            raise VMError("Stack underflow")

    def _call(self, fname):
        if len(self.frames) >= CALL_CAP:
            raise VMError("Call depth cap")
        if fname not in self.library:
            self.library[fname] = self._sample_body()
        self.frames.append((self.library[fname], 0))

    def _sample_body(self):
        body = [self.rng.choice(PRIMITIVES) for _ in range(self.rng.randint(1, BODY_MAX_TOKENS))]
        key = tuple(body)
        if key not in _GLOBAL_BODY_CACHE:
            _GLOBAL_BODY_CACHE[key] = body
        return _GLOBAL_BODY_CACHE[key]

# --------------------------- Smoke test ------------------------------
if __name__ == "__main__":
    vm = VM(rng=random.Random(0))
    prog = ["ARG0","DUP","MUL","PUSH 1","ADD","PRINT"]  # f(x)=x^2+1
    for x in (2,3):
        out = vm.run(prog, inputs=[x])
        print(f"f({x}) ->", out)
