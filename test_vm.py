# test_vm.py – unit tests for toy_dsl_vm
"""Quick unittest suite covering core behaviours of the bounded‑Solomonoff VM.

Run with:
    python -m unittest test_vm.py

If you prefer pytest, the same tests will be auto‑discovered.
"""
import unittest
from toy_dsl_vm import VM, VMError, SENTINEL


class TestToyDSLVM(unittest.TestCase):
    def setUp(self):
        # deterministic RNG for reproducibility
        self.vm = VM(rng=None)

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
        out = self.vm.run(prog)
        self.assertEqual(out, [5])

    # --------------------------------------------------
    # 2. Library call re‑use (square = x*x)
    # --------------------------------------------------
    def test_square_library(self):
        library = {
            "square": [
                "DUP",
                "MUL",
            ]
        }
        vm = VM(library=library)
        prog = [
            "PUSH 4",
            "CALL square",
            "PRINT",
        ]
        out = vm.run(prog)
        self.assertEqual(out, [16])

    # --------------------------------------------------
    # 3. Soft stack overflow propagates SENTINEL, not crash
    # --------------------------------------------------
    def test_sentinel_overflow(self):
        # PUSH 0 five times -> last push overwrites top with 'T'
        prog = ["PUSH 0"] * 5 + ["PRINT"]
        out = self.vm.run(prog)
        self.assertEqual(out, [SENTINEL])

    # --------------------------------------------------
    # 4. Wildcard CALL creates a new function lazily
    # --------------------------------------------------
    def test_wildcard_call(self):
        vm = VM()  # fresh RNG
        prog = [
            "PUSH 1",
            "CALL _",  # binds some random body
            "PRINT",
        ]
        out = vm.run(prog)
        # Can't predict value, but library should now contain one function
        self.assertEqual(len(vm.library), 1)
        self.assertEqual(out[-1] in (SENTINEL, -2, -1, 0, 1, 2, 3, 4, 5), True)

    # --------------------------------------------------
    # 5. Call‑stack cap raises VMError
    # --------------------------------------------------
    def test_call_depth_cap(self):
        deep_lib = {"f": ["CALL f"]}  # infinite recursion but will hit CALL_CAP first
        vm = VM(library=deep_lib)
        with self.assertRaises(VMError):
            vm.run(["CALL f"])


if __name__ == "__main__":
    unittest.main()
