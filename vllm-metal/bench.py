#!/usr/bin/env python3
"""Run AuditBench v1 against the vLLM-Metal server."""

import json
import os
import pathlib
import re
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


def _server_log() -> pathlib.Path:
    state_root = pathlib.Path(
        os.environ.get("XDG_STATE_HOME", pathlib.Path.home() / ".local" / "state")
    )
    return pathlib.Path(
        os.environ.get("VLLM_METAL_LOG", state_root / "vllm-metal" / "server.log")
    )


def _model_dir(tag: str) -> pathlib.Path:
    data_root = pathlib.Path(
        os.environ.get("XDG_DATA_HOME", pathlib.Path.home() / ".local" / "share")
    )
    models_root = pathlib.Path(
        os.environ.get("VLLM_METAL_MODELS_DIR", data_root / "vllm-metal" / "models")
    )
    return models_root / tag


def _download_identity(model_dir: pathlib.Path) -> dict:
    required = [
        model_dir / "config.json",
        model_dir / "tokenizer_config.json",
        *sorted(model_dir.glob("*.safetensors")),
    ]
    for optional in ("chat_template.jinja", "model.safetensors.index.json"):
        path = model_dir / optional
        if path.is_file():
            required.append(path)
    if len(required) < 3 or any(not path.is_file() for path in required):
        raise RuntimeError(f"incomplete managed model directory: {model_dir}")
    metadata_root = model_dir / ".cache" / "huggingface" / "download"
    revisions = set()
    for path in required:
        metadata = metadata_root / f"{path.name}.metadata"
        if not metadata.is_file():
            raise RuntimeError(f"Hugging Face revision metadata missing: {metadata}")
        revision = metadata.read_text(encoding="utf-8").splitlines()[0].strip()
        if not re.fullmatch(r"[0-9a-f]{40}", revision):
            raise RuntimeError(f"invalid Hugging Face revision in {metadata}")
        revisions.add(revision)
    if len(revisions) != 1:
        raise RuntimeError(
            f"managed model directory contains mixed revisions: {sorted(revisions)}"
        )
    return {
        "downloaded_revision": revisions.pop(),
        "verified_files": len(required),
    }


def _live_vllm_version(base: str, timeout: int) -> str:
    """vLLM core version reported by the running server.

    The environment's VLLM_METAL_VLLM_VERSION is what the operator asked
    install.sh for, not what is serving. Recording it as fact is how the CUDA
    adapter once labelled 0.27.1 rates as 0.28.0, so a measured artifact
    probes the engine instead and the caller refuses on disagreement.
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


def _installed_pins() -> dict[str, str]:
    """Plugin and core versions install.sh recorded in the managed venv.

    The plugin version has no endpoint, but install.sh stamps what it actually
    installed into `${VLLM_METAL_VENV}/.pins` as `vllm-metal=X vllm=Y`. That
    file is this tree's own record, so it is evidence rather than a
    declaration. A venv assembled by hand may not have it; the caller then
    records no plugin version rather than echoing the request back.
    """
    data_root = pathlib.Path(
        os.environ.get("XDG_DATA_HOME", pathlib.Path.home() / ".local" / "share")
    )
    data_dir = pathlib.Path(
        os.environ.get("VLLM_METAL_DATA_DIR", data_root / "vllm-metal")
    )
    venv = pathlib.Path(os.environ.get("VLLM_METAL_VENV", data_dir / "venv"))
    try:
        stamp = (venv / ".pins").read_text(encoding="utf-8").strip()
    except OSError:
        return {}
    pins: dict[str, str] = {}
    for field in stamp.split():
        name, separator, value = field.partition("=")
        if separator and value:
            pins[name] = value
    return pins


def _capacity(context: int, dry_run: bool) -> tuple[int, int, str]:
    return vllm_capacity(_server_log(), context, dry_run)


def _prefix_caching(dry_run: bool) -> str | None:
    """Prefix-caching state from the launcher's host line.

    An align-mode (APC) run is a different operating point with different
    temp-0 outputs than the cache-off canonical, so the artifact must say
    which one it measured. None on dry runs and pre-knob logs.
    """
    log = _server_log()
    if dry_run or not log.is_file():
        return None
    matches = re.findall(
        r"host:.*?\bprefix-caching (\S+)", log.read_text(encoding="utf-8")
    )
    return matches[-1] if matches else None


def _last_match(pattern: str, text: str) -> str | None:
    matches = re.findall(pattern, text, re.MULTILINE)
    return matches[-1] if matches else None


def _runtime_profile(
    *,
    context: int,
    active_slots: int,
    kv_pool_tokens: int,
    capacity_source: str,
    model: str,
    model_dir: pathlib.Path,
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
            "prefix_caching": None,
            "model_settings": model_settings,
        }
    log = _server_log()
    if not log.is_file():
        raise RuntimeError(f"managed vLLM-Metal log not found: {log}")
    text = log.read_text(encoding="utf-8")
    starting_line = _last_match(r"^(starting .+)$", text)
    host_line = _last_match(r"^(host: .+)$", text)
    if not starting_line or not host_line:
        raise RuntimeError(f"resolved launch profile not found in {log}")
    expected_start = f'starting {model_dir} as "{model}"'
    if not starting_line.startswith(expected_start):
        raise RuntimeError(
            f"managed launch identity is {starting_line!r}, "
            f"expected prefix {expected_start!r}"
        )
    match = re.fullmatch(
        r"host: ([0-9]+) GiB unified memory -> util ([0-9.]+), "
        r"seqs ([0-9]+), batched ([0-9]+), max-len ([0-9]+), "
        r"NAX (\S+), prefix-caching (\S+)",
        host_line,
    )
    if not match:
        raise RuntimeError(f"could not parse managed host profile: {host_line}")
    memory, utilization, seqs, batched, max_len, nax, prefix_caching = (
        match.groups()
    )
    if int(seqs) != active_slots:
        raise RuntimeError(
            f"launch profile has {seqs} slots, capacity resolver found {active_slots}"
        )
    if int(max_len) != context:
        raise RuntimeError(
            f"launch profile has context {max_len}, configured context is {context}"
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
    nax_evidence = list(
        dict.fromkeys(
            line.strip()
            for line in text.splitlines()
            if "nax" in line.lower() and not line.startswith("host:")
        )
    )
    return {
        "checked": True,
        "launcher_lines": [starting_line, host_line],
        "unified_memory_gib": int(memory),
        "gpu_memory_utilization": float(utilization),
        "max_num_seqs": int(seqs),
        "max_num_batched_tokens": int(batched),
        "configured_context": context,
        "nax_policy": nax,
        "nax_evidence": nax_evidence,
        "prefix_caching": prefix_caching,
        "actual_attention_backends": actual_backends,
        "active_slots": active_slots,
        "kv_pool_tokens": kv_pool_tokens,
        "maximum_concurrency": float(concurrency) if concurrency else None,
        "capacity_source": capacity_source,
        "model_settings": model_settings,
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {pathlib.Path(sys.argv[0]).name} <model-config-name>")

    tag = sys.argv[1]
    conf = SCRIPT_DIR / "models" / f"{tag}.conf"
    if not conf.is_file():
        raise SystemExit(f"no such model config: {conf}")
    model = os.environ.get("VLLM_SERVED_NAME", _config_value(conf, "VLLM_SERVED_NAME"))
    context = int(os.environ.get("VLLM_MAX_LEN", _config_value(conf, "VLLM_MAX_LEN")))
    model_source = os.environ.get(
        "VLLM_MODEL_REPO", _config_value(conf, "VLLM_MODEL_REPO")
    )
    model_revision = os.environ.get(
        "VLLM_MODEL_REVISION", _config_value(conf, "VLLM_MODEL_REVISION")
    )
    model_dir = _model_dir(tag)
    model_settings = {
        "reasoning_parser": os.environ.get("VLLM_REASONING_PARSER")
        or _config_optional(conf, "VLLM_REASONING_PARSER"),
        "tool_parser": os.environ.get("VLLM_TOOL_PARSER")
        or _config_optional(conf, "VLLM_TOOL_PARSER"),
        "kv_bytes_per_token": int(
            os.environ.get("VLLM_KV_BYTES_PER_TOKEN")
            or _config_optional(conf, "VLLM_KV_BYTES_PER_TOKEN")
            or 0
        ),
        "kv_bytes_per_token_apc": int(
            os.environ.get("VLLM_KV_BYTES_PER_TOKEN_APC")
            or _config_optional(conf, "VLLM_KV_BYTES_PER_TOKEN_APC")
            or 0
        ),
    }
    timeout = int(os.environ.get("AUDIT_BENCH_TIMEOUT", "7200"))
    base = os.environ.get("VLLM_METAL_BENCH_BASE", "http://127.0.0.1:8021")
    dry_run = os.environ.get("AUDIT_BENCH_DRY_RUN", "0") == "1"
    active_slots, kv_pool_tokens, capacity_source = _capacity(context, dry_run)
    runtime_metadata = {
        "base_url": base,
        "model_source": model_source,
        "model_revision": model_revision,
        "vllm_metal_version": None,
        "vllm_version": None,
        "capacity_source": capacity_source,
        "prefix_caching": _prefix_caching(dry_run),
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
        declared_vllm_version = os.environ.get("VLLM_METAL_VLLM_VERSION")
        if declared_vllm_version and live_vllm_version != declared_vllm_version:
            raise RuntimeError(
                f"live engine is vLLM {live_vllm_version}, but "
                f"VLLM_METAL_VLLM_VERSION declares {declared_vllm_version}; "
                "the documented rates are read per version, so reinstall the "
                "venv at the pin or pass the version that is actually serving"
            )
        runtime_metadata["vllm_version"] = live_vllm_version
        pins = _installed_pins()
        installed_plugin_version = pins.get("vllm-metal")
        declared_plugin_version = os.environ.get("VLLM_METAL_VERSION")
        if (
            installed_plugin_version
            and declared_plugin_version
            and installed_plugin_version != declared_plugin_version
        ):
            raise RuntimeError(
                f"managed venv holds vllm-metal {installed_plugin_version}, but "
                f"VLLM_METAL_VERSION declares {declared_plugin_version}; run "
                "vllm-metal-install to match the pin, or pass the installed "
                "version"
            )
        runtime_metadata["vllm_metal_version"] = installed_plugin_version
        download_identity = _download_identity(model_dir)
        if download_identity["downloaded_revision"] != model_revision:
            raise RuntimeError(
                f"managed model revision is "
                f"{download_identity['downloaded_revision']}, "
                f"configured revision is {model_revision}"
            )
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
            **download_identity,
        }
    runtime_metadata["model_identity"] = model_identity
    runtime_metadata["runtime_profile"] = _runtime_profile(
        context=context,
        active_slots=active_slots,
        kv_pool_tokens=kv_pool_tokens,
        capacity_source=capacity_source,
        model=model,
        model_dir=model_dir,
        model_settings=model_settings,
        dry_run=dry_run,
    )

    return run_benchmark(
        runtime="vllm-metal",
        tag=tag,
        model=model,
        context=context,
        request=OpenAIChatAdapter(base, model, timeout),
        openai_chat=openai_chat_fn(f"{base}/v1", model, timeout),
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
