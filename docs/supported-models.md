# 支援的模型與分詞器

本文件列出審計模組支援的模型家族與分詞器，以及相關的使用說明。

## 概述

審計模組使用 Hugging Face `transformers` 庫載入分詞器，理論上支援所有在 Hugging Face Hub 上可用的開源模型。以下列出經過測試或常用的模型家族。

## 支援的模型家族

### Meta Llama 系列

Meta 開發的開源大型語言模型系列。

**模型清單：**

- `meta-llama/Llama-3.1-8B`
- `meta-llama/Llama-3.1-70B`
- `meta-llama/Llama-3.1-405B`
- `meta-llama/Llama-2-7b-hf`
- `meta-llama/Llama-2-13b-hf`
- `meta-llama/Llama-2-70b-hf`

**注意事項：**

- Llama 模型需要在 Hugging Face 申請存取權限
- 申請網址：https://huggingface.co/meta-llama
- 申請後使用 `huggingface-cli login` 登入

**配置範例：**

```yaml
tokenizer:
  model_name_or_path: "meta-llama/Llama-3.1-8B"
```

### Qwen 系列

阿里巴巴開發的通義千問系列模型。

**模型清單：**

- `Qwen/Qwen2.5-7B`
- `Qwen/Qwen2.5-14B`
- `Qwen/Qwen2.5-32B`
- `Qwen/Qwen2.5-72B`
- `Qwen/Qwen1.5-7B`
- `Qwen/Qwen1.5-14B`
- `Qwen/Qwen1.5-72B`

**注意事項：**

- Qwen 模型公開可用，無需申請權限
- 支援中文與多語言

**配置範例：**

```yaml
tokenizer:
  model_name_or_path: "Qwen/Qwen2.5-7B"
```

### GLM 系列

清華大學開發的 ChatGLM 系列模型。

**模型清單：**

- `THUDM/glm-4-9b`
- `THUDM/chatglm3-6b`
- `THUDM/chatglm2-6b`

**注意事項：**

- GLM 模型使用自訂分詞器
- 程式碼中已啟用 `trust_remote_code=True` 以支援自訂分詞器

**配置範例：**

```yaml
tokenizer:
  model_name_or_path: "THUDM/glm-4-9b"
```

### Mistral 系列

Mistral AI 開發的開源模型系列。

**模型清單：**

- `mistralai/Mistral-7B-v0.1`
- `mistralai/Mistral-7B-v0.3`
- `mistralai/Mixtral-8x7B-v0.1`
- `mistralai/Mixtral-8x22B-v0.1`

**注意事項：**

- Mistral 模型公開可用
- Mixtral 為 MoE（Mixture of Experts）架構

**配置範例：**

```yaml
tokenizer:
  model_name_or_path: "mistralai/Mistral-7B-v0.1"
```

### Google Gemma 系列

Google 開發的開源模型系列。

**模型清單：**

- `google/gemma-7b`
- `google/gemma-2b`
- `google/gemma-2-9b`
- `google/gemma-2-27b`

**注意事項：**

- Gemma 模型需要同意授權條款
- 首次使用時會提示同意條款

**配置範例：**

```yaml
tokenizer:
  model_name_or_path: "google/gemma-7b"
```

### Microsoft Phi 系列

Microsoft 開發的小型高效模型系列。

**模型清單：**

- `microsoft/phi-2`
- `microsoft/phi-3-mini-4k-instruct`
- `microsoft/phi-3-small-8k-instruct`

**注意事項：**

- Phi 模型公開可用
- 適合資源受限環境

**配置範例：**

```yaml
tokenizer:
  model_name_or_path: "microsoft/phi-2"
```

### Falcon 系列

Technology Innovation Institute 開發的開源模型系列。

**模型清單：**

- `tiiuae/falcon-7b`
- `tiiuae/falcon-40b`
- `tiiuae/falcon-180B`

**注意事項：**

- Falcon 模型公開可用

**配置範例：**

```yaml
tokenizer:
  model_name_or_path: "tiiuae/falcon-7b"
```

### GPT-2（測試用）

OpenAI 的 GPT-2 模型，適合測試與開發。

**模型清單：**

- `gpt2`
- `gpt2-medium`
- `gpt2-large`
- `gpt2-xl`

**注意事項：**

- GPT-2 公開可用，無需申請權限
- 模型較小，適合快速測試
- 不建議用於生產環境審計

**配置範例：**

```yaml
tokenizer:
  model_name_or_path: "gpt2"
```

## 使用本地模型

若模型已下載到本地，可直接指定路徑：

```yaml
tokenizer:
  model_name_or_path: "/path/to/local/model"
```

### 預先下載模型

**方法 1：使用 Python**

```bash
python -c "from transformers import AutoTokenizer; AutoTokenizer.from_pretrained('meta-llama/Llama-3.1-8B')"
```

**方法 2：使用 Hugging Face CLI**

```bash
# 安裝 CLI
pip install huggingface_hub

# 下載模型
huggingface-cli download meta-llama/Llama-3.1-8B --local-dir ./models/llama31

# 在配置中使用本地路徑
# tokenizer:
#   model_name_or_path: "./models/llama31"
```

## 自訂分詞器支援

對於使用自訂分詞器的模型（如 GLM、某些微調模型），審計模組已在程式碼中啟用 `trust_remote_code=True`：

```python
# 程式碼中已自動處理
AutoTokenizer.from_pretrained(
    model_name_or_path,
    trust_remote_code=True  # 支援自訂分詞器
)
```

這允許載入包含自訂 Python 程式碼的分詞器。

## 網路加速

### 使用 Hugging Face 鏡像站

若下載速度較慢，可使用鏡像站：

```bash
# 設定環境變數
export HF_ENDPOINT="https://hf-mirror.com"

# 然後執行審計
llm-testkit audit --config my_audit.yaml
```

### 使用代理

```bash
# HTTP 代理
export HTTP_PROXY="http://proxy.example.com:8080"
export HTTPS_PROXY="http://proxy.example.com:8080"

# SOCKS 代理
export ALL_PROXY="socks5://proxy.example.com:1080"
```

## 權限與授權

### 需要申請權限的模型

以下模型需要在 Hugging Face 申請存取權限：

1. **Meta Llama 系列**
   - 申請網址：https://huggingface.co/meta-llama
   - 申請後使用 `huggingface-cli login` 登入

2. **Google Gemma 系列**
   - 需要同意授權條款
   - 首次使用時會自動提示

### 登入 Hugging Face

```bash
# 安裝 CLI
pip install huggingface_hub

# 登入（需要 Access Token）
huggingface-cli login

# 輸入你的 Access Token
# Token 可在 https://huggingface.co/settings/tokens 取得
```

## 離線使用

若需要在離線環境使用審計模組，請預先下載所需的分詞器：

```bash
# 1. 在有網路的環境下載模型
huggingface-cli download meta-llama/Llama-3.1-8B --local-dir ./models/llama31

# 2. 將模型目錄複製到離線環境

# 3. 在配置中使用本地路徑
# tokenizer:
#   model_name_or_path: "./models/llama31"
```

## 模型選擇建議

### 測試與開發

- **GPT-2**: 公開可用，下載快速，適合快速測試
- **Qwen/Qwen2.5-7B**: 公開可用，支援中文，適合開發

### 生產環境審計

- **Meta Llama 3.1**: 業界標準，廣泛使用
- **Qwen 2.5**: 中文支援優秀，效能良好
- **Mistral**: 開源友好，效能優秀

### 資源受限環境

- **Microsoft Phi-2**: 小型高效
- **GPT-2**: 最小模型，適合測試

## 疑難排解

### 分詞器下載失敗

請參考 [troubleshooting.md](troubleshooting.md) 中的「分詞器下載失敗」章節。

### 權限問題

若遇到權限錯誤：

1. 確認已申請模型存取權限
2. 使用 `huggingface-cli login` 登入
3. 確認 Access Token 有效

### 自訂分詞器載入失敗

若遇到自訂分詞器載入錯誤：

1. 確認程式碼中已啟用 `trust_remote_code=True`（審計模組已預設啟用）
2. 檢查模型是否包含自訂程式碼
3. 嘗試手動載入測試：

```python
from transformers import AutoTokenizer

tokenizer = AutoTokenizer.from_pretrained(
    "THUDM/glm-4-9b",
    trust_remote_code=True
)
```

## 相關文件

- [審計模組使用指南](audit-guide.md)
- [配置檔案說明](configuration.md)
- [環境變數說明](environment-variables.md)
- [疑難排解](troubleshooting.md)
