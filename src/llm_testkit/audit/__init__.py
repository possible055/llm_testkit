"""LLM API 黑盒審計模組

此模組提供 LLM API 黑盒測試能力，用於驗證第三方 API 服務商提供的模型是否與其宣稱的模型一致。
透過「分詞器指紋 + 壓力測試 + 分佈檢查」三層交叉驗證，檢測模型是否被微調、量化或替換。
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from llm_testkit.audit.config import AuditConfig
    from llm_testkit.audit.detectors import BaseDetector, DetectorResult
    from llm_testkit.audit.runner import AuditRunner

__all__ = [
    "AuditConfig",
    "AuditRunner",
    "BaseDetector",
    "DetectorResult",
]


def __getattr__(name: str):
    """延遲導入以避免循環依賴。"""
    if name == "AuditConfig":
        from llm_testkit.audit.config import AuditConfig

        return AuditConfig
    elif name == "BaseDetector":
        from llm_testkit.audit.detectors import BaseDetector

        return BaseDetector
    elif name == "DetectorResult":
        from llm_testkit.audit.detectors import DetectorResult

        return DetectorResult
    elif name == "AuditRunner":
        from llm_testkit.audit.runner import AuditRunner

        return AuditRunner
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
