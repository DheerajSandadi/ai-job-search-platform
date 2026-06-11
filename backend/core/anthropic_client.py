from functools import lru_cache
import anthropic
import structlog
from core.config import settings

logger = structlog.get_logger()

HAIKU = "claude-haiku-4-5"
SONNET = "claude-sonnet-4-6"
OPUS = "claude-opus-4-6"


class AnthropicClient:
    def __init__(self) -> None:
        self._client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    def call_claude(
        self,
        model: str,
        system: str,
        user: str,
        max_tokens: int = 1024,
    ) -> str:
        logger.info("calling_claude", model=model, max_tokens=max_tokens)
        message = self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return message.content[0].text  # type: ignore[union-attr]


@lru_cache(maxsize=1)
def get_anthropic_client() -> AnthropicClient:
    return AnthropicClient()


anthropic_client = get_anthropic_client()
