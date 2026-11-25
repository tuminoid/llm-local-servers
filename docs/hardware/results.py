"""Import measured results per hardware and render them into its page.

docs/hardware/<slug>.json is the one source of a hardware's results: one
record per profile, a session part and a capability part, each the harness's
own row projection (`--show FILE --format row`) of a retained document, plus
hand-set fields an import never touches. docs/hardware/<slug>.md is
hand-written prose with the tables rendered between markers; `make test`
fails when a table is stale.

    results.py import <slug> <retained JSON>   add or replace one part
    results.py render                          rewrite every page's tables
"""

import json
from pathlib import Path
import re
import subprocess
import sys

REPO = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent

# Hand-set per profile; an import creates them empty and never overwrites them.
HAND = ("role", "tier", "engine", "campaign", "note")
ROLES = ("audit", "interactive")

# Retained document protocol: record part and the harness module projecting it.
PARTS = {"audit-v2": ("session", "audit_bench"),
         "capability-v3": ("capability", "capability_check")}

# Runtime directory: the name a reader knows it by.
RUNTIMES = {"vllm": "vLLM", "vllm-metal": "vLLM-Metal", "splash": "Splash", "lmstudio": "LM Studio",
            "ollama": "Ollama", "ds4": "ds4", "kapitsa": "Kapitsa", "strata": "Strata"}

# Harness runtime name -> runtime directory, where they differ.
DIRECTORIES = {"vllm-cuda": "vllm"}

MARKER = re.compile(r"(<!-- results:(\w+) -->\n).*?(<!-- /results:\2 -->)", re.S)


def load(slug: str) -> dict:
    path = HERE / f"{slug}.json"
    return json.loads(path.read_text()) if path.exists() else {"profiles": {}}


def save(slug: str, records: dict) -> None:
    (HERE / f"{slug}.json").write_text(json.dumps(records, indent=2, sort_keys=True) + "\n")


def project(file: str) -> tuple[str, dict]:
    """The harness's row of one retained document, through its public CLI.

    FILE is a path or a name as `--list` prints it, which only the harness
    resolves, so each harness is asked in turn.
    """
    errors = []
    for part, module in PARTS.values():
        done = subprocess.run([sys.executable, "-m", module, "--show", file, "--format", "row"],
                              capture_output=True, text=True)
        if not done.returncode:
            return part, json.loads(done.stdout)
        errors.append(done.stderr.strip() or f"{module} --show failed")
    sys.exit("\n".join(errors))


def import_row(slug: str, file: str) -> None:
    if not (HERE / f"{slug}.md").exists():
        sys.exit(f"no page docs/hardware/{slug}.md; write the page before importing into it")
    part, row = project(file)
    runtime = DIRECTORIES.get(row["runtime"], row["runtime"])
    conf = REPO / runtime / "models" / f"{row['tag']}.conf"
    if not conf.exists():
        sys.exit(f"{file}: no model config {conf.relative_to(REPO)} for tag {row['tag']!r}")
    records = load(slug)
    key = f"{runtime}/{row['tag']}"
    record = records["profiles"].setdefault(key, {field: None for field in HAND})
    # A profile's two rows describe one artifact: a row for another identity
    # makes the other part stale, so it is dropped until that artifact is
    # measured again.
    other = "capability" if part == "session" else "session"
    if record.get(other) and record[other]["model_identity"] != row["model_identity"]:
        print(f"{slug}: {key} {other} {record[other]['artifact']} dropped: it measured "
              f"{record[other]['model_identity']}, not {row['model_identity']}")
        record[other] = None
    old = record.get(part)
    record[part] = row
    save(slug, records)
    print(f"{slug}: {key} {part} " + (f"{old['artifact']} -> " if old else "") + row["artifact"])


# --- rendering ---

def number(value, places: int) -> str:
    return "--" if value is None else f"{value:,.{places}f}"


def streams_text(streams: dict, field: str, places: int, skip=None) -> str:
    cells = [f"{count}x {number(section[field], places)}"
             for count, section in sorted(streams.items(), key=lambda item: int(item[0]))
             if count != skip]
    return ", ".join(cells) or "--"


def at_1x(session: dict, field: str, places: int) -> str:
    section = session["streams"].get("1")
    return number(section[field], places) if section else "--"


def complete(session: dict) -> str:
    cells = [(count, f"{section['sessions'] - section['sessions_incomplete']}/{section['sessions']}")
             for count, section in sorted(session["streams"].items(), key=lambda item: int(item[0]))]
    return cells[0][1] if len(cells) == 1 else ", ".join(f"{count}x {text}" for count, text in cells)


def kv_pool(runtime: str, session: dict) -> str:
    # Ollama exposes no fungible pool: its figure is the allocation, never a pool size.
    text = number(session["kv_pool_tokens"], 0)
    return f"{text} allocated" if runtime == "ollama" else text


def reference(session: dict) -> str:
    ref = session["reference"]
    return f"{number(ref['pp512'], 0)} / {number(ref['tg128'], 1)}" if ref else "unavailable"


def publishable(session: dict) -> str:
    reasons = ", ".join(session["publication_reasons"])
    return "yes" if session["publishable"] else f"no ({reasons})" if reasons else "no"


def best(session: dict) -> float | None:
    optimal = session["optimal_streams"]
    return session["streams"][str(optimal)]["sessions_per_hour"] if optimal else None


def ranked(record: dict) -> bool:
    session, capability = record.get("session"), record.get("capability")
    return bool(session and capability and capability["status"] == "passed"
                and session["publishable"] and session["optimal_streams"])


def score(capability: dict | None) -> str:
    if not capability:
        return "--"
    aptitude = capability["audit_aptitude"]
    if not aptitude.get("scored"):
        return "not scored"
    low, high = aptitude["interval"]
    return f"{aptitude['vuln_score']:+.2f} [{low:+.2f}, {high:+.2f}]"


def table(headers: list[str], rows: list[list[str]]) -> list[str]:
    align = ["--:" if header in NUMERIC else "--" for header in headers]
    return ["| " + " | ".join(row) + " |" for row in (headers, align, *rows)]


NUMERIC = {"Rank", "Context", "Slots", "KV pool", "Best sessions/h", "Out tok/session 1x",
           "Prefill tok/s 1x", "Report decode 1x"}


def session_cells(key: str, record: dict) -> list[str]:
    session = record["session"]
    runtime, profile = key.split("/", 1)
    return [f"`{profile}`", RUNTIMES[runtime], record["engine"], record["tier"],
            number(session["configured_context"], 0), str(session["active_slots"]),
            kv_pool(runtime, session)]


def session_tail(session: dict) -> list[str]:
    return [complete(session), at_1x(session, "output_tokens_per_session", 0),
            at_1x(session, "prefill_tokens_per_second", 1),
            at_1x(session, "report_decode_tokens_per_second", 1), reference(session),
            publishable(session), f"`{session['artifact']}`"]


def notes(keys: list[str], profiles: dict) -> list[str]:
    lines = [f"- `{key.split('/', 1)[1]}`: {profiles[key]['note']}" for key in keys
             if profiles[key]["note"]]
    return ["", *lines] if lines else []


def audit_table(profiles: dict) -> list[str]:
    keys = [key for key, record in profiles.items() if record["role"] == "audit"]
    order = sorted(keys, key=lambda key: (not ranked(profiles[key]),
                                          -(best(profiles[key]["session"]) or 0)
                                          if profiles[key].get("session") else 0, key))
    rows, rank = [], 0
    for key in order:
        record = profiles[key]
        session = record.get("session")
        if ranked(record):
            rank += 1
        head = [str(rank) if ranked(record) else "--"]
        if not session:
            runtime, profile = key.split("/", 1)
            rows.append(head + [f"`{profile}`", RUNTIMES[runtime], record["engine"], record["tier"]]
                        + ["--"] * 3 + ["no session"] + ["--"] * 6 + [score(record.get("capability"))]
                        + ["--"] * 2)
            continue
        optimal = session["optimal_streams"]
        top = f"{number(best(session), 2)} @{optimal}x" if optimal else "--"
        rows.append(head + session_cells(key, record)
                    + [top, streams_text(session["streams"], "sessions_per_hour", 2, str(optimal))]
                    + session_tail(session)[:5] + [score(record.get("capability"))]
                    + session_tail(session)[5:])
    headers = ["Rank", "Profile", "Runtime", "Engine", "Tier", "Context", "Slots", "KV pool",
               "Best sessions/h", "Other stream counts", "Complete", "Out tok/session 1x",
               "Prefill tok/s 1x", "Report decode 1x", "pp512 / tg128",
               "OWASP vuln score [95% CI]", "Publishable", "Session JSON"]
    return table(headers, rows) + notes(order, profiles)


def interactive_table(profiles: dict) -> list[str]:
    keys = sorted(key for key, record in profiles.items()
                  if record["role"] == "interactive" and record.get("session"))
    rows = [session_cells(key, profiles[key])
            + [streams_text(profiles[key]["session"]["streams"], "sessions_per_hour", 2)]
            + session_tail(profiles[key]["session"]) for key in keys]
    headers = ["Profile", "Runtime", "Engine", "Tier", "Context", "Slots", "KV pool",
               "Sessions/h by streams", "Complete", "Out tok/session 1x", "Prefill tok/s 1x",
               "Report decode 1x", "pp512 / tg128", "Publishable", "Session JSON"]
    return table(headers, rows) + notes(keys, profiles)


def capability_table(profiles: dict) -> list[str]:
    def aptitude(record: dict) -> str:
        capability = record["capability"]
        details = capability["audit_aptitude"]
        sound = (f"sound {details['sound_samples']} of {details['judged_samples']}"
                 if details.get("scored") else "")
        # A ranked or listed audit row shows its score in the audit table.
        shown = score(capability) if record["role"] != "audit" or not details.get("scored") else ""
        return "; ".join(part for part in (shown, sound) if part)

    def compatibility(capability: dict) -> str:
        why = ", ".join(capability["failed_checks"] or []) or ("halted" if capability["halted"] else "")
        return f"{capability['status']} ({why})" if why else capability["status"]

    def clean(capability: dict) -> str:
        if capability["clean_rate"] is None:
            return "--"
        text = (f"{capability['clean_samples']} of {capability['samples']} "
                f"({capability['clean_rate']:.0%})")
        if capability["fitness_samples"]:
            text += f"; fitness {capability['fitness_clean']} of {capability['fitness_samples']}"
        return text

    keys = sorted((key for key, record in profiles.items() if record.get("capability")),
                  key=lambda key: (profiles[key]["role"] != "audit",
                                   not ranked(profiles[key]), key))
    rows = []
    for key in keys:
        record = profiles[key]
        capability = record["capability"]
        features = capability["features"] or {}
        runtime, profile = key.split("/", 1)
        rows.append([
            RUNTIMES[runtime], f"`{profile}`", "yes" if record["campaign"] else "no",
            capability["identity_check"], capability["reasoning"],
            *(features.get(name, "--") for name in ("thinking_disabled", "tool_call",
                                                    "streaming_tool_call", "tool_round_trip",
                                                    "structured_json")),
            capability["unaided_document"] or "--",
            f"{capability['schema_enforcement']} ({features.get('json_schema', '--')})",
            clean(capability), compatibility(capability), aptitude(record),
            f"`{(capability['model_identity'] or '--')[:12]}`", f"`{capability['artifact']}`"])
    headers = ["Runtime", "Profile", "Campaign", "Identity", "Reasoning", "Thinking off",
               "Tool call", "Streaming tool call", "Tool loop", "JSON", "Unaided document",
               "Schema enforced", "Clean samples", "Compatibility", "Audit aptitude",
               "Model identity", "Artifact"]
    return table(headers, rows)


TABLES = {"audit": audit_table, "interactive": interactive_table, "capability": capability_table}


def unset(record: dict) -> list[str]:
    return [field for field in ("role", "tier", "engine", "campaign") if record.get(field) is None]


def check(slug: str, profiles: dict) -> None:
    for key, record in profiles.items():
        if unset(record):
            sys.exit(f"{slug}.json {key}: set {', '.join(unset(record))} by hand")
        if record["role"] not in ROLES:
            sys.exit(f"{slug}.json {key}: role must be one of {ROLES}")


def page(slug: str) -> str:
    """The page with its tables rendered from its record."""
    profiles = load(slug)["profiles"]
    check(slug, profiles)
    text = (HERE / f"{slug}.md").read_text()

    def fill(match: re.Match) -> str:
        if match.group(2) not in TABLES:
            sys.exit(f"{slug}.md: unknown table marker {match.group(2)!r}")
        lines = TABLES[match.group(2)](profiles)
        return match.group(1) + "\n" + "\n".join(lines) + "\n\n" + match.group(3)

    return MARKER.sub(fill, text)


def pages() -> dict[Path, str]:
    return {path: page(path.stem) for path in sorted(HERE.glob("*.md"))}


def main(argv: list[str]) -> None:
    if argv[:1] == ["import"] and len(argv) == 3:
        import_row(argv[1], argv[2])
        new = [key for key, record in load(argv[1])["profiles"].items() if unset(record)]
        if new:
            print(f"set the hand fields of {', '.join(new)} in {argv[1]}.json, then make results")
            return
    elif argv != ["render"]:
        sys.exit(__doc__)
    for path, text in pages().items():
        path.write_text(text)


if __name__ == "__main__":
    main(sys.argv[1:])
