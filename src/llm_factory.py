from __future__ import annotations

from langchain_ollama import ChatOllama
from config import Config


class LLMFactory:
    def __init__(self, config: Config = Config()):
        self.config = config

    def create(self, temperature: float, max_new_tokens: int) -> ChatOllama:
        return ChatOllama(
            model=self.config.OLLAMA_MODEL,
            base_url=self.config.OLLAMA_BASE_URL,
            temperature=temperature,
            num_predict=max_new_tokens,
        )

    def generator(self) -> ChatOllama:
        return self.create(self.config.GENERATOR_TEMP, self.config.GENERATOR_MAX_TOKENS)

    def validator(self) -> ChatOllama:
        return self.create(self.config.VALIDATOR_TEMP, self.config.VALIDATOR_MAX_TOKENS)