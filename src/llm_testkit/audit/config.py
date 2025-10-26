"""審計配置模組。

提供審計系統的配置模型與載入功能。
"""

from dataclasses import dataclass
from pathlib import Path

from llm_testkit.utils.config import load_yaml


@dataclass
class EndpointConfig:
    """API 端點配置。"""

    url: str
    model: str
    api_key: str | None = None
    supports_logprobs: bool = False

    def __post_init__(self):
        """驗證配置。"""
        if not self.url:
            raise ValueError("endpoint.url 不能為空")
        if not self.model:
            raise ValueError("endpoint.model 不能為空")


@dataclass
class TokenizerConfig:
    """分詞器配置。"""

    model_name_or_path: str

    def __post_init__(self):
        """驗證配置。"""
        if not self.model_name_or_path:
            raise ValueError("tokenizer.model_name_or_path 不能為空")


@dataclass
class DecodingConfig:
    """解碼參數配置。"""

    temperature: float = 0.0
    top_p: float = 1.0
    max_tokens: int = 128
    seed: int = 1234

    def __post_init__(self):
        """驗證配置。"""
        if not 0.0 <= self.temperature <= 2.0:
            raise ValueError(f"temperature 必須在 0.0-2.0 之間，當前值: {self.temperature}")
        if not 0.0 <= self.top_p <= 1.0:
            raise ValueError(f"top_p 必須在 0.0-1.0 之間，當前值: {self.top_p}")
        if self.max_tokens <= 0:
            raise ValueError(f"max_tokens 必須大於 0，當前值: {self.max_tokens}")


@dataclass
class ThresholdsConfig:
    """檢測閾值配置。"""

    fingerprint_avg_diff_pct: float = 2.0
    perturb_top1_change_pct: float = 20.0
    arithmetic_acc: float = 0.9
    json_valid_rate: float = 0.9
    style_fixed_prefix_rate: float = 0.2
    style_format_violation_rate: float = 0.1

    def __post_init__(self):
        """驗證配置。"""
        if self.fingerprint_avg_diff_pct < 0:
            raise ValueError("fingerprint_avg_diff_pct 必須 >= 0")
        if not 0.0 <= self.perturb_top1_change_pct <= 100.0:
            raise ValueError("perturb_top1_change_pct 必須在 0-100 之間")
        if not 0.0 <= self.arithmetic_acc <= 1.0:
            raise ValueError("arithmetic_acc 必須在 0.0-1.0 之間")
        if not 0.0 <= self.json_valid_rate <= 1.0:
            raise ValueError("json_valid_rate 必須在 0.0-1.0 之間")
        if not 0.0 <= self.style_fixed_prefix_rate <= 1.0:
            raise ValueError("style_fixed_prefix_rate 必須在 0.0-1.0 之間")
        if not 0.0 <= self.style_format_violation_rate <= 1.0:
            raise ValueError("style_format_violation_rate 必須在 0.0-1.0 之間")


@dataclass
class RunConfig:
    """執行配置。"""

    parallel: int = 1
    rate_limit_sleep: float = 0.2
    retries: int = 2
    timeout_sec: int = 60

    def __post_init__(self):
        """驗證配置。"""
        if self.parallel <= 0:
            raise ValueError(f"parallel 必須大於 0，當前值: {self.parallel}")
        if self.rate_limit_sleep < 0:
            raise ValueError(f"rate_limit_sleep 必須 >= 0，當前值: {self.rate_limit_sleep}")
        if self.retries < 0:
            raise ValueError(f"retries 必須 >= 0，當前值: {self.retries}")
        if self.timeout_sec <= 0:
            raise ValueError(f"timeout_sec 必須大於 0，當前值: {self.timeout_sec}")


@dataclass
class AuditConfig:
    """審計總配置。"""

    endpoint: EndpointConfig
    tokenizer: TokenizerConfig
    decoding: DecodingConfig
    suites: dict[str, list[str]]
    thresholds: ThresholdsConfig
    run: RunConfig
    control_endpoint: EndpointConfig | None = None

    @classmethod
    def from_yaml(cls, filepath: str | Path) -> "AuditConfig":
        """從 YAML 載入配置。

        Args:
            filepath: 配置檔路徑

        Returns:
            AuditConfig 實例

        Raises:
            FileNotFoundError: 配置檔不存在
            ValueError: 配置驗證失敗
        """
        config_dict = load_yaml(filepath)

        # 驗證必要區塊
        required_sections = ["endpoint", "tokenizer", "decoding", "suites", "thresholds", "run"]
        for section in required_sections:
            if section not in config_dict:
                raise ValueError(f"配置檔缺少必要區塊: {section}")

        # 解析 endpoint
        endpoint_data = config_dict["endpoint"]
        endpoint = EndpointConfig(**endpoint_data)

        # 解析 tokenizer
        tokenizer_data = config_dict["tokenizer"]
        tokenizer = TokenizerConfig(**tokenizer_data)

        # 解析 decoding
        decoding_data = config_dict.get("decoding", {})
        decoding = DecodingConfig(**decoding_data)

        # 解析 suites
        suites = config_dict["suites"]
        if not isinstance(suites, dict):
            raise ValueError("suites 必須是字典格式")
        if not suites:
            raise ValueError("suites 不能為空")

        # 解析 thresholds
        thresholds_data = config_dict.get("thresholds", {})
        thresholds = ThresholdsConfig(**thresholds_data)

        # 解析 run
        run_data = config_dict.get("run", {})
        run = RunConfig(**run_data)

        # 解析 control_endpoint（完全可選，不存在也不影響）
        control_endpoint = None
        if config_dict.get("control_endpoint") is not None:
            control_endpoint_data = config_dict["control_endpoint"]
            if isinstance(control_endpoint_data, dict):
                control_endpoint = EndpointConfig(**control_endpoint_data)

        return cls(
            endpoint=endpoint,
            tokenizer=tokenizer,
            decoding=decoding,
            suites=suites,
            thresholds=thresholds,
            run=run,
            control_endpoint=control_endpoint,
        )
