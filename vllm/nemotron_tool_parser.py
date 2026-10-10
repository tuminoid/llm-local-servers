# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the vLLM project

"""Streaming reasoning and tool-call parsers for NVIDIA Nemotron Nano v2.

Adapted from vLLM PR #42255 at commit
8c1e4ce022c15da262d3b2f6684c0faea32d89c1. The local changes accept the
checkpoint's truncated ``</TOOLCALL`` marker and repair malformed JSON strings
and container closers. The reasoning adapter fixes the Olmo3 parser's token-ID
transition for this tokenizer while retaining its string-buffered extraction.
"""

import json
import re
from collections.abc import Sequence
from typing import Any

from vllm.entrypoints.chat_utils import make_tool_call_id
from vllm.entrypoints.openai.chat_completion.protocol import (
    ChatCompletionRequest,
)
from vllm.entrypoints.generate.base.protocol import (
    DeltaFunctionCall,
    DeltaMessage,
    DeltaToolCall,
    ExtractedToolCallInformation,
    FunctionCall,
    ToolCall,
)
from vllm.entrypoints.openai.responses.protocol import ResponsesRequest
from vllm.logger import init_logger
from vllm.reasoning import ReasoningParserManager
from vllm.reasoning.olmo3_reasoning_parser import (
    Olmo3ReasoningParser,
    Olmo3ReasoningState,
)
from vllm.tokenizers import TokenizerLike
from vllm.tool_parsers import ToolParserManager
from vllm.tool_parsers.abstract_tool_parser import Tool, ToolParser
from vllm.tool_parsers.utils import partial_tag_overlap

logger = init_logger(__name__)

_JSON_ESCAPES = frozenset('"\\/bfnrt')
_JSON_CLOSER = {"{": "}", "[": "]"}


def _valid_json_escape(text: str, index: int) -> bool:
    if index >= len(text):
        return False
    char = text[index]
    if char in _JSON_ESCAPES:
        return True
    if char != "u" or index + 5 > len(text):
        return False
    return all(c in "0123456789abcdefABCDEF" for c in text[index + 1 : index + 5])


def _repair_json_strings(text: str) -> str:
    """Repair lone backslashes and quotes inside JSON strings."""
    output: list[str] = []
    in_string = False
    index = 0

    while index < len(text):
        char = text[index]
        if not in_string:
            output.append(char)
            if char == '"':
                in_string = True
            index += 1
            continue

        if char == "\\":
            run_end = index
            while run_end < len(text) and text[run_end] == "\\":
                run_end += 1
            run_length = run_end - index
            output.append("\\" * run_length)
            if run_length % 2:
                if not _valid_json_escape(text, run_end):
                    output.append("\\")
                elif text[run_end] == '"':
                    output.append('"')
                    index = run_end + 1
                    continue
            index = run_end
            continue

        if char == '"':
            next_index = index + 1
            while next_index < len(text) and text[next_index].isspace():
                next_index += 1
            if next_index == len(text) or text[next_index] in ":,}]":
                in_string = False
                output.append(char)
            else:
                output.append('\\"')
            index += 1
            continue

        output.append(char)
        index += 1

    if in_string:
        output.append('"')
    return "".join(output)


def _repair_json_structure(text: str) -> str:
    """Close missing containers and discard out-of-order extra closers."""
    output: list[str] = []
    stack: list[str] = []
    in_string = False
    escaped = False

    for char in text:
        if in_string:
            output.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
            output.append(char)
        elif char in _JSON_CLOSER:
            stack.append(char)
            output.append(char)
        elif char in "}]":
            opener = "{" if char == "}" else "["
            if opener not in stack:
                continue
            while stack[-1] != opener:
                output.append(_JSON_CLOSER[stack.pop()])
            stack.pop()
            output.append(char)
        else:
            output.append(char)

    while stack:
        output.append(_JSON_CLOSER[stack.pop()])
    return "".join(output)


def _repair_json(text: str) -> str:
    return _repair_json_structure(_repair_json_strings(text))


@ReasoningParserManager.register_module("nemotron_nano_v2")
class NemotronNanoV2ReasoningParser(Olmo3ReasoningParser):
    """Use Olmo3's string parser and its actual state for phase changes."""

    def is_reasoning_end(self, input_ids: Sequence[int]) -> bool:
        text = self.model_tokenizer.decode(list(input_ids))
        return self.think_end in text

    def is_reasoning_end_streaming(
        self,
        input_ids: Sequence[int],
        delta_ids: Sequence[int],
    ) -> bool:
        return self.buffer.state is Olmo3ReasoningState.CONTENT


@ToolParserManager.register_module("nemotron_nano_v2")
class NemotronNanoV2ToolParser(ToolParser):
    """Parse Nemotron Nano v2 ``<TOOLCALL>`` JSON."""

    def __init__(
        self,
        tokenizer: TokenizerLike,
        tools: list[Tool] | None = None,
    ):
        super().__init__(tokenizer, tools)

        self.tool_call_start_token = "<TOOLCALL>"
        self.tool_call_end_prefix = "</TOOLCALL"
        self.tool_call_regex = re.compile(
            rf"{re.escape(self.tool_call_start_token)}"
            rf"(.*?){re.escape(self.tool_call_end_prefix)}>?",
            re.DOTALL,
        )
        self._sent_content_idx = 0
        self._tool_calls_emitted = False

    def adjust_request(
        self,
        request: ChatCompletionRequest | ResponsesRequest,
    ) -> ChatCompletionRequest | ResponsesRequest:
        request = super().adjust_request(request)
        if request.tools and request.tool_choice != "none":
            request.skip_special_tokens = False
        return request

    @staticmethod
    def _normalize_tool_call_payload(payload: str) -> list[dict[str, Any]]:
        payload = payload.strip()
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError:
            repaired = _repair_json(payload)
            parsed = json.loads(repaired)
            logger.warning(
                "Repaired malformed Nemotron tool-call payload."
            )

        if isinstance(parsed, dict):
            return [parsed]
        if not isinstance(parsed, list) or not all(
            isinstance(item, dict) for item in parsed
        ):
            raise ValueError("Nemotron tool-call payload is not an object array")
        return parsed

    @staticmethod
    def _serialize_arguments(arguments: Any) -> str:
        if isinstance(arguments, str):
            return arguments
        return json.dumps(arguments, ensure_ascii=False)

    def extract_tool_calls(
        self,
        model_output: str,
        request: ChatCompletionRequest,
    ) -> ExtractedToolCallInformation:
        if self.tool_call_start_token not in model_output:
            return ExtractedToolCallInformation(
                tools_called=False,
                tool_calls=[],
                content=model_output,
            )

        payloads = self.tool_call_regex.findall(model_output)
        tool_calls: list[ToolCall] = []
        try:
            for payload in payloads:
                for raw_tool_call in self._normalize_tool_call_payload(payload):
                    name = raw_tool_call.get("name")
                    if (
                        not isinstance(name, str)
                        or not name
                        or "arguments" not in raw_tool_call
                    ):
                        logger.warning("Ignored invalid Nemotron tool call.")
                        continue
                    tool_calls.append(
                        ToolCall(
                            type="function",
                            function=FunctionCall(
                                name=name,
                                arguments=self._serialize_arguments(
                                    raw_tool_call["arguments"]
                                ),
                            ),
                        )
                    )
        except (json.JSONDecodeError, ValueError):
            logger.exception("Failed to parse Nemotron tool-call payload.")
            return ExtractedToolCallInformation(
                tools_called=False,
                tool_calls=[],
                content=model_output,
            )

        if not tool_calls:
            return ExtractedToolCallInformation(
                tools_called=False,
                tool_calls=[],
                content=model_output,
            )

        content = model_output[: model_output.find(self.tool_call_start_token)]
        return ExtractedToolCallInformation(
            tools_called=True,
            tool_calls=tool_calls,
            content=content or None,
        )

    def extract_tool_calls_streaming(
        self,
        previous_text: str,
        current_text: str,
        delta_text: str,
        previous_token_ids: Sequence[int],
        current_token_ids: Sequence[int],
        delta_token_ids: Sequence[int],
        request: ChatCompletionRequest,
    ) -> DeltaMessage | None:
        if not previous_text:
            self.current_tool_id = -1
            self.current_tool_name_sent = False
            self.streamed_args_for_tool = []
            self._sent_content_idx = 0
            self._tool_calls_emitted = False

        start_idx = current_text.find(self.tool_call_start_token)
        if start_idx == -1:
            overlap = partial_tag_overlap(
                current_text,
                self.tool_call_start_token,
            )
            sendable_idx = len(current_text) - overlap
            if sendable_idx > self._sent_content_idx:
                content = current_text[self._sent_content_idx : sendable_idx]
                self._sent_content_idx = sendable_idx
                return DeltaMessage(content=content)
            return None

        content_delta: str | None = None
        if self._sent_content_idx < start_idx:
            content_delta = current_text[self._sent_content_idx : start_idx]
            self._sent_content_idx = start_idx

        payload_start = start_idx + len(self.tool_call_start_token)
        payload_end = current_text.find(
            self.tool_call_end_prefix,
            payload_start,
        )
        if payload_end == -1 or self._tool_calls_emitted:
            return (
                DeltaMessage(content=content_delta)
                if content_delta is not None
                else None
            )

        payload = current_text[payload_start:payload_end]
        try:
            parsed_tool_calls = self._normalize_tool_call_payload(payload)
        except (json.JSONDecodeError, ValueError):
            logger.exception(
                "Failed to parse completed Nemotron tool-call payload."
            )
            self._tool_calls_emitted = True
            raw_block = current_text[start_idx:]
            return DeltaMessage(
                content=(content_delta or "") + raw_block,
            )

        tool_call_deltas: list[DeltaToolCall] = []
        valid_tool_calls: list[dict[str, Any]] = []
        streamed_arguments: list[str] = []
        for raw_tool_call in parsed_tool_calls:
            name = raw_tool_call.get("name")
            if (
                not isinstance(name, str)
                or not name
                or "arguments" not in raw_tool_call
            ):
                logger.warning("Ignored invalid Nemotron tool call.")
                continue
            arguments = self._serialize_arguments(raw_tool_call["arguments"])
            index = len(tool_call_deltas)
            tool_call_deltas.append(
                DeltaToolCall(
                    index=index,
                    id=make_tool_call_id(),
                    type="function",
                    function=DeltaFunctionCall(
                        name=name,
                        arguments=arguments,
                    ),
                )
            )
            valid_tool_calls.append(raw_tool_call)
            streamed_arguments.append(arguments)

        self._tool_calls_emitted = True
        self.current_tool_id = len(tool_call_deltas) - 1
        self.current_tool_name_sent = bool(tool_call_deltas)
        self.prev_tool_call_arr = valid_tool_calls
        self.streamed_args_for_tool = streamed_arguments
        if not tool_call_deltas:
            logger.warning("No valid calls in Nemotron tool-call payload.")
            return DeltaMessage(
                content=(content_delta or "") + current_text[start_idx:],
            )
        if content_delta is not None or tool_call_deltas:
            return DeltaMessage(
                content=content_delta,
                tool_calls=tool_call_deltas or None,
            )
        return None
