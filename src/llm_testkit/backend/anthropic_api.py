import socket
from typing import Any

import anthropic
import httpx
from anthropic import DEFAULT_TIMEOUT, AsyncAnthropic
from anthropic._constants import DEFAULT_CONNECTION_LIMITS
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


class AnthropicAsyncHttpxClient(httpx.AsyncClient):
    """Custom async HTTP client optimized for long-running inference requests.

    Based on Anthropic SDK's DefaultAsyncHttpxClient implementation released
    with Claude 3.7. Configures TCP socket keepalive options to maintain
    long-running connections for extended thinking requests.
    """

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the HTTP client with socket keepalive configuration.

        Args:
            **kwargs: Additional keyword arguments passed to httpx.AsyncClient.
        """
        # Set default values from Anthropic SDK
        kwargs.setdefault("timeout", DEFAULT_TIMEOUT)
        kwargs.setdefault("limits", DEFAULT_CONNECTION_LIMITS)
        kwargs.setdefault("follow_redirects", True)

        # Configure socket options for long-running requests
        # Based on: https://github.com/anthropics/anthropic-sdk-python/commit/c5387e69e799f14e44006ea4e54fdf32f2f74393
        socket_options = [
            (socket.SOL_SOCKET, socket.SO_KEEPALIVE, True),
            (socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 60),
            (socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 5),
        ]

        # Add TCP_KEEPIDLE if supported by the OS
        TCP_KEEPIDLE = getattr(socket, "TCP_KEEPIDLE", None)
        if TCP_KEEPIDLE is not None:
            socket_options.append((socket.IPPROTO_TCP, TCP_KEEPIDLE, 60))

        # Create custom transport with socket options
        kwargs["transport"] = httpx.AsyncHTTPTransport(
            limits=DEFAULT_CONNECTION_LIMITS,
            socket_options=socket_options,
        )

        super().__init__(**kwargs)


class AnthropicAPI:
    """Anthropic API client for Claude models.

    Provides a consistent interface for interacting with Anthropic's Claude models,
    with automatic retry logic for transient errors and proper resource management.
    """

    def __init__(
        self,
        model_name: str,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        """Initialize the Anthropic API client.

        Args:
            model_name: Name of the Claude model to use (e.g., 'claude-sonnet-4-20250514').
            api_key: Anthropic API key. If None, will be read from environment variable.
            base_url: Custom API endpoint URL. If None, uses the default endpoint.

        Raises:
            RuntimeError: If client initialization fails.
        """
        # Create custom HTTP client with socket keepalive configuration
        http_client = AnthropicAsyncHttpxClient()

        # Store model name as instance attribute
        self.model = model_name

        try:
            # Initialize Anthropic client with custom HTTP client
            self.client = AsyncAnthropic(
                api_key=api_key,
                base_url=base_url,
                http_client=http_client,
            )
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Anthropic client: {e}") from e

    async def close(self) -> None:
        """Close the underlying HTTP client.

        Raises:
            RuntimeError: If an error occurs during client closure.
        """
        try:
            await self.client.close()
        except Exception as e:
            raise RuntimeError(f"Error closing Anthropic client: {e}") from e

    async def __aenter__(self) -> "AnthropicAPI":
        """Enter async context manager.

        Returns:
            The AnthropicAPI instance.
        """
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit async context manager and close the client.

        Args:
            exc_type: Exception type if an exception occurred.
            exc_val: Exception value if an exception occurred.
            exc_tb: Exception traceback if an exception occurred.
        """
        await self.close()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=1, max=16),
        retry=retry_if_exception_type(
            (
                anthropic.RateLimitError,
                anthropic.APIConnectionError,
                anthropic.APIStatusError,
                anthropic.APITimeoutError,
            )
        ),
    )
    async def generate(
        self,
        messages: list[dict[str, Any]],
        system: str | None = None,
        max_tokens: int = 2048,
        temperature: float = 0.5,
    ) -> Any:
        """Generate a response using the Anthropic API.

        This method automatically retries on transient errors (rate limits, connection
        issues, timeouts) using exponential backoff. Non-retryable errors like
        authentication failures are raised immediately.

        Args:
            messages: List of message dictionaries, each containing 'role' and 'content'.
            system: Optional system prompt to guide the model's behavior.
            max_tokens: Maximum number of tokens to generate (default: 2048).
            temperature: Sampling temperature between 0 and 1 (default: 0.5).

        Returns:
            The API response object (anthropic.types.Message).

        Raises:
            RuntimeError: If the API request fails after retries or encounters a
                non-retryable error (authentication, model not found, etc.).
        """
        try:
            # Prepare request parameters
            request_params: dict[str, Any] = {
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }

            # Add system prompt if provided
            if system is not None:
                request_params["system"] = system

            # Call Anthropic API
            response = await self.client.messages.create(**request_params)
            return response

        except anthropic.AuthenticationError as e:
            # Authentication errors should not be retried
            raise RuntimeError(f"Authentication error: {e}") from e

        except anthropic.NotFoundError as e:
            # Model not found errors should not be retried
            raise RuntimeError(
                f"Model '{self.model}' not found at endpoint. "
                f"Please check the model name or API endpoint configuration. Error: {e}"
            ) from e

        except (
            anthropic.RateLimitError,
            anthropic.APIConnectionError,
            anthropic.APIStatusError,
            anthropic.APITimeoutError,
        ):
            # These errors will be handled by the @retry decorator
            raise

        except Exception as e:
            # Wrap any other unexpected errors
            raise RuntimeError(f"Unexpected error during generation: {e}") from e
