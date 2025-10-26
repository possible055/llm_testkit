"""審計執行器模組。

提供審計系統的核心執行邏輯，協調 API 客戶端、分詞器與檢測器。
"""

from datetime import datetime
from pathlib import Path

from llm_testkit.audit.config import AuditConfig
from llm_testkit.audit.detectors import (
    ArithmeticJsonDetector,
    BaseDetector,
    DetectorResult,
    PerturbationDetector,
    StyleBiasDetector,
    TokenizerFingerprintDetector,
)
from llm_testkit.backend.openai_api import OpenAICompatibleAPI
from llm_testkit.core.tokenizer import Tokenizer
from llm_testkit.utils.io import write_json
from llm_testkit.utils.logging import setup_logger


class AuditRunner:
    """審計執行器。

    協調所有審計組件，執行檢測器並產生報告。

    Attributes:
        config: 審計配置
        logger: 日誌記錄器
        api: API 客戶端
        tokenizer: 分詞器
        detectors: 檢測器註冊表
    """

    def __init__(self, config: AuditConfig):
        """初始化審計執行器。

        Args:
            config: 審計配置
        """
        self.config = config
        self.logger = setup_logger("audit", level="INFO")

        # 初始化 API 客戶端（重用現有類別）
        self.logger.info(f"初始化 API 客戶端: {config.endpoint.url}")
        self.api = OpenAICompatibleAPI(
            model_name=config.endpoint.model,
            base_url=config.endpoint.url,
            api_key=config.endpoint.api_key,
        )

        # 初始化分詞器
        self.logger.info(f"初始化分詞器: {config.tokenizer.model_name_or_path}")
        self.tokenizer = Tokenizer(model_name_or_path=config.tokenizer.model_name_or_path)

        # 註冊檢測器
        self.detectors: dict[str, BaseDetector] = {
            "tokenizer_fingerprint": TokenizerFingerprintDetector(),
            "perturbation": PerturbationDetector(),
            "arithmetic_json": ArithmeticJsonDetector(),
            "style_bias": StyleBiasDetector(),
        }

        self.logger.info(f"已註冊 {len(self.detectors)} 個檢測器")

    async def run_suite(self, suite_name: str) -> list[DetectorResult]:
        """執行測試套件。

        依序執行套件中的所有檢測器，單一檢測器失敗不影響其他檢測器。

        Args:
            suite_name: 套件名稱（如 "quick"）

        Returns:
            檢測結果列表

        Raises:
            ValueError: 套件名稱不存在
        """
        if suite_name not in self.config.suites:
            available = ", ".join(self.config.suites.keys())
            raise ValueError(f"測試套件 '{suite_name}' 不存在。可用套件: {available}")

        detector_names = self.config.suites[suite_name]
        results = []

        print(f"\n{'=' * 70}")
        print(f"開始執行測試套件: {suite_name}")
        print(f"包含 {len(detector_names)} 個檢測器")
        print(f"{'=' * 70}\n")

        for idx, name in enumerate(detector_names, 1):
            detector = self.detectors.get(name)

            if not detector:
                print(f"[{idx}/{len(detector_names)}] ⚠️  檢測器 '{name}' 不存在，跳過")
                results.append(
                    DetectorResult(
                        name=name, passed=False, metrics={}, notes=f"檢測器 '{name}' 未註冊"
                    )
                )
                continue

            print(f"[{idx}/{len(detector_names)}] 🔄 執行檢測器: {name}")

            try:
                result = await detector.run(
                    api=self.api,
                    tokenizer=self.tokenizer,
                    decoding=self.config.decoding,
                    thresholds=self.config.thresholds,
                )
                results.append(result)

                # 顯示結果
                status_icon = "✅" if result.passed else "❌"
                status_text = "通過" if result.passed else "失敗"
                print(f"[{idx}/{len(detector_names)}] {status_icon} {name}: {status_text}")

                # 顯示關鍵指標
                self._print_metrics_summary(result)

                if result.notes:
                    print(f"     ⚠️  {result.notes}")

                print()  # 空行分隔

            except Exception as e:
                print(f"[{idx}/{len(detector_names)}] ❌ {name}: 執行錯誤")
                print(f"     錯誤: {str(e)}")
                print()
                self.logger.error(f"檢測器 '{name}' 執行失敗: {e}", exc_info=True)
                results.append(
                    DetectorResult(name=name, passed=False, metrics={}, notes=f"執行錯誤: {str(e)}")
                )

        # 統計結果
        passed_count = sum(1 for r in results if r.passed)
        total_count = len(results)

        print(f"{'=' * 70}")
        print(f"測試套件完成: {passed_count}/{total_count} 通過")
        print(f"{'=' * 70}\n")

        return results

    def _print_metrics_summary(self, result: DetectorResult) -> None:
        """顯示檢測器指標摘要。

        Args:
            result: 檢測結果
        """
        # 根據檢測器類型顯示關鍵指標
        if result.name == "tokenizer_fingerprint":
            avg_diff = result.metrics.get("avg_token_diff_pct")
            threshold = result.metrics.get("threshold")
            samples = result.metrics.get("samples", 0)
            if avg_diff is not None:
                print(f"     平均偏差: {avg_diff}% (閾值: ≤{threshold}%) | 樣本數: {samples}")

        elif result.name == "perturbation":
            top1_pct = result.metrics.get("top1_change_pct")
            threshold = result.metrics.get("threshold")
            pairs = result.metrics.get("pairs", 0)
            if top1_pct is not None:
                print(f"     Top-1 變更率: {top1_pct}% (閾值: ≤{threshold}%) | 測試對數: {pairs}")

        elif result.name == "arithmetic_json":
            arith_acc = result.metrics.get("arithmetic_acc")
            json_valid = result.metrics.get("json_valid_sample")
            threshold = result.metrics.get("threshold_arithmetic")
            if arith_acc is not None:
                print(
                    f"     算術正確率: {arith_acc} (閾值: ≥{threshold}) | JSON 合法: {json_valid}"
                )

        elif result.name == "style_bias":
            prefix_rate = result.metrics.get("fixed_prefix_rate")
            violation_rate = result.metrics.get("format_violation_rate")
            threshold_prefix = result.metrics.get("threshold_prefix")
            threshold_violation = result.metrics.get("threshold_violation")
            if prefix_rate is not None:
                print(
                    f"     固定前綴率: {prefix_rate} (閾值: ≤{threshold_prefix}) | 格式違規率: {violation_rate} (閾值: ≤{threshold_violation})"
                )

    def generate_report(self, results: list[DetectorResult], output_dir: str | Path) -> None:
        """產生報告。

        產生 JSON 與 Markdown 兩種格式的報告。

        Args:
            results: 檢測結果列表
            output_dir: 輸出目錄
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().isoformat()

        # JSON 報告（重用現有 IO 工具）
        report_data = {
            "timestamp": timestamp,
            "endpoint": {"url": self.config.endpoint.url, "model": self.config.endpoint.model},
            "results": [r.to_dict() for r in results],
        }

        json_path = output_dir / "report.json"
        write_json(report_data, json_path)
        self.logger.info(f"JSON 報告已產生: {json_path}")

        # Markdown 報告
        md_lines = [
            "# LLM API 審計報告",
            "",
            "## 基本資訊",
            "",
            f"- **時間戳記:** {timestamp}",
            f"- **API 端點:** {self.config.endpoint.url}",
            f"- **模型名稱:** {self.config.endpoint.model}",
            f"- **分詞器:** {self.config.tokenizer.model_name_or_path}",
            "",
            "## 測試摘要",
            "",
        ]

        # 統計摘要
        passed_count = sum(1 for r in results if r.passed)
        total_count = len(results)
        pass_rate = (passed_count / total_count * 100) if total_count > 0 else 0

        # 整體判定
        overall_status = "✅ 通過" if passed_count == total_count else "❌ 失敗"

        md_lines.extend(
            [
                "| 項目 | 數值 |",
                "|------|------|",
                f"| **整體狀態** | {overall_status} |",
                f"| **總測試數** | {total_count} |",
                f"| **通過數** | {passed_count} |",
                f"| **失敗數** | {total_count - passed_count} |",
                f"| **通過率** | {pass_rate:.1f}% |",
                "",
                "## 詳細結果",
                "",
            ]
        )

        # 詳細結果
        for result in results:
            status_icon = "✅" if result.passed else "❌"
            status_text = "通過" if result.passed else "失敗"

            # 檢測器標題
            detector_title = self._get_detector_title(result.name)
            md_lines.append(f"### {status_icon} {detector_title}")
            md_lines.append("")
            md_lines.append(f"**狀態:** {status_text}")
            md_lines.append("")

            # 指標表格
            if result.metrics:
                md_lines.append("**指標:**")
                md_lines.append("")

                # 根據檢測器類型產生不同的表格
                if result.name == "tokenizer_fingerprint":
                    md_lines.extend(self._format_fingerprint_metrics(result))
                elif result.name == "perturbation":
                    md_lines.extend(self._format_perturbation_metrics(result))
                elif result.name == "arithmetic_json":
                    md_lines.extend(self._format_arithmetic_metrics(result))
                elif result.name == "style_bias":
                    md_lines.extend(self._format_style_metrics(result))
                else:
                    # 預設格式
                    md_lines.append("| 指標 | 數值 |")
                    md_lines.append("|------|------|")
                    for key, value in result.metrics.items():
                        md_lines.append(f"| {key} | {value} |")

                md_lines.append("")

            # 解讀說明
            interpretation = self._get_interpretation(result)
            if interpretation:
                md_lines.append("**解讀:**")
                md_lines.append("")
                md_lines.append(interpretation)
                md_lines.append("")

            # 備註
            if result.notes:
                md_lines.append(f"**備註:** {result.notes}")
                md_lines.append("")

            md_lines.append("---")
            md_lines.append("")

        md_path = output_dir / "report.md"
        md_path.write_text("\n".join(md_lines), encoding="utf-8")
        self.logger.info(f"Markdown 報告已產生: {md_path}")

        self.logger.info(f"報告已產生至目錄: {output_dir}")

    def _get_detector_title(self, name: str) -> str:
        """取得檢測器的中文標題。

        Args:
            name: 檢測器名稱

        Returns:
            中文標題
        """
        titles = {
            "tokenizer_fingerprint": "分詞器指紋檢測",
            "perturbation": "微擾穩定性檢測",
            "arithmetic_json": "算術與 JSON 結構完整性檢測",
            "style_bias": "風格偏移檢測",
        }
        return titles.get(name, name)

    def _format_fingerprint_metrics(self, result: DetectorResult) -> list[str]:
        """格式化分詞器指紋檢測的指標。"""
        lines = ["| 指標 | 數值 | 閾值 | 狀態 |", "|------|------|------|------|"]

        avg_diff = result.metrics.get("avg_token_diff_pct")
        threshold = result.metrics.get("threshold")
        samples = result.metrics.get("samples", 0)
        success_rate = result.metrics.get("success_rate", 0)

        if avg_diff is not None:
            status = "✅" if avg_diff <= threshold else "❌"
            lines.append(f"| 平均 token 偏差 | {avg_diff}% | ≤ {threshold}% | {status} |")

        max_diff = result.metrics.get("max_token_diff_pct")
        if max_diff is not None:
            lines.append(f"| 最大 token 偏差 | {max_diff}% | - | - |")

        lines.append(f"| 測試樣本數 | {samples} | - | - |")
        lines.append(f"| 成功率 | {success_rate * 100:.0f}% | - | - |")

        return lines

    def _format_perturbation_metrics(self, result: DetectorResult) -> list[str]:
        """格式化微擾穩定性檢測的指標。"""
        lines = ["| 指標 | 數值 | 閾值 | 狀態 |", "|------|------|------|------|"]

        top1_pct = result.metrics.get("top1_change_pct")
        threshold = result.metrics.get("threshold")
        pairs = result.metrics.get("pairs", 0)
        success_rate = result.metrics.get("success_rate", 0)

        if top1_pct is not None:
            status = "✅" if top1_pct <= threshold else "❌"
            lines.append(f"| Top-1 變更率 | {top1_pct}% | ≤ {threshold}% | {status} |")

        hamming = result.metrics.get("avg_hamming@10")
        if hamming is not None:
            lines.append(f"| 平均 Hamming 距離 (前10 token) | {hamming} | - | - |")

        lines.append(f"| 測試對數 | {pairs} | - | - |")
        lines.append(f"| 成功率 | {success_rate * 100:.0f}% | - | - |")

        return lines

    def _format_arithmetic_metrics(self, result: DetectorResult) -> list[str]:
        """格式化算術與 JSON 檢測的指標。"""
        lines = ["| 指標 | 數值 | 閾值 | 狀態 |", "|------|------|------|------|"]

        arith_acc = result.metrics.get("arithmetic_acc")
        threshold_arith = result.metrics.get("threshold_arithmetic")

        if arith_acc is not None:
            status = "✅" if arith_acc >= threshold_arith else "❌"
            lines.append(f"| 算術正確率 | {arith_acc} | ≥ {threshold_arith} | {status} |")

        correct = result.metrics.get("arithmetic_correct", 0)
        total = result.metrics.get("arithmetic_total", 0)
        lines.append(f"| 算術測試 (正確/總數) | {correct}/{total} | - | - |")

        json_valid = result.metrics.get("json_valid_sample")
        if json_valid is not None:
            status = "✅" if json_valid else "❌"
            lines.append(f"| JSON 合法性 | {json_valid} | True | {status} |")

        success_rate = result.metrics.get("arithmetic_success_rate", 0)
        lines.append(f"| 成功率 | {success_rate * 100:.0f}% | - | - |")

        return lines

    def _format_style_metrics(self, result: DetectorResult) -> list[str]:
        """格式化風格偏移檢測的指標。"""
        lines = ["| 指標 | 數值 | 閾值 | 狀態 |", "|------|------|------|------|"]

        prefix_rate = result.metrics.get("fixed_prefix_rate")
        threshold_prefix = result.metrics.get("threshold_prefix")

        if prefix_rate is not None:
            status = "✅" if prefix_rate <= threshold_prefix else "❌"
            lines.append(f"| 固定前綴出現率 | {prefix_rate} | ≤ {threshold_prefix} | {status} |")

        violation_rate = result.metrics.get("format_violation_rate")
        threshold_violation = result.metrics.get("threshold_violation")

        if violation_rate is not None:
            status = "✅" if violation_rate <= threshold_violation else "❌"
            lines.append(f"| 格式違規率 | {violation_rate} | ≤ {threshold_violation} | {status} |")

        success_rate = result.metrics.get("success_rate", 0)
        lines.append(f"| 成功率 | {success_rate * 100:.0f}% | - | - |")

        return lines

    def _get_interpretation(self, result: DetectorResult) -> str:
        """取得檢測結果的解讀說明。

        Args:
            result: 檢測結果

        Returns:
            解讀說明文字
        """
        if result.name == "tokenizer_fingerprint":
            avg_diff = result.metrics.get("avg_token_diff_pct")
            if avg_diff is None:
                return "無法取得 token 數量資訊，可能是 API 不支援或網路問題。"
            elif result.passed:
                return f"平均 token 數偏差為 {avg_diff}%，在可接受範圍內，表示 API 使用的分詞器與宣稱的模型家族一致。"
            else:
                return f"平均 token 數偏差為 {avg_diff}%，超過閾值，可能表示 API 使用了不同的分詞器或模型家族。"

        elif result.name == "perturbation":
            top1_pct = result.metrics.get("top1_change_pct")
            if top1_pct is None:
                return "無法完成微擾測試，可能是 API 請求失敗。"
            elif result.passed:
                return f"Top-1 token 變更率為 {top1_pct}%，在可接受範圍內，表示模型在微小輸入擾動下保持穩定，未檢測到明顯的量化影響。"
            else:
                return f"Top-1 token 變更率為 {top1_pct}%，超過閾值，可能表示模型使用了低比特量化或解碼核不穩定。"

        elif result.name == "arithmetic_json":
            arith_acc = result.metrics.get("arithmetic_acc")
            json_valid = result.metrics.get("json_valid_sample")
            if arith_acc is None:
                return "無法完成算術測試，可能是 API 請求失敗。"
            elif result.passed:
                return f"算術正確率為 {arith_acc}，JSON 輸出合法，表示模型在精確任務上表現良好，未檢測到明顯的量化影響。"
            else:
                issues = []
                threshold = result.metrics.get("threshold_arithmetic", 0.9)
                if arith_acc < threshold:
                    issues.append(f"算術正確率 ({arith_acc}) 低於閾值 ({threshold})")
                if not json_valid:
                    issues.append("JSON 輸出不合法")
                return f"檢測到問題：{', '.join(issues)}。可能表示模型使用了量化或存在強制後處理。"

        elif result.name == "style_bias":
            prefix_rate = result.metrics.get("fixed_prefix_rate")
            violation_rate = result.metrics.get("format_violation_rate")
            if prefix_rate is None:
                return "無法完成風格測試，可能是 API 請求失敗。"
            elif result.passed:
                return f"固定前綴出現率為 {prefix_rate}，格式違規率為 {violation_rate}，均在可接受範圍內，未檢測到明顯的微調影響。"
            else:
                issues = []
                threshold_prefix = result.metrics.get("threshold_prefix", 0.2)
                threshold_violation = result.metrics.get("threshold_violation", 0.1)
                if prefix_rate > threshold_prefix:
                    issues.append(f"固定前綴出現率 ({prefix_rate}) 超過閾值 ({threshold_prefix})")
                if violation_rate > threshold_violation:
                    issues.append(f"格式違規率 ({violation_rate}) 超過閾值 ({threshold_violation})")
                return f"檢測到問題：{', '.join(issues)}。可能表示模型經過微調，導致行為偏移。"

        return ""

    async def close(self) -> None:
        """關閉資源。

        關閉 API 客戶端連線。
        """
        self.logger.info("關閉 API 客戶端")
        await self.api.close()
