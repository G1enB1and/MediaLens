import traceback
import sys
from tests.test_hashing_and_moves import TestHashingAndMoves
import unittest

suite = unittest.TestSuite()
suite.addTest(TestHashingAndMoves('test_detect_move_by_hash'))
result = unittest.TestResult()

try:
    suite.run(result)
    for failure in result.failures:
        print(f"FAILURE: {failure[0]}")
        print(failure[1])
    for error in result.errors:
        print(f"ERROR: {error[0]}")
        print(error[1])
    if result.wasSuccessful():
        print("SUCCESS")
except Exception:
    traceback.print_exc()
