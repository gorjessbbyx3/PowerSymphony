"""Register built-in agent providers."""

from runtime.node.agent.providers.base import ProviderRegistry

from runtime.node.agent.providers.openai_provider import OpenAIProvider

ProviderRegistry.register(
    "openai",
    OpenAIProvider,
    label="OpenAI",
    summary="OpenAI models via the official OpenAI SDK (responses API)",
)

try:
    from runtime.node.agent.providers.claude_provider import ClaudeProvider
except ImportError:
    ClaudeProvider = None

if ClaudeProvider is not None:
    ProviderRegistry.register(
        "claude",
        ClaudeProvider,
        label="Anthropic Claude",
        summary="Anthropic Claude models (claude-opus-4-5, claude-sonnet-4-5, claude-haiku-3-5, etc.)",
    )
else:
    print("Claude provider not registered: anthropic library not found.")

try:
    from runtime.node.agent.providers.gemini_provider import GeminiProvider
except ImportError:
    GeminiProvider = None

if GeminiProvider is not None:
    ProviderRegistry.register(
        "gemini",
        GeminiProvider,
        label="Google Gemini",
        summary="Google Gemini models via google-genai",
    )
else:
    print("Gemini provider not registered: google-genai library not found.")
