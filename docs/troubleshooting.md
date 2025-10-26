# 疑難排解

本文件提供審計模組常見問題的解決方案。

## 分詞器相關問題

### Q: 分詞器下載失敗怎麼辦？

**問題描述：**

執行審計時出現分詞器下載錯誤，例如：

```
OSError: Can't load tokenizer for 'meta-llama/Llama-3.1-8B'
```

**可能原因與解決方案：**

#### 1. 網路問題

**症狀：** 下載超時或連線失敗

**解決方案：**

使用 Hugging Face 鏡像站：

```bash
# 設定環境變數
export HF_ENDPOINT="https://hf-mirror.com"

# 然後執行審計
llm-testkit audit --config my_audit.yaml
```

或使用代理：

```bash
# HTTP 代理
export HTTP_PROXY="http://proxy.example.com:8080"
export HTTPS_PROXY="http://proxy.example.com:8080"

# SOCKS 代理
export ALL_PROXY="socks5://proxy.example.com:1080"
```

#### 2. 權限問題

**症狀：** 出現 401 或 403 錯誤

**解決方案：**

某些模型（如 Llama）需要申請存取權限：

1. 前往 Hugging Face 申請存取權限
   - Llama: https://huggingface.co/meta-llama
   - Gemma: https://huggingface.co/google/gemma-7b

2. 使用 `huggingface-cli login` 登入：

```bash
# 安裝 CLI
pip install huggingface_hub

# 登入
huggingface-cli login

# 輸入你的 Access Token
# Token 可在 https://huggingface.co/settings/tokens 取得
```

#### 3. 離線環境

**症狀：** 無網路連線

**解決方案：**

預先下載模型到本地：

```bash
# 在有網路的環境下載
huggingface-cli download meta-llama/Llama-3.1-8B --local-dir ./models/llama31

# 將模型目錄複製到離線環境

# 在配置中使用本地路徑
# tokenizer:
#   model_name_or_path: "./models/llama31"
```

或使用 Python 下載：

```bash
python -c "from transformers import AutoTokenizer; AutoTokenizer.from_pretrained('meta-llama/Llama-3.1-8B')"
```

### Q: 自訂分詞器載入失敗

**問題描述：**

載入某些模型（如 GLM）時出現錯誤：

```
ValueError: Tokenizer class ... cannot be loaded without trust_remote_code=True
```

**解決方案：**

審計模組已在程式碼中預設啟用 `trust_remote_code=True`，若仍遇到此問題：

1. 確認使用的是最新版本的審計模組
2. 手動測試分詞器載入：

```python
from transformers import AutoTokenizer

tokenizer = AutoTokenizer.from_pretrained(
    "THUDM/glm-4-9b",
    trust_remote_code=True
)
```

3. 若手動測試成功但審計失敗，請回報問題

## API 相關問題

### Q: API 不回傳 usage 資訊怎麼辦？

**問題描述：**

分詞器指紋檢測失敗，報告中顯示「API 未回傳 usage 資訊」。

**原因：**

某些 OpenAI 相容 API 不回傳 `usage.prompt_tokens` 欄位。

**影響：**

- 分詞器指紋檢測會標記為失敗
- 其他檢測器不受影響，仍會正常執行

**解決方案：**

1. **聯繫 API 服務商**：要求支援 `usage` 欄位
2. **使用其他檢測器**：其他三個檢測器不依賴 `usage` 資訊
3. **等待 Phase 2**：未來版本可能提供替代方案

### Q: 如何處理速率限制？

**問題描述：**

執行審計時頻繁遇到 429 錯誤（速率限制）。

**解決方案：**

調整配置檔中的 `run` 區塊：

```yaml
run:
  parallel: 1              # 確保串行執行
  rate_limit_sleep: 1.0    # 增加請求間延遲（秒）
  retries: 5               # 增加重試次數
  timeout_sec: 120         # 增加超時時間
```

**建議值：**

- 嚴格速率限制：`rate_limit_sleep: 2.0`
- 中等速率限制：`rate_limit_sleep: 1.0`
- 寬鬆速率限制：`rate_limit_sleep: 0.2`（預設）

### Q: API 請求超時

**問題描述：**

執行審計時出現超時錯誤。

**解決方案：**

增加超時時間：

```yaml
run:
  timeout_sec: 180  # 增加到 180 秒
```

若問題持續，檢查：

1. API 服務是否正常運作
2. 網路連線是否穩定
3. API 回應速度是否過慢

### Q: API 回傳錯誤格式

**問題描述：**

API 回傳的格式與 OpenAI 不相容。

**解決方案：**

1. 確認 API 端點是否為 OpenAI 相容 API
2. 檢查 API 文件，確認支援 Chat Completions API
3. 測試 API 端點：

```bash
curl -X POST "https://api.example.com/v1/chat/completions" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "meta-llama/Llama-3.1-8B",
    "messages": [{"role": "user", "content": "Hello"}],
    "temperature": 0.0
  }'
```

## 檢測結果相關問題

### Q: 如何調整檢測靈敏度？

**問題描述：**

檢測器過於嚴格或寬鬆，需要調整閾值。

**解決方案：**

透過修改配置檔中的 `thresholds` 區塊：

```yaml
thresholds:
  # 提高閾值 = 降低靈敏度（更寬鬆）
  fingerprint_avg_diff_pct: 5.0      # 預設 2.0
  perturb_top1_change_pct: 30.0      # 預設 20.0
  
  # 降低閾值 = 提高靈敏度（更嚴格）
  arithmetic_acc: 0.95               # 預設 0.9
  json_valid_rate: 0.95              # 預設 0.9
```

**針對不同場景的建議：**

#### 標準模型（預設值）

```yaml
thresholds:
  fingerprint_avg_diff_pct: 2.0
  perturb_top1_change_pct: 20.0
  arithmetic_acc: 0.9
  json_valid_rate: 0.9
  style_fixed_prefix_rate: 0.2
  style_format_violation_rate: 0.1
```

#### 量化模型（放寬閾值）

```yaml
thresholds:
  fingerprint_avg_diff_pct: 5.0
  perturb_top1_change_pct: 30.0
  arithmetic_acc: 0.85
  json_valid_rate: 0.85
  style_fixed_prefix_rate: 0.3
  style_format_violation_rate: 0.15
```

#### 嚴格檢測（收緊閾值）

```yaml
thresholds:
  fingerprint_avg_diff_pct: 1.0
  perturb_top1_change_pct: 10.0
  arithmetic_acc: 0.95
  json_valid_rate: 0.95
  style_fixed_prefix_rate: 0.1
  style_format_violation_rate: 0.05
```

### Q: 檢測器全部失敗

**問題描述：**

所有檢測器都標記為失敗。

**可能原因與解決方案：**

#### 1. API 端點錯誤

檢查配置檔中的 `endpoint.url` 是否正確。

#### 2. API 金鑰無效

確認環境變數 `OPENAI_API_KEY` 已正確設定：

```bash
echo $OPENAI_API_KEY
```

#### 3. 模型名稱不匹配

確認 `endpoint.model` 與 `tokenizer.model_name_or_path` 是否對應同一模型家族。

#### 4. API 不相容

確認 API 是否為 OpenAI 相容 API，支援 Chat Completions 格式。

### Q: 分詞器指紋檢測失敗，但其他檢測通過

**問題描述：**

只有分詞器指紋檢測失敗，其他檢測器通過。

**可能原因：**

1. **API 使用不同的分詞器**：服務商可能使用了不同版本或修改過的分詞器
2. **API 不回傳 usage 資訊**：某些 API 不提供 token 計數
3. **分詞器版本差異**：本地分詞器版本與 API 使用的版本不同

**解決方案：**

1. 確認 API 宣稱的模型與配置中的分詞器是否一致
2. 檢查報告中的詳細指標，查看差異百分比
3. 若差異在可接受範圍內（如 3-5%），可考慮放寬閾值
4. 聯繫 API 服務商確認分詞器版本

## 環境相關問題

### Q: 依賴安裝失敗

**問題描述：**

執行 `pip install -e .` 時出現錯誤。

**解決方案：**

#### 1. 升級 pip

```bash
pip install --upgrade pip
```

#### 2. 使用虛擬環境

```bash
# 建立虛擬環境
python -m venv venv

# 啟動虛擬環境
# Linux/macOS
source venv/bin/activate
# Windows
venv\Scripts\activate

# 安裝依賴
pip install -e .
```

#### 3. 手動安裝依賴

```bash
pip install transformers>=4.40.0
pip install openai>=2.6.0
pip install tenacity>=9.1.2
pip install pyyaml>=6.0
pip install python-dotenv>=1.1.1
```

### Q: Python 版本不相容

**問題描述：**

出現 Python 版本相關錯誤。

**解決方案：**

確認 Python 版本為 3.12 或更高：

```bash
python --version
```

若版本過低，請升級 Python：

- Linux: 使用套件管理器（如 `apt`、`yum`）
- macOS: 使用 Homebrew（`brew install python@3.12`）
- Windows: 從 [python.org](https://www.python.org/) 下載安裝

### Q: 記憶體不足

**問題描述：**

載入大型分詞器時記憶體不足。

**解決方案：**

1. **使用較小的模型**：選擇參數量較小的模型（如 7B 而非 70B）
2. **增加系統記憶體**：確保系統有足夠的可用記憶體
3. **使用本地分詞器**：預先下載分詞器，避免重複載入

## 報告相關問題

### Q: 報告未產生

**問題描述：**

執行完成但未產生報告檔案。

**解決方案：**

1. 檢查輸出目錄是否存在寫入權限
2. 檢查執行日誌是否有錯誤訊息
3. 手動指定輸出目錄：

```bash
llm-testkit audit --config my_audit.yaml --output output/my_results
```

### Q: 報告格式錯誤

**問題描述：**

報告檔案無法正常開啟或格式異常。

**解決方案：**

1. 確認使用的是最新版本的審計模組
2. 檢查報告檔案是否完整（未被截斷）
3. 嘗試重新執行審計

## 效能相關問題

### Q: 執行速度過慢

**問題描述：**

審計執行時間過長。

**解決方案：**

1. **減少測試項目**：使用 `minimal` 套件而非 `quick`
2. **調整並行度**：若 API 支援，可增加 `parallel` 值（需注意速率限制）
3. **減少重試次數**：降低 `retries` 值
4. **使用本地分詞器**：預先下載分詞器，避免首次下載延遲

### Q: 記憶體使用過高

**問題描述：**

執行審計時記憶體使用量過高。

**解決方案：**

1. 使用較小的模型分詞器
2. 減少並行請求數（`parallel: 1`）
3. 關閉其他佔用記憶體的程式

## 其他問題

### Q: 如何新增自訂檢測器？

請參考 [audit-guide.md](audit-guide.md) 中的「自訂檢測器」章節。

### Q: 如何貢獻新的檢測器？

歡迎貢獻！請：

1. Fork 專案
2. 建立新的檢測器類別（繼承 `BaseDetector`）
3. 新增測試
4. 提交 Pull Request

### Q: 在哪裡回報問題？

若遇到未列出的問題，請：

1. 檢查是否為已知問題
2. 收集錯誤訊息與執行日誌
3. 在專案 Issue 追蹤器中回報

## 相關文件

- [審計模組使用指南](audit-guide.md)
- [配置檔案說明](configuration.md)
- [支援的模型清單](supported-models.md)
- [環境變數說明](environment-variables.md)
