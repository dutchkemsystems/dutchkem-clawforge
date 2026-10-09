# FAIL_TO_PASS Test Pattern

This directory demonstrates the FAIL_TO_PASS pattern used to verify real bug
fixes. Each test here asserts the *correct* behaviour of code. When the test
file is first added against unfixed code, it fails (red). After the fix is
merged, it passes (green).

See ADR-005 for how this fits into the overall testing strategy.
