"""Ask the tutor questions from the command line, and print every step.

Each argument is one message in the same conversation:

    uv run python scripts/ask.py "What was the headlight analogy?" "Where's that in the video?"
"""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tutor.build import build_tutor  # noqa: E402

agent = build_tutor()

for question in sys.argv[1:]:
    task = f"[{datetime.now().astimezone():%Y-%m-%d %H:%M %Z}] {question}"
    print(f"\n### User: {task}")
    agent.start(task)
    for step in agent.steps(max_steps=8):
        tokens = f"({step.metadata['prompt_tokens']:,} prompt, {step.metadata['cached_tokens']:,} cached, " \
                 f"{step.metadata['completion_tokens']:,} completion tokens)"
        if step.action is not None:
            print(f"\n--- Tool: {step.action['tool']}({step.action['kwargs']}) {tokens}")
            print(step.observation[:1200] + (" ..." if len(step.observation) > 1200 else ""))
        else:
            print(f"\n### Tutor {tokens}:\n{step.answer}")
