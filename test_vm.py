"""
Unittest suite that *also* prints each sample program, any library used, and the
resulting VM outputs.  This doubles as a live gallery of "useful" programs when
running `python -m unittest test_vm.py -v`.
"""
import unittest
from dsl_vm import VM, VMError, SENTINEL
from pprint import pprint


def show(name, program, inputs=None, library=None):
    vm = VM(library=library)
    out = vm.run(program, inputs=inputs)
    print(f"\n=== {name} ===")
    print("Prog:", program, "Inputs:", inputs, "→ Output:", out)
    if vm.library:
        print("Library:")
        pprint(vm.library)
    return out, vm.library


class TestDSLVM(unittest.TestCase):
    # --------------------------------------------------
    # 1. Primitive arithmetic / PRINT behaviour
    # --------------------------------------------------
    def test_addition(self):
        prog = [
            "PUSH 2",
            "PUSH 3",
            "ADD",
            "PRINT",
        ]
        out, _ = show("Addition", prog, None)
        self.assertEqual(out, [5])

    # --------------------------------------------------
    # 2. Library call re‑use (square = x*x)
    # --------------------------------------------------
    def test_square_library(self):
        library = {
            "square": ["DUP", "MUL"],
            "inc": ["PUSH 1", "ADD"],
        }
        prog = ["PUSH 4", "CALL square", "CALL inc", "PRINT"]
        out, _ = show("Square+Inc via Library", prog, None, library)
        self.assertEqual(out, [17])

    # --------------------------------------------------
    # 3. Soft stack overflow propagates SENTINEL, not crash
    # --------------------------------------------------
    def test_sentinel_overflow(self):
        prog = ["PUSH 0"] * 100 + ["PRINT"]
        out, _ = show("Soft Overflow", prog, None)
        self.assertEqual(out, [SENTINEL])

    # --------------------------------------------------
    # 4. Wildcard CALL creates a new function lazily
    # --------------------------------------------------
    def test_wildcard_call(self):
        vm = VM()  # fresh RNG
        prog = ["PUSH 1", "CALL _", "PRINT"]
        out, lib = show("Wildcard Call", prog, None)
        # Can't predict value, but library should now contain one function
        self.assertEqual(len(lib), 1)
        self.assertIn(out[-1], (SENTINEL, -2, -1, 0, 1, 2, 3, 4, 5))

    def test_indicator(self):
        # f(x) = 1 if x != 0 else 0 using SELECT
        prog = ["ARG0", "PUSH 1", "PUSH 0", "SELECT", "PRINT"]
        out0, _ = show("indicator(0)", prog, [0])
        out3, _ = show("indicator(3)", prog, [3])
        self.assertEqual(out0, [0])
        self.assertEqual(out3, [1])

if __name__ == "__main__":
    unittest.main(verbosity=2)
