# search.py – enumerative synthesis with examples support (rev 4)
"""Multi‑example IO synthesis for the toy DSL VM.

Fixes parsing so both `[[2]->[5]]` and `[2]->[5]` syntaxes work.
Usage examples:
    # Synthesise f(x)=x^2+1 for x∈{2,3}
    python search.py --examples "[[2]->[5]] [[3]->[10]]" --max-tokens 8 --beam 200 --no-wildcards
"""
from __future__ import annotations
import argparse, random, re
from collections import deque
from typing import List, Tuple
from dsl_vm import VM, VMError, PRIMITIVES

# matches  [2]->[5]   or  [[2]->[5]] (extra brackets optional)
EX_RE = re.compile(r"\[+\s*(.*?)\s*\]+\s*->\s*\[+\s*(.*?)\s*\]+")


def parse_examples(s: str) -> List[Tuple[List[int], List[int]]]:
    examples: List[Tuple[List[int], List[int]]] = []
    for match in EX_RE.finditer(s):
        raw_in = match.group(1).strip()
        raw_out = match.group(2).strip()
        ins = [int(x) for x in re.split(r"\s*,\s*", raw_in) if x]
        outs = [int(x) for x in re.split(r"\s*,\s*", raw_out) if x]
        examples.append((ins, outs))
    if not examples:
        raise ValueError("No examples parsed; expected format [in]->[out]")
    return examples


def run_vm(program: List[str], inputs: List[int], rng: random.Random) -> List[object] | None:
    """Execute program with *inputs*. Returns output list or None on VMError."""
    try:
        vm = VM(rng=rng)
        vm.run(program, inputs=inputs)
        return vm.output
    except VMError:
        return None


def prefix_ok(program: List[str], examples, rng_master) -> bool:
    for inp, exp in examples:
        rng = random.Random(rng_master.randint(0, 2**32 - 1))
        out = run_vm(program, inp, rng)
        if out is None:  # VMError
            return False
        # compare prefix
        if any(o != e for o, e in zip(out, exp)):
            return False
    return True


def candidate_ok(program: List[str], examples, rng_master) -> bool:
    for inp, exp in examples:
        rng = random.Random(rng_master.randint(0, 2**32 - 1))
        out = run_vm(program, inp, rng)
        if out != exp:
            return False
    return True


def enumerate_programs(examples, *, max_tokens, beam, allow_wildcards, seed):
    rng_master = random.Random(seed)
    queue = deque([([], random.Random(rng_master.randint(0, 2**32 - 1)))])
    solutions = []

    while queue:
        if beam and len(queue) > beam:
            while len(queue) > beam:
                queue.pop()
        prog, state_rng = queue.popleft()

        if candidate_ok(prog, examples, state_rng):
            solutions.append(prog)
            continue
        if len(prog) >= max_tokens:
            continue

        token_space = PRIMITIVES if not allow_wildcards else PRIMITIVES + ["CALL _"]
        for tok in token_space:
            child_prog = prog + [tok]
            if prefix_ok(child_prog, examples, state_rng):
                queue.appendleft((child_prog, random.Random(state_rng.randint(0, 2**32 - 1))))
    return solutions


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--examples', type=str, required=True, help='e.g. "[[2]->[5]] [[3]->[10]]"')
    ap.add_argument('--max-tokens', type=int, default=12)
    ap.add_argument('--beam', type=int, default=None)
    ap.add_argument('--no-wildcards', action='store_true')
    ap.add_argument('--seed', type=int, default=None)
    args = ap.parse_args()

    examples = parse_examples(args.examples)
    sols = enumerate_programs(
        examples,
        max_tokens=args.max_tokens,
        beam=args.beam,
        allow_wildcards=not args.no_wildcards,
        seed=args.seed,
    )

    if not sols:
        print('No solutions.')
    else:
        print(f'Found {len(sols)} solution(s):')
        for i, p in enumerate(sols[:20], 1):
            print(f'[{i}]', p)


if __name__ == '__main__':
    main()
