# Configuration Maintenance Toolkit

**Feedback preview.** This project contains focused Copilot agents and a read-only configuration audit utility. It is not a production release. The audit reports syntax and metadata issues; the Config Curator proposes changes but never applies them.

The repository is not affiliated with or endorsed by GitHub or Microsoft. No license is included yet; public visibility does not grant permission to reuse or resell this material.

## Run

From the repository root, copy and adapt the example allowlist:

```sh
cp config-allowlist.example.txt config-allowlist.txt
python3 audit.py --home "$PWD" --manifest "$PWD/config-allowlist.txt" --report -
```

To save the report outside the repository:

```sh
mkdir -p "$HOME/.local/state/config-maintenance"
python3 audit.py --home "$PWD" --manifest "$PWD/config-allowlist.txt" --report "$HOME/.local/state/config-maintenance/latest-report.md"
```

Run the tests with:

```sh
python3 -B -m unittest discover -s tests -v
```

The audit uses only Python's standard library and Bash. It checks JSON syntax, basic YAML frontmatter fields and unique agent names for Copilot customization files, and Bash syntax for allowlisted shell files. It does not evaluate whether prose is current or semantically correct.

## Scope

Edit `config-allowlist.txt` to opt files in or out. Entries are relative to the root passed with `--home`; absolute paths, parent traversal, and symlinks resolving outside that root are rejected. Keep this personalized file out of Git; it is ignored by `.gitignore`. The example covers workspace agents and prompts. Add other config paths only when you use them and control them, and exclude credentials, raw session logs, generated files, and dependency or vendor trees.

Review the report, then invoke **Config Curator** to prepare a proposed diff. Review and apply changes yourself. Do not treat the audit as an automatic upgrade mechanism.

## Widget and weekly run

The agents and prompt are workspace-scoped under `.github/agents/` and `.github/prompts/`. To install them as personal agents instead, copy the `.agent.md` files to your VS Code profile's `agents/` folder and the prompt to its `prompts/` folder. This preview does not install a scheduler; configure one separately if desired, and make it run only the audit command.

## Session learning

Run `/monthly-session-review` when session history is available. Promote a lesson into shared configuration only after it appears in at least two independent sessions, except for a clear safety issue. Record only short, sanitized lessons; do not copy credentials or raw transcripts into this project. The prompt generates recommendations only; it does not edit files.
