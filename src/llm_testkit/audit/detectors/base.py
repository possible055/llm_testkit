"""Base classes for audit detectors.

This module defines the abstract interface that all detectors must implement,
along with the standard result format.
"""

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from typing import Any

from llm_testkit.audit.config import DecodingConfig, ThresholdsConfig
from llm_testkit.backend.openai_api import OpenAICompatibleAPI
from llm_testkit.core.tokenizer import Tokenizer


@dataclass
class DetectorResult:
    """Standard result format for detector execution.

    Attributes:
        name: Detector name identifier
        passed: Whether the detector test passed
        metrics: Dictionary of metric values computed by the detector
        notes: Optional notes or error messages
    """

    name: str
    passed: bool
    metrics: dict[str, Any]
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary format.

        Returns:
            Dictionary representation of the result
        """
        return asdict(self)


class BaseDetector(ABC):
    """Abstract base class for all detectors.

    All detectors must inherit from this class and implement the required
    abstract methods. This ensures a consistent interface across all detectors.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the detector name identifier.

        Returns:
            Unique name for this detector
        """
        ...

    @abstractmethod
    async def run(
        self,
        api: OpenAICompatibleAPI,
        tokenizer: Tokenizer,
        decoding: DecodingConfig,
        thresholds: ThresholdsConfig,
    ) -> DetectorResult:
        """Execute the detector test.

        Args:
            api: API client for making LLM requests
            tokenizer: Tokenizer for token counting and encoding
            decoding: Decoding parameters (temperature, top_p, etc.)
            thresholds: Threshold configuration for pass/fail determination

        Returns:
            DetectorResult containing test results and metrics
        """
        ...
