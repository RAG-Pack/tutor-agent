---
name: colab-lesson
description: Teach an idea hands-on by building a short Colab notebook in the student's browser, with explanations and example code cells they can run and change.
---

# Colab lesson

A notebook lets the student run the idea, not just read about it. Build a short one in
their browser, check that every example runs, then hand it over with an exercise.

## 1. Connect

Call `open_colab_browser_connection`. It opens a Colab notebook in a new tab of the
student's browser and waits up to 60 seconds for that tab to connect.

- `true`: you now have the notebook tools (`add_text_cell`, `add_code_cell`,
  `run_code_cell`, `get_cells`, `update_cell`, ...).
- `false`: tell the student a Colab tab opened in their browser, and ask them to allow
  the connection there (and sign in to Google if it asks), then say when it's done.
  Call it again when they do.

If you don't have `open_colab_browser_connection` at all, this tutor was started
without Colab: teach with a short code block in the chat instead.

## 2. Plan three small steps

Three steps, each showing one piece of the idea and building on the one before: the
whole lesson then takes about 15 tool calls, and fits in one reply. Use the course's
terms (`TinyAgent`, `LLM`, `Memory`, `messages`). Keep every example runnable in a few
seconds on a plain CPU runtime, with the standard library and `numpy`: when the idea is
about the harness (message history, tool calls, the loop), stand in for the model with
a small Python function that returns a fixed reply, so no model or API key is needed.

## 3. Build it, checking each example

Call `get_cells` once to see how many cells the notebook has. Add every new cell at the
end: its `cellIndex` is the number of cells so far, one more after each cell you add.

For each step:

1. `add_text_cell`: a `### ` heading and one to three sentences on what to notice.
2. `add_code_cell` (`language`: `"python"`): 3 to 15 lines, with a comment on the key line.
3. `run_code_cell` with the new cell's id. If the output shows an error, fix the code
   with `update_cell` and run it again, so every example works when the student gets it.

The first `run_code_cell` takes a few extra seconds while Colab starts a runtime.

## 4. End with an exercise

Finish with two more cells, so the student has somewhere to write:

1. `add_text_cell`: `### Try it` and one small task that changes or extends the last
   example.
2. `add_code_cell`: starter code for that task, with a `# TODO` line where the
   student's code goes. Leave this cell unrun: it's theirs.

## 5. Hand it over

In the chat, in a few lines: the notebook is ready in the Colab tab, what each step
shows, and what the exercise asks. Ask them to try it and tell you when they've run it;
then read their cell and its output with `get_cells` (`includeOutputs`: true) and give
feedback. To keep the notebook, they can use **File → Save a copy in Drive**.
