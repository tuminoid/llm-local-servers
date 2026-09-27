#!/usr/bin/env python3
"""Run AuditBench v2 against the CUDA vLLM server."""

import json
import os
import pathlib
import re
import subprocess
import sys
import urllib.request

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
    vllm_capacity,
)


def _config_values(conf: pathlib.Path, names: tuple[str, ...]) -> dict[str, str]:
    """Resolve trusted shell config with the same inheritance as start.sh."""
    printers = "\n".join(
        f'printf "%s\\0" "${{{name}:-}}"' for name in names
    )
    try:
        completed = subprocess.run(
            [
                "bash",
                "-c",
                f'set -euo pipefail\nsource "$1"\n{printers}',
                "bash",
                str(conf),
            ],
            capture_output=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("bash is required to resolve vLLM model config") from exc
    if completed.returncode:
        error = completed.stderr.decode(errors="replace").strip()
        raise RuntimeError(f"failed to resolve {conf}: {error}")
    values = completed.stdout.split(b"\0")
    if len(values) != len(names) + 1 or values[-1]:
        raise RuntimeError(f"unexpected config output while resolving {conf}")
    return {
        name: value.decode(errors="strict")
        for name, value in zip(names, values[:-1], strict=True)
    }


def _require_revision(revision: str, conf: pathlib.Path) -> None:
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise SystemExit(
            f"VLLM_MODEL_REVISION in {conf} must be a 40-character commit SHA"
        )


def _server_log() -> pathlib.Path:
    state_root = pathlib.Path(
        os.environ.get("XDG_STATE_HOME", pathlib.Path.home() / ".local" / "state")
    )
    return pathlib.Path(os.environ.get("VLLM_LOG", state_root / "vllm" / "server.log"))


def _capacity(context: int, dry_run: bool) -> tuple[int, int, str]:
    return vllm_capacity(_server_log(), context, dry_run)


def _last_match(pattern: str, text: str) -> str | None:
    matches = re.findall(pattern, text, re.MULTILINE)
    return matches[-1] if matches else None


def _live_vllm_version(base: str, timeout: int) -> str:
    """Engine version reported by the running server.

    The environment's VLLM_VERSION is what the operator asked for, not what is
    serving: locally nothing installs from it -- run.sh uses whatever `vllm`
    resolves to -- so recording it as fact once let this host serve 0.27.1
    while the Makefile default claimed 0.28.0. A measured artifact must name
    the engine that produced it, so this probes and the caller refuses on
    disagreement.
    """
    url = f"{base.rstrip('/')}/version"
    try:
        with urllib.request.urlopen(url, timeout=min(timeout, 30)) as response:
            payload = json.load(response)
    except (OSError, ValueError) as error:
        raise RuntimeError(f"cannot read the live engine version from {url}: {error}")
    version = payload.get("version")
    if not version:
        raise RuntimeError(f"{url} returned no version field: {payload!r}")
    return str(version)


def _runtime_profile(
    *,
    context: int,
    active_slots: int,
    kv_pool_tokens: int,
    capacity_source: str,
    model_source: str,
    model_revision: str,
    model: str,
    model_settings: dict,
    dry_run: bool,
) -> dict:
    if dry_run:
        return {
            "checked": False,
            "configured_context": context,
            "active_slots": active_slots,
            "kv_pool_tokens": kv_pool_tokens,
            "capacity_source": capacity_source,
            "model_settings": model_settings,
        }
    log = _server_log()
    if not log.is_file():
        raise RuntimeError(f"managed vLLM log not found: {log}")
    text = log.read_text(encoding="utf-8")
    starting_line = _last_match(r"^(starting .+)$", text)
    host_line = _last_match(r"^(host: .+)$", text)
    if not starting_line or not host_line:
        raise RuntimeError(f"resolved launch profile not found in {log}")
    expected_start = f'starting {model_source}@{model_revision} as "{model}"'
    if not starting_line.startswith(expected_start):
        raise RuntimeError(
            f"managed launch identity is {starting_line!r}, "
            f"expected prefix {expected_start!r}"
        )
    match = re.fullmatch(
        r"host: sm_([0-9]+), ([0-9]+) MiB VRAM -> backend (.+?), "
        r"kv (\S+), util ([0-9.]+), seqs ([0-9]+), batched ([0-9]+)",
        host_line,
    )
    if not match:
        raise RuntimeError(f"could not parse managed host profile: {host_line}")
    capability, vram, requested_backend, kv_dtype, utilization, seqs, batched = (
        match.groups()
    )
    if int(seqs) != active_slots:
        raise RuntimeError(
            f"launch profile has {seqs} slots, capacity resolver found {active_slots}"
        )
    actual_backends = list(
        dict.fromkeys(
            re.findall(
                r"Using (?:AttentionBackendEnum\.)?([A-Z_]+)(?: attention)? backend",
                text,
            )
        )
    )
    concurrency = _last_match(
        r"Maximum concurrency for [0-9,]+ tokens per request: ([0-9.]+)x",
        text,
    )
    return {
        "checked": True,
        "launcher_lines": [starting_line, host_line],
        "compute_capability": int(capability),
        "vram_mib": int(vram),
        "requested_attention_backend": requested_backend,
        "actual_attention_backends": actual_backends,
        "kv_cache_dtype": kv_dtype,
        "gpu_memory_utilization": float(utilization),
        "max_num_seqs": int(seqs),
        "max_num_batched_tokens": int(batched),
        "configured_context": context,
        "active_slots": active_slots,
        "kv_pool_tokens": kv_pool_tokens,
        "maximum_concurrency": float(concurrency) if concurrency else None,
        "capacity_source": capacity_source,
        "model_settings": model_settings,
    }


def _provenance_files(conf: pathlib.Path) -> dict[str, pathlib.Path]:
    files = {
        "adapter": pathlib.Path(__file__).resolve(),
        "model_config": conf,
    }
    match = re.search(
        r'^source "\$\{BASH_SOURCE\[0\]%/\*\}/([^"]+)"$',
        conf.read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    if match:
        files["model_config_base"] = conf.parent / match.group(1)
    return files


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {pathlib.Path(sys.argv[0]).name} <model-config-name>")

    tag = sys.argv[1]
    conf = SCRIPT_DIR / "models" / f"{tag}.conf"
    if not conf.is_file():
        raise SystemExit(f"no such model config: {conf}")
    config = _config_values(
        conf,
        (
            "VLLM_MODEL",
            "VLLM_MODEL_REVISION",
            "VLLM_SERVED_NAME",
            "VLLM_MAX_LEN",
            "VLLM_HF_OVERRIDES",
            "VLLM_ALLOW_LONG_MAX_MODEL_LEN",
            "VLLM_KV_DTYPE",
            "VLLM_ATTN_AUTO",
            "VLLM_MLA",
            "VLLM_REASONING_PARSER",
            "VLLM_REASONING_PLUGIN",
            "VLLM_TOOL_PARSER",
            "VLLM_TOOL_PLUGIN",
            "VLLM_CHAT_TEMPLATE",
            "VLLM_SAMPLING",
        ),
    )
    model_source = config["VLLM_MODEL"]
    model_revision = config["VLLM_MODEL_REVISION"]
    model = config["VLLM_SERVED_NAME"]
    context = int(config["VLLM_MAX_LEN"])
    if not model_source or not model_revision or not model:
        raise SystemExit(f"incomplete model identity in {conf}")
    _require_revision(model_revision, conf)
    model_settings = {
        "hf_overrides": config["VLLM_HF_OVERRIDES"] or None,
        "allow_long_max_model_len": config["VLLM_ALLOW_LONG_MAX_MODEL_LEN"] or None,
        "preferred_kv_dtype": config["VLLM_KV_DTYPE"] or None,
        "attention_auto": config["VLLM_ATTN_AUTO"] or None,
        "mla": config["VLLM_MLA"] or None,
        "reasoning_parser": config["VLLM_REASONING_PARSER"] or None,
        "reasoning_plugin": config["VLLM_REASONING_PLUGIN"] or None,
        "tool_parser": config["VLLM_TOOL_PARSER"] or None,
        "tool_plugin": config["VLLM_TOOL_PLUGIN"] or None,
        "chat_template": config["VLLM_CHAT_TEMPLATE"] or None,
    }
    # The checkpoint's sampling, a model fact; the harness decodes at it.
    os.environ["AUDIT_BENCH_SAMPLING"] = config["VLLM_SAMPLING"]
    timeout = int(os.environ.get("AUDIT_BENCH_TIMEOUT", "7200"))
    base = os.environ.get("VLLM_BENCH_BASE", "http://127.0.0.1:8000")
    dry_run = os.environ.get("AUDIT_BENCH_DRY_RUN", "0") == "1"
    active_slots, kv_pool_tokens, capacity_source = _capacity(context, dry_run)
    runtime_metadata = {
        "base_url": base,
        "model_source": model_source,
        "model_revision": model_revision,
        "vllm_version": None,
        "transformers_version_declared": os.environ.get(
            "VLLM_TRANSFORMERS_VERSION"
        ),
        "capacity_source": capacity_source,
    }
    model_identity = {
        "source": model_source,
        "revision": model_revision,
        "served_name": model,
        "configured_context": context,
        "checked": False,
        "matched": False,
    }
    if not dry_run:
        live_vllm_version = _live_vllm_version(base, timeout)
        declared_vllm_version = os.environ.get("VLLM_VERSION")
        if declared_vllm_version and live_vllm_version != declared_vllm_version:
            raise RuntimeError(
                f"live engine is vLLM {live_vllm_version}, but VLLM_VERSION "
                f"declares {declared_vllm_version}; the documented rates are "
                "read per engine version, so align the installed vllm with "
                "the pin or pass the version that is actually serving"
            )
        runtime_metadata["vllm_version"] = live_vllm_version
        card = openai_model_card(base, timeout)
        if card.get("id") != model:
            raise RuntimeError(
                f"live model is {card.get('id')}, expected configured {model}"
            )
        live_context = card.get("max_model_len")
        if live_context is not None and int(live_context) != context:
            raise RuntimeError(
                f"live max_model_len is {int(live_context):,}, "
                f"expected configured {context:,}; repeat the startup override"
            )
        runtime_metadata["live_max_model_len"] = live_context
        model_identity = {
            **model_identity,
            "checked": True,
            "matched": True,
            "live_max_model_len": live_context,
        }
    runtime_metadata["model_identity"] = model_identity
    runtime_metadata["runtime_profile"] = _runtime_profile(
        context=context,
        active_slots=active_slots,
        kv_pool_tokens=kv_pool_tokens,
        capacity_source=capacity_source,
        model_source=model_source,
        model_revision=model_revision,
        model=model,
        model_settings=model_settings,
        dry_run=dry_run,
    )

    return run_benchmark(
        runtime="vllm-cuda",
        tag=tag,
        model=model,
        context=context,
        request=OpenAIChatAdapter(base, model, timeout),
        openai_chat=openai_chat_fn(f"{base}/v1", model, timeout),
        active_slots=active_slots,
        kv_pool_tokens=kv_pool_tokens,
        runtime_metadata=runtime_metadata,
        provenance_files=_provenance_files(conf),
    )


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:
        sys.exit(f"error: {error}")
