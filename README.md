# LLM TestKit

LLM TestKit 是一個 Python 工具包，專為測試與評估 LLM（大型語言模型）應用而設計。目前提供 LLM API 黑盒審計功能，用於驗證第三方 API 服務商提供的模型是否與其宣稱的模型一致。

## 功能特性

### LLM API 黑盒審計 (`audit`)

透過「分詞器指紋 + 壓力測試 + 分佈檢查」三層交叉驗證，檢測模型是否被微調、量化或替換。

**核心檢測器：**

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

## 系統需求

- Python 3.12+
- pip（Python 套件管理器）

## 安裝

### 基本安裝

```bash
# 從專案根目錄安裝
pip install -e .
```

### 依賴說明

核心依賴會自動安裝：

- `openai>=2.6.0` - OpenAI API 客戶端（支援相容 API）
- `anthropic>=0.40.0` - Anthropic API 客戶端（支援 Claude 模型）
- `tenacity>=9.1.2` - 重試邏輯與指數回退
- `pyyaml>=6.0` - YAML 配置解析
- `python-dotenv>=1.1.1` - 環境變數管理
- `transformers>=4.40.0` - Hugging Face 分詞器（審計功能必要）

### 開發依賴（可選）

```bash
# 安裝測試依賴
pip install -e ".[test]"
```

## 快速開始

### 1. 設定環境變數

**方法一：使用 .env 檔案（推薦）**

```bash
# 複製範例檔案
cp .env.example .env

# 編輯 .env 檔案，填入你的 API 金鑰
nano .env  # 或使用其他編輯器
```

`.env` 檔案內容範例：
```env
OPENAI_API_KEY=sk-your-actual-api-key-here
# OPENAI_BASE_URL=https://api.example.com/v1  # 可選
# LOG_LEVEL=INFO  # 可選
```

**方法二：直接設定環境變數**

```bash
# Linux/macOS
export OPENAI_API_KEY="your-api-key-here"
export OPENAI_BASE_URL="https://api.example.com/v1"  # 可選
export LOG_LEVEL=INFO  # 可選

# Windows (PowerShell)
$env:OPENAI_API_KEY="your-api-key-here"
$env:OPENAI_BASE_URL="https://api.example.com/v1"  # 可選
$env:LOG_LEVEL="INFO"  # 可選
```

**環境變數說明：**

| 變數 | 必要性 | 說明 |
|------|--------|------|
| `OPENAI_API_KEY` | 必要 | OpenAI API 金鑰，當配置檔中 `api_key: null` 時使用 |
| `OPENAI_BASE_URL` | 可選 | 自訂 API 端點，用於第三方相容 API |
| `ANTHROPIC_API_KEY` | 可選 | Anthropic API 金鑰，用於 Claude 模型 |
| `ANTHROPIC_BASE_URL` | 可選 | 自訂 Anthropic API 端點 |
| `LOG_LEVEL` | 可選 | 日誌等級 (DEBUG/INFO/WARNING/ERROR/CRITICAL) |
| `HF_ENDPOINT` | 可選 | Hugging Face 鏡像站，用於加速分詞器下載 |

> 💡 **提示**: 更多環境變數說明請參考 [環境變數文件](docs/environment-variables.md)

### 2. 建立審計配置檔

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

完整配置範例請參考 `configs/audit_example.yaml`。

### 3. 執行審計

```bash
# 使用配置檔執行審計
llm-testkit audit --config my_audit.yaml

# 指定測試套件
llm-testkit audit --config my_audit.yaml --suite quick

# 指定輸出目錄
llm-testkit audit --config my_audit.yaml --output output/my_results
```

### 4. 檢視報告

執行完成後，會在輸出目錄產生兩種格式的報告：

- `report.json` - 機器可讀格式，便於後續分析
- `report.md` - 人類可讀格式，便於快速檢視

```bash
# 檢視 Markdown 報告
cat output/audit/report.md
```

## CLI 使用方式

### 主命令

```bash
llm-testkit --help
```

### Audit 子命令

```bash
llm-testkit audit --help
```

**參數說明：**

- `--config` (必要): 審計配置檔路徑（YAML 格式）
- `--suite` (可選): 測試套件名稱，預設為 `quick`
- `--output` (可選): 報告輸出目錄，預設為 `output/audit`

## 支援的模型與分詞器

審計模組使用 Hugging Face `transformers` 庫，支援所有主流開源模型：

### Meta Llama 系列
- `meta-llama/Llama-3.1-8B`
- `meta-llama/Llama-3.1-70B`
- `meta-llama/Llama-2-7b-hf`
- `meta-llama/Llama-2-13b-hf`

### Qwen 系列
- `Qwen/Qwen2.5-7B`
- `Qwen/Qwen2.5-14B`
- `Qwen/Qwen2.5-72B`
- `Qwen/Qwen1.5-7B`

### GLM 系列
- `THUDM/glm-4-9b`
- `THUDM/chatglm3-6b`

### Mistral 系列
- `mistralai/Mistral-7B-v0.1`
- `mistralai/Mixtral-8x7B-v0.1`

### 其他開源模型
- `google/gemma-7b`
- `microsoft/phi-2`
- `tiiuae/falcon-7b`
- `gpt2`（公開可用，適合測試）

### 使用本地模型

若模型已下載到本地，可直接指定路徑：

```yaml
tokenizer:
  model_name_or_path: "/path/to/local/model"
```

### 預先下載分詞器

首次使用時，分詞器會自動從 Hugging Face Hub 下載。若需離線使用，可預先下載：

```bash
# 使用 Python 預先下載
python -c "from transformers import AutoTokenizer; AutoTokenizer.from_pretrained('meta-llama/Llama-3.1-8B')"

# 或使用 Hugging Face CLI
pip install huggingface_hub
huggingface-cli download meta-llama/Llama-3.1-8B
```

## API 客戶端支援

LLM TestKit 提供兩種 API 客戶端實作，可用於與不同的 LLM 服務互動：

### OpenAI 相容 API

支援 OpenAI 官方 API 及所有相容的第三方服務（如 Azure OpenAI、本地部署等）。

```python
from llm_testkit.backend import OpenAICompatibleAPI

async with OpenAICompatibleAPI(
    model_name="gpt-4",
    api_key="your-api-key",
    base_url="https://api.openai.com/v1"  # 可選
) as client:
    response = await client.generate(
        messages=[{"role": "user", "content": "Hello!"}],
        max_tokens=100,
        temperature=0.7
    )
    print(response.choices[0].message.content)
```

### Anthropic API

支援 Anthropic Claude 模型系列，包含針對長時間推理請求的最佳化。

```python
from llm_testkit.backend import AnthropicAPI

async with AnthropicAPI(
    model_name="claude-sonnet-4-20250514",
    api_key="your-anthropic-api-key",
    base_url="https://api.anthropic.com"  # 可選
) as client:
    response = await client.generate(
        messages=[{"role": "user", "content": "Hello!"}],
        system="You are a helpful assistant.",  # 可選
        max_tokens=2048,
        temperature=0.5
    )
    print(response.content[0].text)
```

**特性：**
- 自動重試機制（速率限制、連線錯誤、超時）
- 指數退避策略（最多 3 次重試）
- Socket keepalive 支援長時間推理請求
- 完整的錯誤處理與類型提示
- Async context manager 自動資源管理

## 程式化使用

除了 CLI，也可以在 Python 程式碼中直接使用審計模組：

```python
import asyncio
from pathlib import Path
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

## 專案結構

```
llm_testkit/
├── src/llm_testkit/          # 主要原始碼
│   ├── audit/                # 審計模組
│   │   ├── detectors/        # 檢測器實作
│   │   ├── cli.py            # CLI 入口
│   │   ├── runner.py         # 審計執行器
│   │   └── config.py         # 配置模型
│   ├── backend/              # API 客戶端實作
│   │   ├── openai_api.py     # OpenAI 相容 API 包裝器
│   │   └── anthropic_api.py  # Anthropic API 包裝器
│   ├── core/                 # 核心工具
│   │   ├── tokenizer.py      # 分詞器抽象
│   │   └── metrics.py        # 指標計算工具
│   ├── utils/                # 工具模組
│   │   ├── config.py         # YAML 配置載入器
│   │   ├── io.py             # JSON/JSONL 檔案操作
│   │   └── logging.py        # 日誌工具
│   └── main.py               # 統一 CLI 入口點
├── configs/                  # 配置檔案
│   ├── default.yaml          # 預設配置
│   └── audit_example.yaml    # 審計配置範例
├── tests/                    # 測試檔案
├── output/                   # 產生的輸出（gitignored）
├── pyproject.toml            # 專案配置
└── README.md                 # 本檔案
```

## 開發指南

### 程式碼品質工具

專案使用以下工具維護程式碼品質：

- **Ruff**: Linter 與 Formatter（取代 flake8、black、isort）
- **Pyright**: 型別檢查器
- **Pre-commit**: Git hooks 自動化

### 常用命令

```bash
# 格式化程式碼
ruff format .

# Lint 與自動修正
ruff check --fix .

# 型別檢查
pyright src

# 執行 pre-commit hooks
pre-commit run --all-files

# 建置套件
python -m build
```

### 配置檔案

- **Ruff**: `ruff.toml`
  - 行長度: 100 字元
  - 目標: Python 3.12
  - 引號風格: 雙引號
  - Docstring 慣例: Google style

- **Pyright**: `pyrightconfig.json`
  - 模式: standard
  - Python 版本: 3.12

- **Pre-commit**: `.pre-commit-config.yaml`
  - Ruff 自動修正與格式化

## 常見問題

### Q: 分詞器下載失敗怎麼辦？

**A:** 可能原因與解決方案：

1. **網路問題**: 使用代理或鏡像站
   ```bash
   export HF_ENDPOINT=https://hf-mirror.com
   ```

2. **權限問題**: 某些模型需要授權（如 Llama）
   - 前往 Hugging Face 申請存取權限
   - 使用 `huggingface-cli login` 登入

3. **離線環境**: 預先下載模型到本地
   ```bash
   huggingface-cli download meta-llama/Llama-3.1-8B --local-dir ./models/llama31
   ```
   然後在配置中使用本地路徑：
   ```yaml
   tokenizer:
     model_name_or_path: "./models/llama31"
   ```

### Q: API 不回傳 usage 資訊怎麼辦？

**A:** 分詞器指紋檢測會自動處理此情況：
- 若 API 不回傳 `usage.prompt_tokens`，檢測器會標記為失敗
- 報告中會註明「API 未回傳 usage 資訊」
- 其他檢測器不受影響，仍會正常執行

### Q: 如何調整檢測靈敏度？

**A:** 透過修改配置檔中的 `thresholds` 區塊：

```yaml
thresholds:
  # 提高閾值 = 降低靈敏度（更寬鬆）
  fingerprint_avg_diff_pct: 5.0      # 預設 2.0
  perturb_top1_change_pct: 30.0      # 預設 20.0
  
  # 降低閾值 = 提高靈敏度（更嚴格）
  arithmetic_acc: 0.95               # 預設 0.9
```

### Q: 如何處理速率限制？

**A:** 調整配置檔中的 `run` 區塊：

```yaml
run:
  rate_limit_sleep: 1.0    # 增加請求間延遲（秒）
  retries: 5               # 增加重試次數
  timeout_sec: 120         # 增加超時時間
```

## 授權

本專案遵循專案授權條款。

## 貢獻

歡迎貢獻新的檢測器或改進現有功能！

---

更多詳細資訊請參考 `src/llm_testkit/audit/README.md`。
