# ADR-005: Testing Strategy

## Status
Accepted

## Context
Every bug fix should be provable. A regression test that fails before the fix
and passes after is the strongest signal that the fix is correct.

## Decision
Adopt the FAIL_TO_PASS pattern for non-trivial bug fixes:
1. Write a test that reproduces the bug (fails).
2. Commit the test.
3. Fix the bug.
4. Verify the test passes.
5. Merge both together.

## Consequences
### Positive
- Every fixed bug has a permanent regression test
- Reviewers can verify fixes by running tests
### Negative
- Slightly longer PRs
- Requires discipline to write tests first
