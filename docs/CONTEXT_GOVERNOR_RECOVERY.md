# Context Governor Recovery

If work is interrupted, resume from the current `feat/context-governor-v6` GitHub state rather than assuming the local checkout is current.

## Safe checkpoint
The latest checkpoint commit is `c03e90c1c3b60113be698cd886a062a565a5e50a`.

## Completed
Context Governor v1, browser system-prompt document removal, browser history-result bounding, regression tests, and GitHub Actions CI are implemented. CI has passed.

## Do not change yet
Global context limits, history compression architecture, vision/screenshot handling, and Responses API state handling.

## Next milestone
Measure real browser-context token usage, inspect browser response formatting, improve structured observations, then design targeted artifact/reference retrieval.
