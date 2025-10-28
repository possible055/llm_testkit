"""分詞器指紋檢測器。

透過特製字串測試 API 回傳的 token 數量是否與本地分詞器一致，
用於判斷 API 服務商是否使用了宣稱的分詞器/模型家族。
"""

import asyncio

from llm_testkit.audit.config import DecodingConfig, ThresholdsConfig
from llm_testkit.audit.detectors.base import BaseDetector, DetectorResult
from llm_testkit.backend.openai_api import OpenAICompatibleAPI
from llm_testkit.core.tokenizer import Tokenizer


class TokenizerFingerprintDetector(BaseDetector):
    """分詞器指紋檢測器。

    使用包含空白、Unicode、Emoji、URL、CJK 混排的特製字串測試
    API 回傳的 prompt_tokens 是否與本地分詞器計算結果一致。

    檢測邏輯：
    1. 使用本地分詞器計算測試字串的 token 數
    2. 呼叫 API 並從 usage.prompt_tokens 取得遠端計算的 token 數
    3. 計算偏差百分比
    4. 若平均偏差超過閾值，標記為「高度懷疑非該家族」
    """

    # 測試字串集：涵蓋空白、ZWJ、Emoji、URL、CJK 混排等邊界情況
    FINGERPRINT_STRINGS = [
        "a a  a\n\n🙂http://例.com/路径?x=1#锚",
        "A" + (" " * 64) + "👨‍👩‍👦‍👦",
        "零寬連字元：a\u200db",
        "Emoji ZWJ: 👩\u200d💻👨\u200d👩\u200d👧\u200d👦",
    ]

    @property
    def name(self) -> str:
        """回傳檢測器名稱。"""
        return "tokenizer_fingerprint"

    async def run(
        self,
        api: OpenAICompatibleAPI,
        tokenizer: Tokenizer,
        decoding: DecodingConfig,
        thresholds: ThresholdsConfig,
    ) -> DetectorResult:
        """執行分詞器指紋檢測。

        Args:
            api: API 客戶端
            tokenizer: 本地分詞器
            decoding: 解碼參數
            thresholds: 閾值配置

        Returns:
            檢測結果，包含平均偏差百分比與樣本數
        """
        # 本地計算所有 token 數
        prompts = [f"請原樣回傳以下文字：\n{test_str}" for test_str in self.FINGERPRINT_STRINGS]
        local_counts = [tokenizer.count(prompt) for prompt in prompts]

        # 併發執行所有 API 呼叫
        tasks = []
        for prompt in prompts:
            messages = [{"role": "user", "content": prompt}]
            task = api.generate(
                messages=messages, temperature=decoding.temperature, max_tokens=decoding.max_tokens
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        diffs = []
        max_diff = 0.0
        failed_samples = 0
        no_usage_count = 0

        for local_count, result in zip(local_counts, results, strict=False):
            if isinstance(result, Exception):
                failed_samples += 1
                continue

            # 提取 usage.prompt_tokens
            try:
                remote_count = result.usage.prompt_tokens if result.usage else None  # type: ignore
            except AttributeError:
                remote_count = None

            if remote_count is None:
                no_usage_count += 1
                continue

            # 計算偏差百分比
            diff_pct = abs(local_count - remote_count) / max(1, local_count) * 100
            diffs.append(diff_pct)
            max_diff = max(max_diff, diff_pct)

        # 計算平均偏差
        avg_diff = sum(diffs) / len(diffs) if diffs else None
        success_rate = len(diffs) / len(prompts) if prompts else 0.0

        # 判定通過條件：有 usage 資訊且平均偏差在閾值內
        if avg_diff is None:
            passed = False
            if no_usage_count > 0:
                notes = f"API 未回傳 usage 資訊（{no_usage_count} 個樣本），無法驗證分詞器"
            else:
                notes = f"所有請求失敗（{failed_samples} 個樣本）"
        else:
            passed = avg_diff <= thresholds.fingerprint_avg_diff_pct
            notes = ""
            if failed_samples > 0:
                notes = f"警告：{failed_samples} 個樣本請求失敗"

        return DetectorResult(
            name=self.name,
            passed=passed,
            metrics={
                "avg_token_diff_pct": round(avg_diff, 2) if avg_diff is not None else None,
                "max_token_diff_pct": round(max_diff, 2) if diffs else None,
                "samples": len(diffs),
                "failed_samples": failed_samples,
                "success_rate": round(success_rate, 2),
                "threshold": thresholds.fingerprint_avg_diff_pct,
            },
            notes=notes,
        )
