import socket
from typing import Any, Literal

import httpx
import openai
from openai import (
    DEFAULT_CONNECTION_LIMITS,
    DEFAULT_TIMEOUT,
    AsyncOpenAI,
    AuthenticationError,
    NotFoundError,
)
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


class OpenAICompatibleAPI:
    def __init__(
        self,
        model_name: str,
        base_url: str,
        api_key: str | None = None,
    ):
        """
        Initialize the OpenAI Compatible API client.

        Args:
            model_name (str): Name of the OpenAI model to use.
            base_url (str): Custom base URL for API requests.
            api_key (Optional[str]): API key for authentication.
        """
        if not base_url:
            raise ValueError("base_url must be provided")

        http_client = OpenAIAsyncHttpxClient()

        self.model = model_name

        try:
            self.client = AsyncOpenAI(
                api_key=api_key,
                base_url=base_url,
                http_client=http_client,
            )
        except Exception as e:
            raise RuntimeError(f"Failed to initialize OpenAI client: {e}") from e

    async def close(self) -> None:
        """
        Close the underlying HTTP client.
        """
        try:
            await self.client.close()
        except Exception as e:
            raise RuntimeError(f"Error closing OpenAI client: {e}") from e

    # 設定 API 重試機制（僅對可重試的錯誤進行重試）
    @retry(
        stop=stop_after_attempt(3),  # 最多重試 3 次
        wait=wait_exponential(multiplier=2, min=1, max=16),  # 指數回退機制
        retry=retry_if_exception_type(
            (
                openai.RateLimitError,  # 速率限制
                openai.APIConnectionError,  # API 連線失敗
                openai.APIStatusError,  # API 回應狀態碼異常
                openai.APITimeoutError,  # API 請求超時
            )
        ),
    )
    async def generate(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        tool_choice: Literal["none", "auto", "required"] | dict[str, Any] = "auto",
        max_tokens: int = 2048,
        temperature: float = 0.5,
        parallel_tool_calls: bool = True,
    ) -> Any:
        """
        Generate a response using the OpenAI chat completion API.

        Args:
            messages (List[Dict[str, Any]]): List of message dictionaries.
            tools (Optional[List[Dict[str, Any]]]): Optional list of tools.
            tool_choice: Tool choice strategy ("none", "auto", "required", or specific tool).
            max_tokens (int): Maximum number of tokens to generate.
            temperature (float): Sampling temperature.
            parallel_tool_calls (bool): Whether to enable parallel tool calls.

        Returns:
            API response object.

        Raises:
            AuthenticationError: If authentication fails.
            RuntimeError: If generation fails due to other errors.
        """

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=messages,  # type: ignore
                tools=tools,  # type: ignore
                tool_choice=tool_choice,  # type: ignore
                parallel_tool_calls=parallel_tool_calls,
            )
            return response
        except AuthenticationError as e:
            raise RuntimeError(f"Authentication error: {e}") from e
        except NotFoundError as e:
            raise RuntimeError(
                f"Model '{self.model}' not found at endpoint. "
                f"Please check the model name or API endpoint configuration. Error: {e}"
            ) from e
        except (
            openai.RateLimitError,
            openai.APIConnectionError,
            openai.APIStatusError,
            openai.APITimeoutError,
        ):
            raise
        except Exception as e:
            raise RuntimeError(f"Unexpected error during generation: {e}") from e


class OpenAIAsyncHttpxClient(httpx.AsyncClient):
    """Custom async client that deals better with long-running Async requests.

    Based on Anthropic DefaultAsyncHttpClient implementation that they
    released along with Claude 3.7 as well as the OpenAI DefaultAsyncHttpxClient

    """

    def __init__(self, **kwargs: Any) -> None:
        # This is based on the openai DefaultAsyncHttpxClient:
        # https://github.com/openai/openai-python/commit/347363ed67a6a1611346427bb9ebe4becce53f7e
        kwargs.setdefault("timeout", DEFAULT_TIMEOUT)
        kwargs.setdefault("limits", DEFAULT_CONNECTION_LIMITS)
        kwargs.setdefault("follow_redirects", True)

        # This is based on the anthrpopic changes for claude 3.7:
        # https://github.com/anthropics/anthropic-sdk-python/commit/c5387e69e799f14e44006ea4e54fdf32f2f74393#diff-3acba71f89118b06b03f2ba9f782c49ceed5bb9f68d62727d929f1841b61d12bR1387-R1403

        # set socket options to deal with long-running reasoning requests
        socket_options = [
            (socket.SOL_SOCKET, socket.SO_KEEPALIVE, True),
            (socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 60),
            (socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 5),
        ]
        TCP_KEEPIDLE = getattr(socket, "TCP_KEEPIDLE", None)
        if TCP_KEEPIDLE is not None:
            socket_options.append((socket.IPPROTO_TCP, TCP_KEEPIDLE, 60))

        kwargs["transport"] = httpx.AsyncHTTPTransport(
            limits=DEFAULT_CONNECTION_LIMITS,
            socket_options=socket_options,
        )

        super().__init__(**kwargs)
