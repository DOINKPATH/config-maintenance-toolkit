#!/usr/bin/env python3
"""Read-only checks for explicitly allowlisted personal configuration files."""

from __future__ import annotations

import argparse
import glob
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


MAX_FILE_BYTES = 1_000_000
FRONTMATTER_SUFFIXES = {".agent.md", ".instructions.md", ".prompt.md"}
SHELL_BASENAMES = {".bashrc", ".profile", "start-services", "start-code-server"}
FRONTMATTER_FIELD = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*):(?:\s*(.*))?$")


@dataclass
class Finding:
    level: str
    path: str
    message: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--home", type=Path, default=Path.home(), help="home directory containing the allowlist"
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        help="allowlist file (default: config-allowlist.txt beside this script)",
    )
    parser.add_argument(
        "--report",
        default="default",
        help="report path, or '-' for stdout (default: ~/.local/state/config-maintenance/latest-report.md)",
    )
    return parser.parse_args()


def is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def load_paths(manifest: Path, home: Path) -> tuple[list[Path], list[Finding]]:
    findings: list[Finding] = []
    paths: set[Path] = set()

    try:
        entries = manifest.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        return [], [Finding("ERROR", str(manifest), f"cannot read allowlist: {error}")]

    for line_number, raw_entry in enumerate(entries, start=1):
        entry = raw_entry.strip()
        if not entry or entry.startswith("#"):
            continue

        relative = Path(entry)
        if relative.is_absolute() or ".." in relative.parts:
            findings.append(
                Finding("ERROR", f"{manifest}:{line_number}", "allowlist entries must stay under home")
            )
            continue

        matches = glob.glob(str(home / entry), recursive=True)
        if not matches:
            findings.append(Finding("WARN", entry, "allowlist pattern matched no files"))
            continue

        for match in matches:
            path = Path(match).resolve()
            if not is_within(path, home):
                findings.append(Finding("ERROR", entry, "resolved path escapes home; skipped"))
                continue
            if path.is_file():
                paths.add(path)

    return sorted(paths), findings


def frontmatter_fields(text: str) -> tuple[dict[str, str], str | None]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, "missing opening frontmatter delimiter"

    try:
        end = next(index for index in range(1, len(lines)) if lines[index].strip() == "---")
    except StopIteration:
        return {}, "missing closing frontmatter delimiter"

    fields: dict[str, str] = {}
    for line in lines[1:end]:
        if not line.strip() or line.lstrip().startswith("#") or line[:1].isspace():
            continue
        match = FRONTMATTER_FIELD.match(line)
        if not match:
            return fields, f"unsupported frontmatter line: {line.strip()}"
        key, value = match.groups()
        if key in fields:
            return fields, f"duplicate frontmatter key: {key}"
        fields[key] = (value or "").strip().strip("\"'")

    if not fields.get("description"):
        return fields, "frontmatter requires a non-empty description"
    return fields, None


def check_file(path: Path, home: Path) -> list[Finding]:
    relative = path.relative_to(home).as_posix()
    findings: list[Finding] = []

    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            return [Finding("ERROR", relative, f"file exceeds {MAX_FILE_BYTES} byte audit limit")]
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        return [Finding("ERROR", relative, f"cannot read as UTF-8: {error}")]

    lower_name = path.name.lower()
    if lower_name.endswith((".json", ".code-snippets")):
        try:
            json.loads(text)
        except json.JSONDecodeError as error:
            findings.append(Finding("ERROR", relative, f"invalid JSON at line {error.lineno}"))

    if any(lower_name.endswith(suffix) for suffix in FRONTMATTER_SUFFIXES):
        _, error = frontmatter_fields(text)
        if error:
            findings.append(Finding("ERROR", relative, error))

    if path.suffix in {".sh", ".bash"} or path.name in SHELL_BASENAMES:
        try:
            result = subprocess.run(
                ["bash", "-n", str(path)], capture_output=True, text=True, check=False
            )
        except OSError as error:
            findings.append(Finding("WARN", relative, f"bash syntax check unavailable: {error}"))
        else:
            if result.returncode:
                findings.append(Finding("ERROR", relative, "bash syntax check failed"))

    if not findings:
        findings.append(Finding("OK", relative, "checks passed"))
    return findings


def check_unique_agent_names(paths: list[Path], home: Path) -> list[Finding]:
    findings: list[Finding] = []
    names: dict[str, Path] = {}
    for path in paths:
        if not path.name.lower().endswith(".agent.md"):
            continue
        try:
            fields, error = frontmatter_fields(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError):
            continue
        name = fields.get("name", "").strip()
        if error or not name:
            continue
        key = name.casefold()
        previous = names.get(key)
        if previous:
            findings.append(
                Finding(
                    "ERROR",
                    path.relative_to(home).as_posix(),
                    f"agent name duplicates `{previous.relative_to(home).as_posix()}`",
                )
            )
        else:
            names[key] = path
    return findings


def render_report(findings: list[Finding], file_count: int) -> str:
    errors = sum(item.level == "ERROR" for item in findings)
    warnings = sum(item.level == "WARN" for item in findings)
    lines = [
        "# Configuration audit",
        "",
        f"Audited files: {file_count} | Errors: {errors} | Warnings: {warnings}",
        "",
        "This report checks only allowlisted paths. No audited configuration was modified.",
        "",
        "| Status | Path | Finding |",
        "| --- | --- | --- |",
    ]
    for item in findings:
        message = item.message.replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {item.level} | `{item.path}` | {message} |")
    if not findings:
        lines.append("| OK | - | No allowlisted files found |")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    home = args.home.expanduser().resolve()
    manifest = args.manifest or Path(__file__).with_name("config-allowlist.txt")
    manifest = manifest.expanduser().resolve()

    paths, findings = load_paths(manifest, home)
    for path in paths:
        findings.extend(check_file(path, home))
    findings.extend(check_unique_agent_names(paths, home))

    report = render_report(findings, len(paths))
    if args.report == "-":
        sys.stdout.write(report)
    else:
        destination = (
            home / ".local/state/config-maintenance/latest-report.md"
            if args.report == "default"
            else Path(args.report).expanduser()
        )
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(report, encoding="utf-8")
        except OSError as error:
            print(f"cannot write report: {error}", file=sys.stderr)
            return 2
        print(f"Wrote {destination}")

    return 1 if any(item.level == "ERROR" for item in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())