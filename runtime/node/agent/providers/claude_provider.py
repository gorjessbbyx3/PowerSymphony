"""Anthropic Claude provider implementation."""

import base64
import os
from typing import Any, Dict, List, Optional

import anthropic
from anthropic import Anthropic

from entity.messages import (
    AttachmentRef,
    FunctionCallOutputEvent,
    Message,
    MessageBlock,
    MessageBlockType,
    MessageRole,
    ToolCallPayload,
)
from entity.tool_spec import ToolSpec
from runtime.node.agent import ModelProvider
from runtime.node.agent import ModelResponse
from utils.token_tracker import TokenUsage


class ClaudeProvider(ModelProvider):
    """Anthropic Claude provider implementation."""

    MAX_INLINE_FILE_BYTES = 50 * 1024 * 1024

    def create_client(self):
        """Create and return the Anthropic client."""
        kwargs: Dict[str, Any] = {}
        if self.api_key:
            kwargs["api_key"] = self.api_key
        if self.base_url:
            kwargs["base_url"] = self.base_url
        return Anthropic(**kwargs)

    def call_model(
        self,
        client: Anthropic,
        conversation: List[Message],
        timeline: List[Any],
        tool_specs: Optional[List[ToolSpec]] = None,
        **kwargs,
    ) -> ModelResponse:
        """Call Claude with the given conversation."""
        system_prompt, messages = self._build_messages(conversation)
        tools = self._build_tools(tool_specs) if tool_specs else []

        create_kwargs: Dict[str, Any] = {
            "model": self.model_name,
            "max_tokens": self.params.get("max_tokens", 8192),
            "messages": messages,
        }
        if system_prompt:
            create_kwargs["system"] = system_prompt
        if tools:
            create_kwargs["tools"] = tools
        if "temperature" in self.params:
            create_kwargs["temperature"] = self.params["temperature"]
        if "top_p" in self.params:
            create_kwargs["top_p"] = self.params["top_p"]

        response = client.messages.create(**create_kwargs)
        self._track_token_usage(response)
        self._append_response_to_timeline(timeline, response)
        message = self._deserialize_response(response)
        return ModelResponse(message=message, raw_response=response)

    def _build_messages(self, conversation: List[Message]):
        """Convert internal conversation format to Anthropic messages format."""
        system_parts = []
        messages = []

        for msg in conversation:
            role = msg.role
            if role == MessageRole.SYSTEM:
                for block in (msg.blocks or []):
                    if block.type == MessageBlockType.TEXT:
                        system_parts.append(block.text or "")
                continue

            anthropic_role = "assistant" if role == MessageRole.ASSISTANT else "user"
            content = self._serialize_blocks(msg.blocks or [], role)

            if not content:
                continue

            if messages and messages[-1]["role"] == anthropic_role:
                if isinstance(messages[-1]["content"], list):
                    messages[-1]["content"].extend(content)
                else:
                    messages[-1]["content"] = content
            else:
                messages.append({"role": anthropic_role, "content": content})

        system_prompt = "\n\n".join(system_parts) if system_parts else None
        return system_prompt, messages

    def _serialize_blocks(self, blocks: List[MessageBlock], role: MessageRole) -> List[Dict[str, Any]]:
        """Convert message blocks to Anthropic content format."""
        result = []
        for block in blocks:
            if block.type == MessageBlockType.TEXT:
                text = block.text or ""
                if text:
                    result.append({"type": "text", "text": text})

            elif block.type == MessageBlockType.TOOL_CALL:
                payload: ToolCallPayload = block.tool_call_payload
                if payload:
                    result.append({
                        "type": "tool_use",
                        "id": payload.call_id or f"call_{payload.function_name}",
                        "name": payload.function_name,
                        "input": payload.arguments or {},
                    })

            elif block.type == MessageBlockType.FUNCTION_CALL_OUTPUT:
                event: FunctionCallOutputEvent = block.function_call_output
                if event:
                    output_text = event.output_text or ""
                    result.append({
                        "type": "tool_result",
                        "tool_use_id": event.call_id or event.function_name or "tool_call",
                        "content": output_text,
                    })

            elif block.type == MessageBlockType.ATTACHMENT:
                ref: AttachmentRef = block.attachment_ref
                if ref and ref.path:
                    encoded = self._encode_file(ref.path)
                    if encoded:
                        mime = ref.mime_type or "image/png"
                        if mime.startswith("image/"):
                            result.append({
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": mime,
                                    "data": encoded,
                                },
                            })
                        else:
                            result.append({"type": "text", "text": f"[Attachment: {ref.path}]"})

        return result

    def _encode_file(self, path: str) -> Optional[str]:
        """Base64-encode a file for inline attachment."""
        try:
            size = os.path.getsize(path)
            if size > self.MAX_INLINE_FILE_BYTES:
                return None
            with open(path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        except Exception:
            return None

    def _build_tools(self, tool_specs: List[ToolSpec]) -> List[Dict[str, Any]]:
        """Convert ToolSpec objects to Anthropic tool format."""
        tools = []
        for spec in tool_specs:
            tool = {
                "name": spec.name,
                "description": spec.description or "",
                "input_schema": spec.parameters or {"type": "object", "properties": {}},
            }
            tools.append(tool)
        return tools

    def _append_response_to_timeline(self, timeline: List[Any], response: Any) -> None:
        """Append Claude response content blocks to the timeline."""
        if hasattr(response, "content"):
            timeline.extend(response.content)

    def _deserialize_response(self, response: Any) -> Message:
        """Convert Claude API response to internal Message format."""
        blocks = []
        tool_calls = []

        for block in getattr(response, "content", []):
            block_type = getattr(block, "type", None)

            if block_type == "text":
                blocks.append(MessageBlock(
                    type=MessageBlockType.TEXT,
                    text=block.text,
                ))

            elif block_type == "tool_use":
                call_payload = ToolCallPayload(
                    call_id=block.id,
                    function_name=block.name,
                    arguments=block.input if isinstance(block.input, dict) else {},
                )
                blocks.append(MessageBlock(
                    type=MessageBlockType.TOOL_CALL,
                    tool_call_payload=call_payload,
                ))
                tool_calls.append(call_payload)

        stop_reason = getattr(response, "stop_reason", None)

        return Message(
            role=MessageRole.ASSISTANT,
            blocks=blocks,
            tool_calls=tool_calls if tool_calls else None,
            finish_reason=stop_reason,
        )

    def extract_token_usage(self, response: Any) -> TokenUsage:
        """Extract token usage from Anthropic response."""
        usage = getattr(response, "usage", None)
        if not usage:
            return TokenUsage()
        return TokenUsage(
            input_tokens=getattr(usage, "input_tokens", 0) or 0,
            output_tokens=getattr(usage, "output_tokens", 0) or 0,
        )

    def _track_token_usage(self, response: Any) -> None:
        """Track token usage if tracker is available."""
        from utils.token_tracker import get_global_tracker
        tracker = get_global_tracker()
        if tracker:
            usage = self.extract_token_usage(response)
            tracker.add(usage)
