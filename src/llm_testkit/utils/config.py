"""配置載入模組。

提供 YAML 配置檔的載入與管理功能。
支援從環境變數覆蓋配置值。
"""

import os
from pathlib import Path
from typing import Any

import yaml


class Config:
    """配置管理器。"""

    def __init__(self, config_dict: dict[str, Any]):
        """初始化配置。

        Args:
            config_dict: 配置字典
        """
        self._config = config_dict

    def get(self, key: str, default: Any = None) -> Any:
        """取得配置值（支援點號路徑）。

        Args:
            key: 配置鍵（例如：'generation.temperature'）
            default: 預設值

        Returns:
            配置值
        """
        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default

        return value

    def __getitem__(self, key: str) -> Any:
        """字典式存取。"""
        return self.get(key)

    def __contains__(self, key: str) -> bool:
        """檢查配置鍵是否存在。"""
        return self.get(key) is not None

    @property
    def raw(self) -> dict[str, Any]:
        """取得原始配置字典。"""
        return self._config


def _apply_env_overrides(config_dict: dict[str, Any]) -> dict[str, Any]:
    """從環境變數覆蓋配置值。

    支援的環境變數映射：
    - OPENAI_API_KEY -> llm.api_key
    - OPENAI_BASE_URL -> llm.base_url
    - ANTHROPIC_API_KEY -> anthropic.api_key
    - ANTHROPIC_BASE_URL -> anthropic.base_url
    - LOG_LEVEL -> logging.level

    Args:
        config_dict: 原始配置字典

    Returns:
        覆蓋後的配置字典
    """
    # 定義環境變數到配置路徑的映射
    env_mappings = {
        "OPENAI_API_KEY": ("llm", "api_key"),
        "OPENAI_BASE_URL": ("llm", "base_url"),
        "ANTHROPIC_API_KEY": ("anthropic", "api_key"),
        "ANTHROPIC_BASE_URL": ("anthropic", "base_url"),
        "LOG_LEVEL": ("logging", "level"),
    }

    for env_var, config_path in env_mappings.items():
        value = os.getenv(env_var)
        if value is not None:
            # 逐層建立巢狀字典並設定值
            current = config_dict
            for key in config_path[:-1]:
                if key not in current:
                    current[key] = {}
                current = current[key]
            current[config_path[-1]] = value

    return config_dict


def load_config(config_path: str | Path) -> Config:
    """載入 YAML 配置檔。

    會自動從環境變數覆蓋對應的配置值（如果環境變數存在）。

    Args:
        config_path: 配置檔路徑

    Returns:
        Config 實例
    """
    config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"配置檔不存在: {config_path}")

    with config_path.open("r", encoding="utf-8") as f:
        config_dict = yaml.safe_load(f)

    # 應用環境變數覆蓋
    config_dict = _apply_env_overrides(config_dict or {})

    return Config(config_dict)


def load_yaml(filepath: str | Path) -> dict[str, Any]:
    """載入 YAML 檔案為字典。

    Args:
        filepath: 檔案路徑

    Returns:
        解析後的字典
    """
    filepath = Path(filepath)

    if not filepath.exists():
        raise FileNotFoundError(f"檔案不存在: {filepath}")

    with filepath.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
