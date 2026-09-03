#!/usr/bin/env python3
"""Run AuditBench v1 against the managed LM Studio server."""

import json
import os
import pathlib
import re
import subprocess
import sys

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
# The shared harness modules (audit_bench, capability_check) resolve via
# PYTHONPATH -- the sibling llm-audit-bench checkout's src/, set by the root
# Makefile -- or, on deployed remote trees, as copies rsynced next to this
# file.

from audit_bench import (
    OpenAIChatAdapter,
    openai_chat_fn,
    openai_model_card,
    run_benchmark,
)


def _config_value(conf: pathlib.Path, name: str) -> str:
    pattern = rf'^{name}="\$\{{{name}:-([^}}"]+)\}}"'
    match = re.search(pattern, conf.read_text(encoding="utf-8"), re.MULTILINE)
    if not match:
        raise ValueError(f"{name} not found in {conf}")
    return match.group(1)


def _config_optional(conf: pathlib.Path, name: str) -> str | None:
    try:
        return _config_value(conf, name)
    except ValueError:
        return None


def _config_setting(conf: pathlib.Path, name: str) -> str | None:
    return os.environ.get(name) or _config_optional(conf, name)


def _server_log() -> pathlib.Path:
    state_root = pathlib.Path(
        os.environ.get("XDG_STATE_HOME", pathlib.Path.home() / ".local" / "state")
    )
    return pathlib.Path(
        os.environ.get("LMSTUDIO_LOG", state_root / "lmstudio" / "server.log")
    )


def _lms_bin() -> str:
    override = os.environ.get("LMSTUDIO_BIN")
    if override and pathlib.Path(override).is_file():
        return override
    return "lms"


def _loaded_models() -> list[dict]:
    """Loaded-model records from `lms ps --json`."""
    try:
        out = subprocess.run(
            [_lms_bin(), "ps", "--json"],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        ).stdout
    except (subprocess.SubprocessError, OSError) as exc:
        raise RuntimeError(f"could not run `lms ps --json`: {exc}") from exc
    try:
        data = json.loads(out)
    except (json.JSONDecodeError, ValueError) as exc:
        raise RuntimeError(f"`lms ps --json` was not valid JSON: {out!r}") from exc
    if isinstance(data, dict):
        data = data.get("models") or data.get("data") or []
    if not isinstance(data, list):
        raise RuntimeError(f"unexpected `lms ps --json` shape: {data!r}")
    return data


def _select_loaded(models: list[dict], served_name: str) -> dict:
    matches = [
        model
        for model in models
        if served_name
        in {
            str(model.get("identifier") or ""),
            str(model.get("modelKey") or ""),
            str(model.get("key") or ""),
        }
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"expected one loaded model identified as {served_name!r}, "
            f"found {len(matches)}"
        )
    return matches[0]


def _format_matches(expected: str, actual: str) -> bool:
    """Compare a config LMSTUDIO_FORMAT against the format lms reports.

    LMSTUDIO_FORMAT names the artifact family the way `lms get --mlx/--gguf`
    selects it (mlx or gguf), but `lms ls`/`lms ps` report the on-disk
    container: an MLX artifact reports format "safetensors", not "mlx" (a
    GGUF artifact reports "gguf"). So an mlx config expectation matches a
    reported safetensors (or mlx) format; every other family matches on the
    reported string directly. Without this, the identity check aborts every
    MLX load even when the correct MLX artifact is resident.
    """
    expected = str(expected).lower()
    actual = str(actual).lower()
    if expected == "mlx":
        return actual in {"mlx", "safetensors"}
    return actual == expected


def _model_identity(served_name: str, expectations: dict) -> dict:
    """Live identity from `lms ps`, keyed on served name plus artifact facts.

    Accepted deviation (lmstudio/AGENTS.md): LM Studio exposes no served
    content digest, so identity is verified against the model key/path,
    format, quantization, and architecture rather than a SHA256.
    """
    loaded = _select_loaded(_loaded_models(), served_name)
    details = loaded.get("details") or {}

    def field(*keys: str):
        for key in keys:
            value = loaded.get(key)
            if value in (None, "", []):
                value = details.get(key)
            if value not in (None, "", []):
                return value
        return None

    def quant_name(value) -> str | None:
        # lms reports quantization as {"name": "Q4_K_M", "bits": 4} in ls/ps,
        # or occasionally as a bare string. Normalise to the name.
        if isinstance(value, dict):
            value = value.get("name") or value.get("level")
        return (str(value) or None) if value not in (None, "") else None

    identity = {
        "served_name": served_name,
        "model_key": field("modelKey", "key") or served_name,
        "path": field("path"),
        "format": (str(field("format", "type") or "") or None),
        "quantization": quant_name(
            field("quantization", "quantizationLevel")
        ),
        "architecture": (str(field("architecture") or "") or None),
        "size_bytes": int(field("sizeBytes", "size") or 0),
        "context_length": int(
            field("contextLength", "context_length", "maxContextLength") or 0
        ),
        "checked": True,
    }
    mismatches = []
    for key, expected in expectations.items():
        actual = identity.get(key)
        if expected is None or actual is None:
            continue
        if key == "format":
            # LMSTUDIO_FORMAT names the get-filter family (mlx/gguf); lms
            # reports the on-disk container (mlx -> safetensors), so map
            # rather than compare literally. See _format_matches.
            if not _format_matches(expected, actual):
                mismatches.append(f"{key}={actual!r}, expected {expected!r}")
            continue
        # Compare case-insensitively: lms reports Q4_K_M / gguf / Qwen3 with
        # inconsistent casing across fields and versions.
        if str(actual).lower() != str(expected).lower():
            mismatches.append(f"{key}={actual!r}, expected {expected!r}")
    if mismatches:
        raise RuntimeError(
            f"LM Studio model identity mismatch for {served_name}: "
            + "; ".join(mismatches)
        )
    return {**identity, "expected": expectations, "matched": True}


def _identity_expectations(conf: pathlib.Path) -> dict:
    return {
        "format": _config_setting(conf, "LMSTUDIO_FORMAT"),
        "quantization": _config_setting(conf, "LMSTUDIO_EXPECTED_QUANTIZATION"),
        "architecture": _config_setting(conf, "LMSTUDIO_EXPECTED_ARCHITECTURE"),
    }


def _runtime_profile(*, context: int, identity: dict, dry_run: bool) -> dict:
    if dry_run:
        return {
            "checked": False,
            "configured_context": context,
            "active_slots": 1,
        }
    log = _server_log()
    if not log.is_file():
        raise RuntimeError(f"managed LM Studio log not found: {log}")
    text = log.read_text(encoding="utf-8", errors="replace")
    config_line = _last_match(r"^(config: .+)$", text)
    host_line = _last_match(r"^(host: .+)$", text)
    if not config_line or not host_line:
        raise RuntimeError(f"resolved LM Studio launch profile not found in {log}")
    config_match = re.fullmatch(
        r"config: model=(\S+) served=(\S+) format=(\S+) context=([0-9]+)",
        config_line,
    )
    host_match = re.fullmatch(
        r"host: bind=(\S+) port=([0-9]+) gpu=(\S+) version=(\S+)", host_line
    )
    if not config_match or not host_match:
        raise RuntimeError(
            f"could not parse LM Studio profile: {config_line}; {host_line}"
        )
    _model_key, served, fmt, logged_context = config_match.groups()
    bind, port, gpu, version = host_match.groups()
    if int(logged_context) != context:
        raise RuntimeError(
            f"launch profile context is {logged_context}, configured is {context}"
        )
    return {
        "checked": True,
        "launcher_lines": [config_line, host_line],
        "served_name": served,
        "artifact_format": fmt,
        "bind": bind,
        "port": int(port),
        "gpu_offload": gpu,
        "lmstudio_version": version,
        "configured_context": context,
        "active_slots": 1,
        "model_identity": identity,
    }


def _last_match(pattern: str, text: str) -> str | None:
    matches = re.findall(pattern, text, re.MULTILINE)
    return matches[-1] if matches else None


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {pathlib.Path(sys.argv[0]).name} <model-config-name>")

    tag = sys.argv[1]
    conf = SCRIPT_DIR / "models" / f"{tag}.conf"
    if not conf.is_file():
        raise SystemExit(f"no such model config: {conf}")
    served = os.environ.get(
        "LMSTUDIO_SERVED_NAME", _config_value(conf, "LMSTUDIO_SERVED_NAME")
    )
    context = int(
        os.environ.get(
            "LMSTUDIO_CONTEXT_LENGTH", _config_value(conf, "LMSTUDIO_CONTEXT_LENGTH")
        )
    )
    expectations = _identity_expectations(conf)
    timeout = int(os.environ.get("AUDIT_BENCH_TIMEOUT", "7200"))
    host = os.environ.get("LMSTUDIO_HOST", "127.0.0.1")
    port = os.environ.get("LMSTUDIO_PORT", "1234")
    base = os.environ.get("LMSTUDIO_BENCH_BASE", f"http://{host}:{port}")
    dry_run = os.environ.get("AUDIT_BENCH_DRY_RUN", "0") == "1"

    # LM Studio's CLI-loaded single model is one served instance; it exposes no
    # fungible KV pool metric, so -- like the Ollama adapter -- capacity is one
    # active slot with the configured per-request context. Never synthesise a
    # pool size from context length.
    active_slots = 1
    kv_pool_tokens = context

    runtime_metadata = {
        "base_url": base,
        "lmstudio_version": os.environ.get("LMSTUDIO_VERSION"),
        "capacity_source": "single loaded model, configured context (no fungible pool)",
    }
    model_identity = {
        "served_name": served,
        "configured_context": context,
        "expected": expectations,
        "checked": False,
        "matched": False,
    }

    if dry_run:
        runtime_metadata["model_identity"] = model_identity
        runtime_metadata["runtime_profile"] = _runtime_profile(
            context=context, identity=model_identity, dry_run=True
        )
        return run_benchmark(
            runtime="lmstudio",
            tag=tag,
            model=served,
            context=context,
            request=None,
            active_slots=active_slots,
            kv_pool_tokens=kv_pool_tokens,
            runtime_metadata=runtime_metadata,
            provenance_files={
                "adapter": pathlib.Path(__file__).resolve(),
                "model_config": conf,
            },
        )

    card = openai_model_card(base, timeout)
    if card.get("id") != served:
        raise RuntimeError(
            f"live model is {card.get('id')}, expected configured {served}"
        )
    live_context = card.get("max_model_len")
    if live_context is not None and int(live_context) != context:
        raise RuntimeError(
            f"live max_model_len is {int(live_context):,}, "
            f"expected configured {context:,}; repeat the startup override"
        )
    identity = _model_identity(served, expectations)
    print(
        "identity: "
        f"{identity['served_name']} key {identity['model_key']} "
        f"format {identity['format']} quantization "
        f"{identity['quantization'] or 'unspecified'} architecture "
        f"{identity['architecture'] or 'unspecified'}"
    )
    model_identity = {**model_identity, **identity, "live_max_model_len": live_context}
    runtime_metadata["model_identity"] = model_identity
    runtime_metadata["live_max_model_len"] = live_context
    runtime_metadata["runtime_profile"] = _runtime_profile(
        context=context, identity=model_identity, dry_run=False
    )

    return run_benchmark(
        runtime="lmstudio",
        tag=tag,
        model=served,
        context=context,
        request=OpenAIChatAdapter(base, served, timeout),
        openai_chat=openai_chat_fn(f"{base}/v1", served, timeout),
        active_slots=active_slots,
        kv_pool_tokens=kv_pool_tokens,
        runtime_metadata=runtime_metadata,
        provenance_files={
            "adapter": pathlib.Path(__file__).resolve(),
            "model_config": conf,
        },
    )


if __name__ == "__main__":
    sys.exit(main())
