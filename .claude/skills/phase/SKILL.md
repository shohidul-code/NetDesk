---
name: phase
description: Plan and build one phase of the NetDesk roadmap (docs/PROPOSAL.md section 16), with tests, a gate check and viva notes.
argument-hint: "[phase-number 0-10]"
disable-model-invocation: true
---

# Phase $ARGUMENTS

We are doing **Phase $ARGUMENTS** of `docs/PROPOSAL.md` §16, and nothing from any other phase.

## 1. Plan, then stop

1. Read `CLAUDE.md`, the Phase $ARGUMENTS block in §16, and every PROPOSAL section it relies on: §7 for tables, §8 for endpoints, §9 for AI, §10 for security, §12 for infrastructure, §13 for tests.
2. Look at the code that already exists for this phase.
3. Reply in at most 15 lines:
   - what already exists and works;
   - the tasks, in order, with the files each one adds or changes;
   - the tests you will write;
   - anything in the proposal that is unclear, wrong, or in conflict with the code.
4. Stop and wait for me to say "go". Do not edit files yet.

## 2. Build one task at a time

For each task:

1. Write or update the tests first when the behaviour can be tested.
2. Make the smallest change that makes them pass.
3. Run `uv run ruff check . && uv run ruff format --check . && uv run mypy app && uv run pytest -q`. In phase 7, run the frontend's lint, typecheck and build instead.
4. Fix failures. Never weaken, skip or `xfail` a test to make it pass.
5. Stop and give me a 3-line summary, the changed files, and a conventional commit message. Wait while I review the diff and commit.

## 3. Gate

When every task is done, check each "Done when" item of Phase $ARGUMENTS. Report each one as PASS or FAIL, with the exact command you ran and a short piece of its output. Never write PASS without running the check.

## 4. Viva notes

Write `docs/learning/phase-$ARGUMENTS.md` containing:

- what was built and why, in at most 10 bullets;
- the 5 code locations I must be able to explain, as `path:line` plus one sentence each;
- 5 likely viva questions with short model answers;
- the rows of the rubric matrix (PROPOSAL §4) that this phase completes, so I can update their status.

If the proposal turns out to be wrong, or a library works differently than written, stop and tell me instead of improvising.
