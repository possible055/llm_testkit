# LLM API 黑盒審計模組使用指南

本文件提供 LLM API 黑盒審計模組的完整使用指南，包含安裝、配置、執行與報告解讀。

## 概述

審計模組透過「分詞器指紋 + 壓力測試 + 分佈檢查」三層交叉驗證，檢測第三方 API 服務商提供的模型是否與其宣稱的模型一致，識別模型是否被微調、量化或替換。

## 核心檢測器

### Phase 1（已實作）

1. **分詞器指紋檢測** (`tokenizer_fingerprint`)
   - 使用特製字串測試集（空白、Unicode、Emoji、URL、CJK 混排）
   - 比對 API 回傳的 token 數與本地分詞器計算結果
   - 檢測模型家族是否正確

2. **微擾穩定性檢測** (`perturbation`)
   - 對提示進行微小擾動（末尾空白、換行、同義替換）
   - 在 temperature=0 下比較輸出差異
   - 檢測低比特量化或粗糙解碼核跡象

3. **算術與 JSON 結構完整性檢測** (`arithmetic_json`)
   - 測試 2-4 位數乘法運算能力
   - 驗證 JSON 結構化輸出能力
   - 檢測量化對精確任務的影響

4. **風格偏移檢測** (`style_bias`)
   - 使用強格式要求的提示
   - 檢測固定前言（如「Sure」「抱歉」）與格式違規
   - 識別微調導致的行為變化

### Phase 2（規劃中）

- 零溫度重播檢測 (`zero_replay`)
- Near-tie 探針檢測 (`near_tie`)
- 尾部詞彙檢測 (`tail_vocab`)
- 長上下文記憶檢測 (`long_context`)

## 快速開始

### 1. 安裝

```bash
# 從專案根目錄安裝
pip install -e .
```

核心依賴會自動安裝：
- `transformers>=4.40.0` - Hugging Face 分詞器（必要）
- `openai>=2.6.0` - OpenAI API 客戶端
- `tenacity>=9.1.2` - 重試邏輯
- `pyyaml>=6.0` - YAML 配置解析

### 2. 設定環境變數

```bash
# 設定 API 金鑰（必要）
export OPENAI_API_KEY="your-api-key-here"

# 可選：設定自訂 API 端點
export OPENAI_BASE_URL="https://api.example.com/v1"

# 可選：設定 Hugging Face 鏡像站（加速分詞器下載）
export HF_ENDPOINT="https://hf-mirror.com"
```

詳細環境變數說明請參考 [environment-variables.md](environment-variables.md)。

### 3. 建立配置檔

建立 YAML 配置檔（例如 `my_audit.yaml`）：

```yaml
# API 端點配置
endpoint:
  url: "https://api.example.com/v1/chat/completions"
  model: "meta-llama/Llama-3.1-8B"
  api_key: null  # 從環境變數 OPENAI_API_KEY 讀取

# 分詞器配置
tokenizer:
  model_name_or_path: "meta-llama/Llama-3.1-8B"

# 解碼參數
decoding:
  temperature: 0.0
  top_p: 1.0
  max_tokens: 128
  seed: 1234

# 測試套件
suites:
  quick:
    - tokenizer_fingerprint
    - perturbation
    - arithmetic_json
    - style_bias

# 檢測閾值
thresholds:
  fingerprint_avg_diff_pct: 2.0
  perturb_top1_change_pct: 20.0
  arithmetic_acc: 0.9
  json_valid_rate: 0.9
  style_fixed_prefix_rate: 0.2
  style_format_violation_rate: 0.1

# 執行配置
run:
  parallel: 1
  rate_limit_sleep: 0.2
  retries: 2
  timeout_sec: 60
```

完整配置說明請參考 [configuration.md](configuration.md)。

### 4. 執行審計

```bash
# 使用統一 CLI 入口
llm-testkit audit --config my_audit.yaml

# 或使用模組方式
python -m llm_testkit.audit.cli --config my_audit.yaml

# 指定測試套件
llm-testkit audit --config my_audit.yaml --suite quick

# 指定輸出目錄
llm-testkit audit --config my_audit.yaml --output output/my_results
```

### 5. 檢視報告

執行完成後，會在輸出目錄產生兩種格式的報告：

- `report.json` - 機器可讀格式，便於後續分析
- `report.md` - 人類可讀格式，便於快速檢視

```bash
# 檢視 Markdown 報告
cat output/audit/report.md
```

報告內容包含：
- 時間戳記
- 測試端點資訊
- 各檢測器的通過/失敗狀態
- 詳細指標數據
- 錯誤訊息（如有）

## 使用範例

### 範例 1：測試 Llama 3.1 API

```bash
# 1. 建立配置檔
cat > llama31_audit.yaml << EOF
endpoint:
  url: "https://api.example.com/v1/chat/completions"
  model: "meta-llama/Llama-3.1-8B"
  api_key: null

tokenizer:
  model_name_or_path: "meta-llama/Llama-3.1-8B"

control_endpoint: null

decoding:
  temperature: 0.0
  top_p: 1.0
  max_tokens: 128
  seed: 1234

suites:
  quick:
    - tokenizer_fingerprint
    - perturbation
    - arithmetic_json
    - style_bias

thresholds:
  fingerprint_avg_diff_pct: 2.0
  perturb_top1_change_pct: 20.0
  arithmetic_acc: 0.9
  json_valid_rate: 0.9
  style_fixed_prefix_rate: 0.2
  style_format_violation_rate: 0.1

run:
  parallel: 1
  rate_limit_sleep: 0.2
  retries: 2
  timeout_sec: 60
EOF

# 2. 設定 API 金鑰
export OPENAI_API_KEY="your-api-key"

# 3. 執行審計
llm-testkit audit \
  --config llama31_audit.yaml \
  --suite quick \
  --output output/llama31_audit

# 4. 檢視報告
cat output/llama31_audit/report.md
```

### 範例 2：測試 Qwen 2.5 API

```bash
# 修改配置檔中的模型名稱
sed -i 's/Llama-3.1-8B/Qwen2.5-7B/g' llama31_audit.yaml

# 執行審計
llm-testkit audit \
  --config llama31_audit.yaml \
  --output output/qwen25_audit
```

### 範例 3：針對量化模型放寬閾值

```yaml
# 在配置檔中調整閾值
thresholds:
  fingerprint_avg_diff_pct: 5.0        # 放寬到 5%
  perturb_top1_change_pct: 30.0        # 放寬到 30%
  arithmetic_acc: 0.85                 # 降低到 85%
  json_valid_rate: 0.85
  style_fixed_prefix_rate: 0.3
  style_format_violation_rate: 0.15
```

## 程式化使用

除了 CLI，也可以在 Python 程式碼中直接使用審計模組：

```python
import asyncio
from llm_testkit.audit.config import AuditConfig
from llm_testkit.audit.runner import AuditRunner

async def run_audit():
    # 載入配置
    config = AuditConfig.from_yaml("my_audit.yaml")
    
    # 建立執行器
    runner = AuditRunner(config)
    
    try:
        # 執行測試套件
        results = await runner.run_suite("quick")
        
        # 產生報告
        runner.generate_report(results, "output/my_audit")
        
        # 檢查結果
        for result in results:
            print(f"{result.name}: {'通過' if result.passed else '失敗'}")
            print(f"  指標: {result.metrics}")
            if result.notes:
                print(f"  備註: {result.notes}")
    
    finally:
        # 關閉資源
        await runner.close()

# 執行
asyncio.run(run_audit())
```

## 自訂檢測器

若需要新增自訂檢測器，可繼承 `BaseDetector` 並實作 `name` 和 `run` 方法：

```python
from llm_testkit.audit.detectors.base import BaseDetector, DetectorResult

class MyCustomDetector(BaseDetector):
    @property
    def name(self) -> str:
        return "my_custom"
    
    async def run(self, api, tokenizer, decoding, thresholds) -> DetectorResult:
        # 實作檢測邏輯
        # ...
        
        return DetectorResult(
            name=self.name,
            passed=True,
            metrics={"my_metric": 0.95},
            notes="檢測通過"
        )
```

然後在 `AuditRunner` 中註冊：

```python
runner = AuditRunner(config)
runner.detectors["my_custom"] = MyCustomDetector()
```

## 技術架構

### 模組結構

```
src/llm_testkit/audit/
├── __init__.py              # 匯出主要類別
├── cli.py                   # CLI 入口
├── runner.py                # 審計執行器
├── config.py                # 配置模型
├── tokenizer.py             # 分詞器抽象
├── metrics.py               # 指標計算工具
└── detectors/               # 檢測器模組
    ├── __init__.py
    ├── base.py              # 檢測器基類
    ├── tokenizer_fingerprint.py
    ├── perturbation.py
    ├── arithmetic_json.py
    └── style_bias.py
```

### 設計原則

1. **最小侵入性**: 作為獨立模組，不修改現有程式碼
2. **架構重用**: 重用 `OpenAICompatibleAPI`、`utils.io`、`utils.logging`
3. **可擴展性**: 檢測器採用插件式設計，易於新增
4. **分階段實作**: Phase 1 實作核心功能，Phase 2 擴展進階功能

## 相關文件

- [配置檔案說明](configuration.md)
- [支援的模型清單](supported-models.md)
- [環境變數說明](environment-variables.md)
- [疑難排解](troubleshooting.md)
