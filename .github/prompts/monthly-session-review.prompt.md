---
name: Monthly Session Review
description: "Review available Copilot sessions for repeated friction and propose small, evidence-based configuration improvements without editing files."
argument-hint: "Optional time window or project scope"
agent: "agent"
---
Review the available Copilot session history for reusable improvements to this project's configuration.

1. First establish the available history scope: backend, number of sessions, date range, and any repository or device limitations. Do not claim to have reviewed sessions that are not available.
2. Look for repeated user corrections, retries, incomplete validation, recurring setup context, and successful patterns. Treat a behavior as recurring only when it appears in at least two independent sessions; a clear safety issue may be raised from one session.
3. Exclude credentials, tokens, private personal data, and raw transcript excerpts from recommendations. Summarize evidence minimally.
4. Read `config-allowlist.txt` and inspect only relevant allowlisted configuration. Do not read unrelated repositories or configuration files.
5. Recommend only small changes tied to concrete evidence. State the affected path, observed pattern, rationale, and a focused way to validate the change. Label one-off observations and incomplete history as provisional.
6. If a change is justified, provide a unified diff for review. Do not apply or save it. If no repeated improvement is supported, say so plainly.

Return history coverage and limitations, evidence-backed patterns, proposed diffs or an explicit no-change conclusion, and a short validation checklist.