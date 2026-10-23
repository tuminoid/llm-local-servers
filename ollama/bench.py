#!/usr/bin/env python3
"""Run AuditBench v2 against the managed Ollama server."""

import json
import os
import pathlib
import re
import sys
import time
import urllib.error
import urllib.request

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
# The shared harness modules (audit_bench, capability_check) resolve via
# PYTHONPATH -- the sibling llm-audit-bench checkout's src/, set by the root
# Makefile -- or, on deployed remote trees, as copies rsynced next to this
# file.

from audit_bench import (
    RequestResult,
    Settings,
    openai_chat_fn,
    run_benchmark,
)


def _base_url() -> str:
    value = os.environ.get(
        "OLLAMA_BENCH_BASE", os.environ.get("OLLAMA_HOST", "127.0.0.1:11434")
    ).rstrip("/")
    if not value.startswith(("http://", "https://")):
        value = f"http://{value}"
    return value


BASE = _base_url()
CHAT_URL = f"{BASE}/api/chat"
PS_URL = f"{BASE}/api/ps"
PULL_URL = f"{BASE}/api/pull"
SHOW_URL = f"{BASE}/api/show"
TAGS_URL = f"{BASE}/api/tags"
REGISTRY = "https://registry.ollama.ai"
STATE_ROOT = pathlib.Path(
    os.environ.get("XDG_STATE_HOME", pathlib.Path.home() / ".local" / "state")
)
SERVER_LOG = pathlib.Path(
    os.environ.get("OLLAMA_LOG", STATE_ROOT / "ollama" / "server.log")
)
TIMEOUT = int(
    os.environ.get(
        "AUDIT_BENCH_TIMEOUT", os.environ.get("OLLAMA_BENCH_TIMEOUT", "7200")
    )
)
EXPECTED_SLOTS = int(os.environ.get("OLLAMA_BENCH_JOBS", "1"))
LOAD_ONLY = os.environ.get("OLLAMA_BENCH_LOAD_ONLY", "0") == "1"


def _config_default(conf: pathlib.Path, name: str) -> str:
    pattern = rf'^{name}="\$\{{{name}:-([^}}"]+)\}}"'
    match = re.search(pattern, conf.read_text(encoding="utf-8"), re.MULTILINE)
    if not match:
        raise ValueError(f"{name} not found in {conf}")
    return match.group(1)


def _config_optional(conf: pathlib.Path, name: str) -> str | None:
    try:
        return _config_default(conf, name)
    except ValueError:
        return None


def _config_setting(conf: pathlib.Path, name: str) -> str | None:
    return os.environ.get(name) or _config_optional(conf, name)


def _identity_expectations(conf: pathlib.Path) -> dict:
    fields = {
        "digest": "OLLAMA_EXPECTED_DIGEST",
        "format": "OLLAMA_EXPECTED_FORMAT",
        "quantization": "OLLAMA_EXPECTED_QUANTIZATION",
        "architecture": "OLLAMA_EXPECTED_ARCHITECTURE",
        "native_context": "OLLAMA_EXPECTED_NATIVE_CONTEXT",
    }
    expectations = {}
    for field, variable in fields.items():
        value = _config_setting(conf, variable)
        # Some MLX tags publish no context_length; the conf then pins that.
        if field == "native_context" and value == "unspecified":
            expectations[field] = None
        elif value:
            expectations[field] = int(value) if field == "native_context" else value
    missing = {"digest", "format", "native_context"} - expectations.keys()
    if missing:
        raise ValueError(
            f"missing Ollama identity expectations in {conf}: "
            f"{', '.join(sorted(missing))}"
        )
    if not re.fullmatch(r"[0-9a-f]{64}", expectations["digest"]):
        raise ValueError(
            f"OLLAMA_EXPECTED_DIGEST in {conf} must be a 64-character SHA256"
        )
    return expectations


def _request(url: str, payload: dict | None = None) -> dict:
    data = None if payload is None else json.dumps(payload).encode()
    request = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        raise RuntimeError(f"{exc.code} from {url}: {body}") from exc


def _canonical_model_name(name: str) -> str:
    leaf = name.rsplit("/", 1)[-1]
    return name if ":" in leaf else f"{name}:latest"


def _select_model(models: list[dict], requested: str, source: str) -> dict:
    target = _canonical_model_name(requested)
    matches = [
        model
        for model in models
        if any(
            _canonical_model_name(str(model.get(field, ""))) == target
            for field in ("name", "model")
            if model.get(field)
        )
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"expected one {source} entry for {requested}, found {len(matches)}"
        )
    return matches[0]


def _native_context(model_info: dict, architecture: str | None) -> tuple[int | None, dict]:
    context_fields = {}
    for key, value in model_info.items():
        if not key.endswith(".context_length"):
            continue
        try:
            context = int(value)
        except (TypeError, ValueError):
            continue
        if context > 0:
            context_fields[key] = context
    if architecture:
        preferred = context_fields.get(f"{architecture}.context_length")
        if preferred is not None:
            return preferred, context_fields
    unique = set(context_fields.values())
    return (unique.pop() if len(unique) == 1 else None), context_fields


def _model_identity(model: str) -> dict:
    summary = _select_model(
        _request(TAGS_URL).get("models", []), model, "installed model"
    )
    shown = _request(SHOW_URL, {"model": model, "verbose": False})
    details = dict(summary.get("details") or {})
    for key, value in (shown.get("details") or {}).items():
        if value not in (None, "", []):
            details[key] = value
    model_info = shown.get("model_info") or {}
    architecture = model_info.get("general.architecture") or None
    native_context, context_fields = _native_context(model_info, architecture)
    digest = str(summary.get("digest", ""))
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise RuntimeError(f"Ollama returned an invalid digest for {model}: {digest}")
    return {
        "requested_tag": model,
        "resolved_name": summary.get("name") or summary.get("model") or model,
        "digest": digest,
        "size_bytes": int(summary.get("size") or 0),
        "modified_at": summary.get("modified_at") or shown.get("modified_at"),
        "format": details.get("format") or None,
        "family": details.get("family") or None,
        "families": details.get("families") or [],
        "parameter_size": details.get("parameter_size") or None,
        "quantization": details.get("quantization_level") or None,
        "architecture": architecture,
        "parameter_count": model_info.get("general.parameter_count"),
        "native_context": native_context,
        "context_fields": context_fields,
        "capabilities": sorted(shown.get("capabilities") or []),
        "checked": True,
    }


def _registry_tag_digest(model: str) -> str | None:
    """Digest the registry currently serves for a tag, without downloading.

    Read from the Docker-Content-Digest header of the manifest endpoint
    (a few KB). Returns None when the registry is unreachable or answers
    strangely; the caller then treats the mismatch as unrecoverable.
    """
    namespace, _, rest = model.rpartition("/")
    name, _, tag = rest.partition(":")
    url = (f"{REGISTRY}/v2/{namespace or 'library'}/{name}"
           f"/manifests/{tag or 'latest'}")
    request = urllib.request.Request(url, headers={
        "Accept": "application/vnd.docker.distribution.manifest.v2+json",
    })
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            digest = response.headers.get("Docker-Content-Digest", "")
    except (urllib.error.URLError, TimeoutError):
        return None
    if digest.startswith("sha256:"):
        digest = digest[7:]
    return digest if re.fullmatch(r"[0-9a-f]{64}", digest) else None


def stale_or_drifted(
    local_digest: str, expected_digest: str, registry_digest: str | None
) -> str:
    """Classify a digest mismatch.

    "stale": the registry still serves the reviewed pin, so the local
    store simply predates the tag move -- pulling lands exactly the
    reviewed artifact and is safe to do automatically.
    "drifted": the registry moved past the pin; repin is a reviewed
    human decision (CAPABILITIES.md, identity drift), never automatic.
    "unknown": the registry could not be consulted; the refusal stands.
    """
    if registry_digest == expected_digest:
        return "stale"
    if registry_digest is None:
        return "unknown"
    return "drifted"


def verified_identity(model: str, expectations: dict) -> dict:
    """Validate live identity, auto-recovering a merely stale local store.

    A digest mismatch is only refused outright when the registry no
    longer serves the pinned digest (true drift) or cannot be consulted.
    When the registry still serves the pin, the local tag is stale from
    an upstream tag move: pull through the managed server -- landing
    exactly the already-reviewed artifact -- and validate again.
    """
    identity = _model_identity(model)
    expected_digest = expectations.get("digest")
    if expected_digest and identity["digest"] != expected_digest:
        registry_digest = _registry_tag_digest(model)
        verdict = stale_or_drifted(
            identity["digest"], expected_digest, registry_digest
        )
        if verdict == "stale":
            print(
                f"note: local {model} manifest {identity['digest'][:12]} is "
                f"stale; registry still serves the pinned "
                f"{expected_digest[:12]} -- pulling through the managed "
                "server",
                file=sys.stderr,
            )
            data = json.dumps({"model": model, "stream": False}).encode()
            request = urllib.request.Request(
                PULL_URL, data=data,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(request, timeout=3600) as response:
                json.load(response)
            identity = _model_identity(model)
        elif verdict == "drifted":
            raise RuntimeError(
                f"Ollama registry tag {model} has drifted past the reviewed "
                f"pin: registry serves {registry_digest[:12]}, the conf pins "
                f"{expected_digest[:12]}, local store has "
                f"{identity['digest'][:12]}. Repin is a reviewed decision "
                "(CAPABILITIES.md, identity drift)."
            )
    return _validate_identity(identity, expectations)


def _validate_identity(identity: dict, expectations: dict) -> dict:
    mismatches = []
    for field, expected in expectations.items():
        actual = identity.get(field)
        if actual != expected:
            mismatches.append(f"{field}={actual!r}, expected {expected!r}")
    if mismatches:
        raise RuntimeError(
            f"Ollama model identity mismatch for {identity['requested_tag']}: "
            + "; ".join(mismatches)
        )
    return {**identity, "expected": expectations, "matched": True}


class OllamaAdapter:
    def __init__(self, model: str, context: int, system: str | None = None):
        self.model = model
        self.context = context
        self.system = system

    def __call__(self, prompt: str, max_tokens: int, seed: int) -> RequestResult:
        messages = []
        if self.system:
            messages.append({"role": "system", "content": self.system})
        messages.append({"role": "user", "content": prompt})
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "keep_alive": -1,
            "options": {
                "num_ctx": self.context,
                "num_predict": max_tokens,
                "seed": seed,
                "temperature": 0,
            },
        }
        started = time.monotonic()
        body = _request(CHAT_URL, payload)
        return RequestResult(
            prompt_tokens=int(body.get("prompt_eval_count", 0)),
            output_tokens=int(body.get("eval_count", 0)),
            seconds=time.monotonic() - started,
            details={
                "load_duration_ns": body.get("load_duration", 0),
                "prompt_eval_duration_ns": body.get("prompt_eval_duration", 0),
                "eval_duration_ns": body.get("eval_duration", 0),
            },
        )


def _residency(model: str, identity: dict) -> dict:
    models = _request(PS_URL).get("models", [])
    loaded = _select_model(models, model, "running model")
    live_digest = str(loaded.get("digest", ""))
    if live_digest != identity["digest"]:
        raise RuntimeError(
            f"loaded model digest is {live_digest}, "
            f"installed identity is {identity['digest']}"
        )
    live_details = loaded.get("details") or {}
    for field, detail in (
        ("format", "format"),
        ("family", "family"),
        ("quantization", "quantization_level"),
    ):
        expected = identity.get(field)
        actual = live_details.get(detail)
        # HF manifests can leave the file-type field used by /api/ps as
        # "unknown" even when /api/show parsed the GGUF quantization.
        # The exact loaded digest was checked above; this sentinel adds no
        # conflicting evidence. A named, different quantization still fails.
        if field == "quantization" and actual == "unknown":
            actual = None
        if expected and actual and actual != expected:
            raise RuntimeError(
                f"loaded model {field} is {actual}, installed identity is {expected}"
            )
    total = int(loaded.get("size", 0))
    vram = int(loaded.get("size_vram", 0))
    cpu = max(total - vram, 0)
    print(
        "residency: "
        f"{cpu / 2**30:.2f} GiB CPU + {vram / 2**30:.2f} GiB GPU "
        f"= {total / 2**30:.2f} GiB, "
        f"context {loaded.get('context_length', 0):,}"
    )
    return {
        "resolved_name": loaded.get("name") or loaded.get("model"),
        "digest": live_digest,
        "bytes_total": total,
        "bytes_cpu": cpu,
        "bytes_gpu": vram,
        "allocated_context": int(loaded.get("context_length", 0)),
    }


def _effective_runner() -> tuple[str, int]:
    if not SERVER_LOG.is_file():
        raise RuntimeError(f"managed Ollama log not found: {SERVER_LOG}")
    text = SERVER_LOG.read_text(encoding="utf-8", errors="replace")
    matches = re.findall(r"starting llama-server.*?-np ([0-9]+)", text)
    if matches:
        return "llama.cpp", int(matches[-1])
    if "starting mlx runner subprocess" in text:
        return "mlx", 1
    if "model architecture does not currently support parallel requests" in text:
        return "llama.cpp", 1
    raise RuntimeError(f"effective runner parallelism not found in {SERVER_LOG}")


def _validate_runner(identity: dict, runner: str) -> None:
    expected = {"gguf": "llama.cpp", "safetensors": "mlx"}.get(
        identity.get("format")
    )
    if expected and runner != expected:
        raise RuntimeError(
            f"{identity['format']} artifact started with {runner}, expected {expected}"
        )


def _runtime_profile(
    *,
    model: str,
    context: int,
    identity: dict,
    residency: dict,
    runner: str,
    effective_slots: int,
) -> dict:
    if not SERVER_LOG.is_file():
        raise RuntimeError(f"managed Ollama log not found: {SERVER_LOG}")
    text = SERVER_LOG.read_text(encoding="utf-8", errors="replace")
    config_lines = re.findall(r"^(config: .+)$", text, re.MULTILINE)
    if len(config_lines) < 3:
        raise RuntimeError(f"resolved Ollama launch profile not found in {SERVER_LOG}")
    model_line, host_line, paths_line = config_lines[-3:]
    model_match = re.fullmatch(
        r"config: model=(\S+) context=([0-9]+) parallel=([0-9]+) "
        r"aggregate=([0-9]+) kv=(\S+)",
        model_line,
    )
    host_match = re.fullmatch(
        r"config: host=(\S+) flash_attention=(\S+) "
        r"fit_target=([0-9]+)MiB version=(\S+)",
        host_line,
    )
    if not model_match or not host_match:
        raise RuntimeError(
            f"could not parse managed Ollama profile: {model_line}; {host_line}"
        )
    logged_model, logged_context, requested_slots, aggregate, kv_type = (
        model_match.groups()
    )
    host, flash_attention, fit_target, version = host_match.groups()
    if logged_model != model or int(logged_context) != context:
        raise RuntimeError(
            f"managed profile is {logged_model} at {logged_context}, "
            f"expected {model} at {context}"
        )
    return {
        "checked": True,
        "launcher_lines": [model_line, host_line, paths_line],
        "bind": host,
        "ollama_version": version,
        "runner": runner,
        "requested_slots": int(requested_slots),
        "effective_slots": effective_slots,
        "configured_context": context,
        "aggregate_allocated_context": int(aggregate),
        "kv_cache_type": kv_type,
        "flash_attention": flash_attention == "1",
        "fit_target_mib": int(fit_target),
        "model_digest": identity["digest"],
        "artifact_format": identity["format"],
        "quantization": identity["quantization"],
        "residency": residency,
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {pathlib.Path(sys.argv[0]).name} <model-config-name>")
    if EXPECTED_SLOTS < 1:
        raise SystemExit("OLLAMA_BENCH_JOBS must be positive")

    tag = sys.argv[1]
    conf = SCRIPT_DIR / "models" / f"{tag}.conf"
    if not conf.is_file():
        raise SystemExit(f"no such model config: {conf}")
    model = os.environ.get("OLLAMA_MODEL", _config_default(conf, "OLLAMA_MODEL"))
    expectations = _identity_expectations(conf)
    context = int(
        os.environ.get(
            "OLLAMA_CONTEXT_LENGTH", _config_default(conf, "OLLAMA_CONTEXT_LENGTH")
        )
    )
    # Model-documented decode-compliance control (AuditBench protocol): a
    # per-model system message from the config, env wins. Exported so the
    # shared harness records it in the run's settings.
    system = (
        os.environ.get("OLLAMA_BENCH_SYSTEM_PROMPT")
        or _config_optional(conf, "OLLAMA_BENCH_SYSTEM_PROMPT")
        or None
    )
    if system:
        os.environ["AUDIT_BENCH_SYSTEM_PROMPT"] = system
    # The same standing: a reasoning_effort for templates that default
    # thinking off.
    effort = _config_setting(conf, "OLLAMA_BENCH_REASONING_EFFORT")
    if effort:
        os.environ["AUDIT_BENCH_REASONING_EFFORT"] = effort
    # A model whose card requires its prior reasoning back in the history.
    if _config_setting(conf, "OLLAMA_PRESERVE_REASONING") == "1":
        os.environ["AUDIT_BENCH_PRESERVE_REASONING"] = "1"
    # The checkpoint's sampling, a model fact; the harness decodes at it.
    os.environ["AUDIT_BENCH_SAMPLING"] = os.environ.get(
        "OLLAMA_SAMPLING"
    ) or _config_default(conf, "OLLAMA_SAMPLING")
    adapter = OllamaAdapter(model, context, system)

    if Settings.from_env().dry_run:
        return run_benchmark(
            runtime="ollama",
            tag=tag,
            model=model,
            context=context,
            request=None,
            active_slots=EXPECTED_SLOTS,
            kv_pool_tokens=context * EXPECTED_SLOTS,
            runtime_metadata={
                "base_url": BASE,
                "ollama_version": os.environ.get("OLLAMA_VERSION"),
                "capacity_source": "allocated context x effective slots",
                "model_identity": {
                    "requested_tag": model,
                    "checked": False,
                    "matched": False,
                    "expected": expectations,
                },
                "runtime_profile": {
                    "checked": False,
                    "configured_context": context,
                    "requested_slots": EXPECTED_SLOTS,
                },
            },
            provenance_files={
                "adapter": pathlib.Path(__file__).resolve(),
                "model_config": conf,
            },
        )

    print("loading model...")
    loaded = adapter("Reply with the single word ok.", 1, 1)
    if loaded.output_tokens != 1:
        raise RuntimeError("model-load request did not return one output token")
    identity = verified_identity(model, expectations)
    runner, effective_slots = _effective_runner()
    _validate_runner(identity, runner)
    identity = {
        **identity,
        "runner": runner,
        "effective_slots": effective_slots,
    }
    print(
        "identity: "
        f"{identity['resolved_name']} digest {identity['digest'][:12]} "
        f"format {identity['format']} quantization "
        f"{identity['quantization'] or 'unspecified'} architecture "
        f"{identity['architecture'] or 'unspecified'} native-context "
        f"{identity['native_context'] or 'unspecified'}"
    )
    residency = _residency(model, identity)
    if effective_slots != EXPECTED_SLOTS:
        raise RuntimeError(
            f"Ollama runner uses {effective_slots} slot(s), "
            f"expected OLLAMA_BENCH_JOBS={EXPECTED_SLOTS}"
        )
    if residency["allocated_context"] != context:
        raise RuntimeError(
            "Ollama did not allocate the requested context per slot: "
            f"{residency['allocated_context']:,} allocated, {context:,} expected"
        )
    runtime_profile = _runtime_profile(
        model=model,
        context=context,
        identity=identity,
        residency=residency,
        runner=runner,
        effective_slots=effective_slots,
    )
    if LOAD_ONLY:
        print(
            json.dumps(
                {
                    "tag": tag,
                    "model": model,
                    "context_per_slot": context,
                    "aggregate_context": context * effective_slots,
                    "active_slots": effective_slots,
                    "model_identity": identity,
                    "runtime_profile": runtime_profile,
                    "residency": residency,
                },
                sort_keys=True,
            )
        )
        return 0

    return run_benchmark(
        runtime="ollama",
        tag=tag,
        model=model,
        context=context,
        request=adapter,
        openai_chat=openai_chat_fn(
            f"{BASE}/v1", model,
            int(os.environ.get("AUDIT_BENCH_TIMEOUT", "7200")),
            reasoning_effort=effort or None,
        ),
        active_slots=effective_slots,
        kv_pool_tokens=context * effective_slots,
        runtime_metadata={
            "base_url": BASE,
            "model_identity": identity,
            "runtime_profile": runtime_profile,
            "residency": residency,
            "ollama_version": os.environ.get("OLLAMA_VERSION"),
            "capacity_source": "allocated context x effective slots",
        },
        provenance_files={
            "adapter": pathlib.Path(__file__).resolve(),
            "model_config": conf,
        },
    )


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:
        sys.exit(f"error: {error}")
