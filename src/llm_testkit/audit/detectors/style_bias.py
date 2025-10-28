"""風格偏移檢測器。

測試模型輸出的風格偏移，用於識別微調導致的行為變化。
透過使用強格式要求的提示，檢測模型是否產生固定前言或違反格式要求。
"""

import asyncio
import re

from llm_testkit.audit.config import DecodingConfig, ThresholdsConfig
from llm_testkit.audit.detectors.base import BaseDetector, DetectorResult
from llm_testkit.backend.openai_api import OpenAICompatibleAPI
from llm_testkit.core.tokenizer import Tokenizer


class StyleBiasDetector(BaseDetector):
    """風格偏移檢測器。

    使用強格式要求的提示（如「No preface」「Output JSON only」）進行測試，
    檢測模型輸出是否包含固定前言或違反格式要求。

    檢測邏輯：
    1. 使用強格式要求的提示進行測試
    2. 檢測輸出是否包含固定前綴（如「Sure」「As an AI」「抱歉」）
    3. 檢測輸出是否違反格式要求（應以項目符號開頭）
    4. 計算固定前綴出現率與格式違規比例
    5. 若固定前綴出現率或格式違規率超過閾值，標記為「微調可能性上升」
    """

    # 強格式要求提示集：涵蓋中英文、不同格式要求
    PROMPTS = [
        "State 3 risks of overfitting. No preface. 3 bullet points only.",
        "列出兩項 L2 正則化的代價。不要任何前言或結語。只輸出兩個項目。",
    ]

    # 固定前綴模式：檢測常見的禮貌性前言或拒答措辭
    FIXED_PREFIX_PATTERNS = [
        r"(?i)^sure[, ]|^of course|^as an ai",
        r"^(抱歉|很抱歉|我無法)",
    ]

    @property
    def name(self) -> str:
        """回傳檢測器名稱。"""
        return "style_bias"

    async def run(
        self,
        api: OpenAICompatibleAPI,
        tokenizer: Tokenizer,
        decoding: DecodingConfig,
        thresholds: ThresholdsConfig,
    ) -> DetectorResult:
        """執行風格偏移檢測。

        Args:
            api: API 客戶端
            tokenizer: 分詞器
            decoding: 解碼參數
            thresholds: 閾值配置

        Returns:
            檢測結果，包含固定前綴出現率與格式違規率
        """
        # 併發執行所有 API 呼叫
        tasks = [self._call_api(api, prompt, decoding) for prompt in self.PROMPTS]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        prefix_hits = 0
        format_violations = 0
        failed_samples = 0
        total = len(self.PROMPTS)

        for result in results:
            if isinstance(result, Exception):
                failed_samples += 1
                continue

            response = result.strip()

            # 檢查固定前綴
            if any(re.search(pat, response) for pat in self.FIXED_PREFIX_PATTERNS):
                prefix_hits += 1

            # 檢查格式（應以項目符號開頭）
            # 支援常見的項目符號格式：-, *, •, 數字編號
            if not re.match(r"^[-*•\d]", response):
                format_violations += 1

        # 計算指標（排除失敗樣本）
        valid_samples = total - failed_samples
        prefix_rate = prefix_hits / valid_samples if valid_samples > 0 else 0.0
        violation_rate = format_violations / valid_samples if valid_samples > 0 else 0.0
        success_rate = valid_samples / total if total > 0 else 0.0

        # 判定通過條件：固定前綴出現率與格式違規率均在閾值內
        passed = not (
            prefix_rate > thresholds.style_fixed_prefix_rate
            or violation_rate > thresholds.style_format_violation_rate
        )

        notes = ""
        if failed_samples > 0:
            notes = f"警告：{failed_samples} 個樣本請求失敗"
            if valid_samples == 0:
                passed = False
                notes = f"所有請求失敗（{failed_samples} 個樣本）"

        return DetectorResult(
            name=self.name,
            passed=passed,
            metrics={
                "fixed_prefix_rate": round(prefix_rate, 2),
                "format_violation_rate": round(violation_rate, 2),
                "failed_samples": failed_samples,
                "success_rate": round(success_rate, 2),
                "threshold_prefix": thresholds.style_fixed_prefix_rate,
                "threshold_violation": thresholds.style_format_violation_rate,
            },
            notes=notes,
        )

    async def _call_api(
        self, api: OpenAICompatibleAPI, prompt: str, decoding: DecodingConfig
    ) -> str:
        """呼叫 API 並回傳回應內容。

        Args:
            api: API 客戶端
            prompt: 提示文字
            decoding: 解碼參數

        Returns:
            API 回應的文字內容
        """
        messages = [{"role": "user", "content": prompt}]
        response = await api.generate(
            messages=messages, temperature=decoding.temperature, max_tokens=decoding.max_tokens
        )
        return response.choices[0].message.content
