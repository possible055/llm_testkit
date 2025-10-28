"""算術與 JSON 結構完整性檢測器。

測試模型的算術能力與結構化輸出能力，用於檢測量化對精確任務的影響。
透過產生算術測題與 JSON 格式要求，驗證模型的數值計算與格式遵循能力。
"""

import asyncio
import random

from llm_testkit.audit.config import DecodingConfig, ThresholdsConfig
from llm_testkit.audit.detectors.base import BaseDetector, DetectorResult
from llm_testkit.backend.openai_api import OpenAICompatibleAPI
from llm_testkit.core.metrics import extract_first_int, json_valid
from llm_testkit.core.tokenizer import Tokenizer


class ArithmeticJsonDetector(BaseDetector):
    """算術與 JSON 結構完整性檢測器。

    測試模型在精確任務上的表現，包括：
    1. 算術測試：2-4 位數的乘法運算
    2. JSON 測試：結構化輸出的合法性

    檢測邏輯：
    1. 產生 20 題 2 位數乘法測題（使用固定種子確保可重複）
    2. 要求模型輸出嚴格格式（只輸出整數）
    3. 使用 extract_first_int() 提取答案並比對
    4. 要求模型產生 JSON 格式輸出並驗證合法性
    5. 計算算術正確率與 JSON 合法率
    6. 若相較基線掉分超過閾值，標記為「量化影響或強制後處理」
    """

    @property
    def name(self) -> str:
        """回傳檢測器名稱。"""
        return "arithmetic_json"

    async def run(
        self,
        api: OpenAICompatibleAPI,
        tokenizer: Tokenizer,
        decoding: DecodingConfig,
        thresholds: ThresholdsConfig,
    ) -> DetectorResult:
        """執行算術與 JSON 檢測。

        Args:
            api: API 客戶端
            tokenizer: 分詞器
            decoding: 解碼參數
            thresholds: 閾值配置

        Returns:
            檢測結果，包含算術正確率與 JSON 合法率
        """
        # 產生算術測題
        arithmetic_total = 20
        rng = random.Random(1234)

        test_cases = []
        for _ in range(arithmetic_total):
            a = rng.randint(12, 97)
            b = rng.randint(12, 97)
            expected = a * b
            prompt = f"Multiply {a}×{b}. Output only the integer."
            test_cases.append((prompt, expected))

        # 加入 JSON 測試
        json_prompt = 'Complete valid JSON with keys ["id","name","tags"]. Output JSON only.'

        # 併發執行所有 API 呼叫（算術 + JSON）
        tasks = [self._call_api(api, prompt, decoding) for prompt, _ in test_cases]
        tasks.append(self._call_api(api, json_prompt, decoding))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 處理算術測試結果
        arithmetic_correct = 0
        arithmetic_failed = 0
        for (_, expected), result in zip(test_cases, results[:arithmetic_total], strict=False):
            if isinstance(result, Exception):
                arithmetic_failed += 1
                continue

            # 確保 result 是字串
            if isinstance(result, str):
                extracted = extract_first_int(result)
                if extracted == expected:
                    arithmetic_correct += 1

        arithmetic_valid = arithmetic_total - arithmetic_failed
        arithmetic_acc = arithmetic_correct / arithmetic_valid if arithmetic_valid > 0 else 0.0
        arithmetic_success_rate = (
            arithmetic_valid / arithmetic_total if arithmetic_total > 0 else 0.0
        )

        # 處理 JSON 測試結果
        json_result = results[-1]
        json_failed = isinstance(json_result, Exception)

        if json_failed:
            json_ok = False
            notes = f"JSON 測試請求失敗: {str(json_result)}"
        else:
            # 確保 json_result 是字串
            json_ok = json_valid(json_result) if isinstance(json_result, str) else False
            notes = ""

        if arithmetic_failed > 0:
            if notes:
                notes += f"; 算術測試：{arithmetic_failed} 個樣本請求失敗"
            else:
                notes = f"警告：算術測試 {arithmetic_failed} 個樣本請求失敗"

        # 判定通過條件：算術正確率與 JSON 合法率均達標
        passed = arithmetic_acc >= thresholds.arithmetic_acc and json_ok and arithmetic_valid > 0

        return DetectorResult(
            name=self.name,
            passed=passed,
            metrics={
                "arithmetic_acc": round(arithmetic_acc, 2),
                "arithmetic_correct": arithmetic_correct,
                "arithmetic_total": arithmetic_valid,
                "arithmetic_failed": arithmetic_failed,
                "arithmetic_success_rate": round(arithmetic_success_rate, 2),
                "json_valid_sample": bool(json_ok),
                "json_failed": json_failed,
                "threshold_arithmetic": thresholds.arithmetic_acc,
                "threshold_json": thresholds.json_valid_rate,
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
