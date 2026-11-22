---
name: viva
description: Quiz me on a file or feature the way the Phitron examiner would. Read-only; never changes code.
argument-hint: "[file path or feature]"
disable-model-invocation: true
disallowed-tools: Edit Write
---

Act as a strict examiner for: $ARGUMENTS

1. Read the relevant code. Do not change anything.
2. In at most 8 lines, explain what it does, why it is designed this way, and what would break if its most important line were removed.
3. Ask me 5 questions, one at a time. Wait for each answer, grade it in one or two lines, and say what I missed.
4. Finish with the one thing I should revise before recording the video.
