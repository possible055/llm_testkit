# 審計模組配置檔案說明

本文件詳細說明審計模組的 YAML 配置檔案結構與各項參數。

## 配置檔案結構

完整的配置檔案包含以下區塊：

```yaml
endpoint:           # API 端點配置
tokenizer:          # 分詞器配置
control_endpoint:   # 控制端點配置（Phase 2 功能）
decoding:           # 解碼參數
suites:             # 測試套件定義
thresholds:         # 檢測閾值
run:                # 執行配置
```

## 詳細參數說明

### endpoint（API 端點配置）

定義待測試的 API 端點資訊。

```yaml
endpoint:
  url: "https://api.example.com/v1/chat/completions"
  model: "meta-llama/Llama-3.1-8B"
  api_key: null  # null 表示從環境變數 OPENAI_API_KEY 讀取
```

**參數說明：**

- `url` (必要): API 端點 URL，必須是 OpenAI 相容的 Chat Completions API
- `model` (必要): 模型名稱，應與 API 宣稱的模型一致
- `api_key` (可選): API 金鑰
  - 設為 `null` 時從環境變數 `OPENAI_API_KEY` 讀取
  - 可直接填入金鑰字串（不建議，有安全風險）

### tokenizer（分詞器配置）

定義用於比對的本地分詞器。

```yaml
tokenizer:
  model_name_or_path: "meta-llama/Llama-3.1-8B"
```

**參數說明：**

- `model_name_or_path` (必要): 分詞器模型名稱或本地路徑
  - Hugging Face 模型 ID（如 `meta-llama/Llama-3.1-8B`）
  - 本地模型路徑（如 `/path/to/local/model`）

**注意事項：**

- 首次使用時會自動從 Hugging Face Hub 下載分詞器
- 某些模型（如 Llama）需要申請存取權限
- 支援自訂分詞器（程式碼中已啟用 `trust_remote_code=True`）

支援的模型清單請參考 [supported-models.md](supported-models.md)。

### control_endpoint（控制端點配置）

Phase 2 功能，用於對照測試。目前設為 `null`。

```yaml
control_endpoint: null
```

未來可配置為：

```yaml
control_endpoint:
  url: "https://official-api.example.com/v1/chat/completions"
  model: "meta-llama/Llama-3.1-8B"
  api_key: null
```

### decoding（解碼參數）

定義 API 請求的解碼參數。

```yaml
decoding:
  temperature: 0.0
  top_p: 1.0
  max_tokens: 128
  seed: 1234
```

**參數說明：**

- `temperature` (建議 0.0): 溫度參數
  - 設為 0.0 可確保輸出的確定性，便於檢測
  - 微擾穩定性檢測依賴此參數為 0.0
  
- `top_p` (建議 1.0): Nucleus sampling 參數
  - 設為 1.0 表示不進行 top-p 過濾
  
- `max_tokens` (建議 128): 最大生成 token 數
  - 根據檢測需求調整，128 通常足夠
  
- `seed` (可選): 隨機種子
  - 某些 API 支援種子參數以確保可重現性

### suites（測試套件定義）

定義不同的測試套件組合。

```yaml
suites:
  quick:
    - tokenizer_fingerprint
    - perturbation
    - arithmetic_json
    - style_bias
  
  minimal:
    - tokenizer_fingerprint
    - perturbation
  
  full:
    - tokenizer_fingerprint
    - perturbation
    - arithmetic_json
    - style_bias
    # Phase 2 檢測器（未來新增）
    # - zero_replay
    # - near_tie
    # - tail_vocab
    # - long_context
```

**可用檢測器：**

- `tokenizer_fingerprint`: 分詞器指紋檢測
- `perturbation`: 微擾穩定性檢測
- `arithmetic_json`: 算術與 JSON 結構完整性檢測
- `style_bias`: 風格偏移檢測

**使用方式：**

```bash
# 執行 quick 套件
llm-testkit audit --config my_audit.yaml --suite quick

# 執行 minimal 套件
llm-testkit audit --config my_audit.yaml --suite minimal
```

### thresholds（檢測閾值）

定義各檢測器的通過閾值。

```yaml
thresholds:
  # 分詞器指紋檢測
  fingerprint_avg_diff_pct: 2.0
  
  # 微擾穩定性檢測
  perturb_top1_change_pct: 20.0
  
  # 算術與 JSON 檢測
  arithmetic_acc: 0.9
  json_valid_rate: 0.9
  
  # 風格偏移檢測
  style_fixed_prefix_rate: 0.2
  style_format_violation_rate: 0.1
```

**參數說明：**

#### fingerprint_avg_diff_pct（預設 2.0）

分詞器指紋平均差異百分比閾值。

- **含義**: API 回傳的 token 數與本地分詞器計算結果的平均差異百分比
- **通過條件**: `avg_diff_pct <= fingerprint_avg_diff_pct`
- **調整建議**:
  - 標準模型: 2.0%（預設）
  - 量化模型: 3.0-5.0%（放寬）
  - 嚴格檢測: 1.0%（收緊）

#### perturb_top1_change_pct（預設 20.0）

微擾穩定性 Top-1 變化百分比閾值。

- **含義**: 在 temperature=0 下，微擾後輸出變化的比例
- **通過條件**: `top1_change_pct <= perturb_top1_change_pct`
- **調整建議**:
  - 標準模型: 20.0%（預設）
  - 量化模型: 30.0-40.0%（放寬）
  - 嚴格檢測: 10.0%（收緊）

#### arithmetic_acc（預設 0.9）

算術運算準確率閾值。

- **含義**: 2-4 位數乘法運算的正確率
- **通過條件**: `accuracy >= arithmetic_acc`
- **調整建議**:
  - 標準模型: 0.9（預設）
  - 量化模型: 0.8-0.85（放寬）
  - 嚴格檢測: 0.95（收緊）

#### json_valid_rate（預設 0.9）

JSON 結構有效率閾值。

- **含義**: 生成的 JSON 結構有效的比例
- **通過條件**: `valid_rate >= json_valid_rate`
- **調整建議**:
  - 標準模型: 0.9（預設）
  - 量化模型: 0.85（放寬）
  - 嚴格檢測: 0.95（收緊）

#### style_fixed_prefix_rate（預設 0.2）

風格固定前言比例閾值。

- **含義**: 輸出包含固定前言（如「Sure」「抱歉」）的比例
- **通過條件**: `fixed_prefix_rate <= style_fixed_prefix_rate`
- **調整建議**:
  - 標準模型: 0.2（預設）
  - 微調模型: 0.3-0.4（放寬）
  - 嚴格檢測: 0.1（收緊）

#### style_format_violation_rate（預設 0.1）

風格格式違規比例閾值。

- **含義**: 輸出違反格式要求的比例
- **通過條件**: `format_violation_rate <= style_format_violation_rate`
- **調整建議**:
  - 標準模型: 0.1（預設）
  - 微調模型: 0.15-0.2（放寬）
  - 嚴格檢測: 0.05（收緊）

### run（執行配置）

定義審計執行的運行參數。

```yaml
run:
  parallel: 1
  rate_limit_sleep: 0.2
  retries: 2
  timeout_sec: 60
```

**參數說明：**

- `parallel` (預設 1): 並行請求數
  - 設為 1 表示串行執行（推薦，避免速率限制）
  - 可增加以加速執行，但需注意 API 速率限制
  
- `rate_limit_sleep` (預設 0.2): 請求間延遲（秒）
  - 用於避免觸發 API 速率限制
  - 遇到速率限制時可增加到 0.5-1.0
  
- `retries` (預設 2): 失敗重試次數
  - 遇到暫時性錯誤（如網路問題）時的重試次數
  - 建議設為 2-5
  
- `timeout_sec` (預設 60): 請求超時時間（秒）
  - 單個 API 請求的最大等待時間
  - 對於慢速 API 可增加到 120-180

## 配置範例

### 範例 1：標準配置

適用於大多數情況的標準配置。

```yaml
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
```

### 範例 2：量化模型配置

針對量化模型放寬閾值。

```yaml
endpoint:
  url: "https://api.example.com/v1/chat/completions"
  model: "meta-llama/Llama-3.1-8B-Q4"
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
  fingerprint_avg_diff_pct: 5.0        # 放寬到 5%
  perturb_top1_change_pct: 30.0        # 放寬到 30%
  arithmetic_acc: 0.85                 # 降低到 85%
  json_valid_rate: 0.85
  style_fixed_prefix_rate: 0.3
  style_format_violation_rate: 0.15

run:
  parallel: 1
  rate_limit_sleep: 0.2
  retries: 2
  timeout_sec: 60
```

### 範例 3：慢速 API 配置

針對速率限制嚴格或回應較慢的 API。

```yaml
endpoint:
  url: "https://slow-api.example.com/v1/chat/completions"
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
  rate_limit_sleep: 1.0      # 增加請求間延遲
  retries: 5                 # 增加重試次數
  timeout_sec: 180           # 增加超時時間
```

### 範例 4：本地模型配置

使用本地下載的模型與分詞器。

```yaml
endpoint:
  url: "https://api.example.com/v1/chat/completions"
  model: "meta-llama/Llama-3.1-8B"
  api_key: null

tokenizer:
  model_name_or_path: "/path/to/local/models/llama31"

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
```

## 相關文件

- [審計模組使用指南](audit-guide.md)
- [支援的模型清單](supported-models.md)
- [環境變數說明](environment-variables.md)
- [疑難排解](troubleshooting.md)
