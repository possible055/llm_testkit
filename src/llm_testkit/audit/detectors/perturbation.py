"""微擾穩定性檢測器。

測試模型對微小輸入擾動的穩定性，用於檢測低比特量化的跡象。
透過比較原始提示與擾動版本的輸出差異，計算 Top-1 變更率與 Hamming 距離。
"""

import asyncio

from llm_testkit.audit.config import DecodingConfig, ThresholdsConfig
from llm_testkit.audit.detectors.base import BaseDetector, DetectorResult
from llm_testkit.backend.openai_api import OpenAICompatibleAPI
from llm_testkit.core.metrics import hamming_distance
from llm_testkit.core.tokenizer import Tokenizer


class PerturbationDetector(BaseDetector):
    """微擾穩定性檢測器。

    對每個基礎提示產生微小擾動版本（末尾空白、換行、同義替換），
    在 temperature=0 下比較原始與擾動版本的輸出差異。

    檢測邏輯：
    1. 對每個基礎提示產生擾動版本
    2. 在 temperature=0 下呼叫 API 獲取原始與擾動版本的回應
    3. 分詞並比較首 token 與前 10 個 token 的差異
    4. 計算 Top-1 變更率與平均 Hamming 距離
    5. 若 Top-1 變更率超過閾值，標記為「低比特量化或粗糙解碼核跡象」
    """

    # 基礎提示集：涵蓋中英文、不同長度與任務類型
    BASE_PROMPTS = [
        "Explain dropout in one sentence.",
        "給我三個過擬合風險。輸出三個項目符號，禁止前言。",
        "Summarize: Transformers enable parallel sequence modeling.",
        "以繁體中文回答：為何 BatchNorm 有時會害推論不穩？一句話。",
    ]

    @property
    def name(self) -> str:
        """回傳檢測器名稱。"""
        return "perturbation"

    async def run(
        self,
        api: OpenAICompatibleAPI,
        tokenizer: Tokenizer,
        decoding: DecodingConfig,
        thresholds: ThresholdsConfig,
    ) -> DetectorResult:
        """執行微擾穩定性檢測。

        Args:
            api: API 客戶端
            tokenizer: 分詞器
            decoding: 解碼參數
            thresholds: 閾值配置

        Returns:
            檢測結果，包含 Top-1 變更率、平均 Hamming 距離與測試對數
        """
        # 準備所有 API 呼叫任務
        tasks = []
        for base_prompt in self.BASE_PROMPTS:
            # 產生擾動版本
            perturbed_prompts = [
                base_prompt + " ",  # 末尾空白
                base_prompt + "\n",  # 末尾換行
                self._apply_synonym_replacement(base_prompt),  # 同義替換
            ]

            # 加入原始提示和所有擾動版本的呼叫任務
            tasks.append((base_prompt, self._call_api(api, base_prompt, decoding)))
            for pert_prompt in perturbed_prompts:
                tasks.append((pert_prompt, self._call_api(api, pert_prompt, decoding)))

        # 併發執行所有 API 呼叫
        results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)

        # 建立 prompt -> response 的映射
        response_map = {}
        for (prompt, _), result in zip(tasks, results, strict=False):
            if not isinstance(result, Exception):
                response_map[prompt] = result

        # 計算指標
        top1_changes = 0
        total_pairs = 0
        hamming_sum = 0
        failed_samples = len(tasks) - len(response_map)

        for base_prompt in self.BASE_PROMPTS:
            base_resp = response_map.get(base_prompt)
            if not base_resp:
                continue

            base_tokens = tokenizer.tokenize(base_resp)

            # 產生擾動版本（與上面相同）
            perturbed_prompts = [
                base_prompt + " ",
                base_prompt + "\n",
                self._apply_synonym_replacement(base_prompt),
            ]

            for pert_prompt in perturbed_prompts:
                pert_resp = response_map.get(pert_prompt)
                if not pert_resp:
                    continue

                pert_tokens = tokenizer.tokenize(pert_resp)

                # 比較首 token
                if base_tokens and pert_tokens:
                    if base_tokens[0] != pert_tokens[0]:
                        top1_changes += 1

                    # 計算 Hamming 距離（前 10 個 token）
                    hamming_sum += hamming_distance(base_tokens, pert_tokens, k=10)

                total_pairs += 1

        # 計算指標
        top1_change_pct = (top1_changes / total_pairs * 100) if total_pairs else 0
        avg_hamming = hamming_sum / total_pairs if total_pairs else 0
        success_rate = len(response_map) / len(tasks) if tasks else 0.0

        # 判定通過條件：Top-1 變更率在閾值內
        passed = top1_change_pct <= thresholds.perturb_top1_change_pct

        notes = ""
        if failed_samples > 0:
            notes = f"警告：{failed_samples} 個樣本請求失敗"
            if total_pairs == 0:
                passed = False
                notes = f"所有請求失敗（{failed_samples} 個樣本）"

        return DetectorResult(
            name=self.name,
            passed=passed,
            metrics={
                "top1_change_pct": round(top1_change_pct, 2),
                "avg_hamming@10": round(avg_hamming, 2),
                "pairs": total_pairs,
                "failed_samples": failed_samples,
                "success_rate": round(success_rate, 2),
                "threshold": thresholds.perturb_top1_change_pct,
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

    def _apply_synonym_replacement(self, text: str) -> str:
        """應用簡單的同義替換。

        Args:
            text: 原始文字

        Returns:
            替換後的文字
        """
        # 簡單的同義詞替換規則
        replacements = {"three": "3", "三個": "3個", "one": "1", "一句話": "1句話"}

        result = text
        for old, new in replacements.items():
            result = result.replace(old, new)

        return result
