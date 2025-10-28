# 環境變數說明

本文件說明 LLM TestKit 如何使用環境變數。

## 支援的環境變數

### API 配置

#### `OPENAI_API_KEY`
- **必要性**: 必要（當配置檔中 `api_key: null` 時）
- **用途**: OpenAI API 金鑰
- **範例**: `sk-proj-xxxxxxxxxxxxx`
- **說明**: 
  - 當審計配置檔中 `endpoint.api_key` 設為 `null` 時，會自動從此環境變數讀取
  - 建議透過環境變數設定，避免將金鑰寫入配置檔

#### `OPENAI_BASE_URL`
- **必要性**: 可選
- **用途**: 自訂 API 端點
- **預設值**: `https://api.openai.com/v1`
- **範例**: 
  - Azure OpenAI: `https://your-resource.openai.azure.com/`
  - 本地部署: `http://localhost:8000/v1`
  - 第三方代理: `https://api.example.com/v1`
- **說明**: 用於連接 OpenAI 相容的第三方 API

#### `ANTHROPIC_API_KEY`
- **必要性**: 可選（使用 Anthropic API 時必要）
- **用途**: Anthropic API 金鑰
- **範例**: `sk-ant-xxxxxxxxxxxxx`
- **說明**: 
  - 用於呼叫 Anthropic Claude 模型 API
  - 當配置檔中 `anthropic.api_key` 設為 `null` 時，會自動從此環境變數讀取
  - 建議透過環境變數設定，避免將金鑰寫入配置檔

#### `ANTHROPIC_BASE_URL`
- **必要性**: 可選
- **用途**: 自訂 Anthropic API 端點
- **預設值**: `https://api.anthropic.com`
- **範例**: `https://api.anthropic.com`
- **說明**: 用於連接自訂的 Anthropic API 端點或代理

### 日誌配置

#### `LOG_LEVEL`
- **必要性**: 可選
- **用途**: 控制日誌輸出等級
- **預設值**: `INFO`
- **可選值**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- **說明**: 
  - `DEBUG`: 顯示所有除錯資訊
  - `INFO`: 顯示一般資訊（推薦）
  - `WARNING`: 只顯示警告和錯誤
  - `ERROR`: 只顯示錯誤
  - `CRITICAL`: 只顯示嚴重錯誤

### Hugging Face 配置

#### `HF_ENDPOINT`
- **必要性**: 可選
- **用途**: Hugging Face Hub 鏡像站
- **預設值**: `https://huggingface.co`
- **範例**: `https://hf-mirror.com`
- **說明**: 
  - 用於加速分詞器模型下載
  - 在中國大陸等地區可能需要使用鏡像站

## 設定方式

### 方法一：使用 .env 檔案（推薦）

1. 複製範例檔案：
   ```bash
   cp .env.example .env
   ```

2. 編輯 `.env` 檔案：
   ```env
   OPENAI_API_KEY=sk-your-actual-api-key-here
   OPENAI_BASE_URL=https://api.example.com/v1
   ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here
   ANTHROPIC_BASE_URL=https://api.anthropic.com
   LOG_LEVEL=INFO
   ```

3. `.env` 檔案會被自動載入（透過 `python-dotenv`）

**優點：**
- 集中管理環境變數
- `.env` 已被 `.gitignore` 排除，不會意外提交
- 適合本地開發

### 方法二：系統環境變數

**Linux/macOS:**
```bash
export OPENAI_API_KEY="your-api-key-here"
export OPENAI_BASE_URL="https://api.example.com/v1"
export ANTHROPIC_API_KEY="your-anthropic-key-here"
export ANTHROPIC_BASE_URL="https://api.anthropic.com"
export LOG_LEVEL=INFO
```

**Windows (PowerShell):**
```powershell
$env:OPENAI_API_KEY="your-api-key-here"
$env:OPENAI_BASE_URL="https://api.example.com/v1"
$env:ANTHROPIC_API_KEY="your-anthropic-key-here"
$env:ANTHROPIC_BASE_URL="https://api.anthropic.com"
$env:LOG_LEVEL="INFO"
```

**Windows (CMD):**
```cmd
set OPENAI_API_KEY=your-api-key-here
set OPENAI_BASE_URL=https://api.example.com/v1
set ANTHROPIC_API_KEY=your-anthropic-key-here
set ANTHROPIC_BASE_URL=https://api.anthropic.com
set LOG_LEVEL=INFO
```

**優點：**
- 適合 CI/CD 環境
- 適合容器化部署
- 不需要額外檔案

### 方法三：配置檔直接設定（不推薦）

在 YAML 配置檔中直接設定：
```yaml
endpoint:
  api_key: "sk-your-api-key-here"  # 不推薦！
```

**缺點：**
- 容易意外提交到版本控制
- 不安全
- 不建議使用

## 優先順序

當同一個設定在多個地方都有定義時，優先順序如下（由高到低）：

1. **系統環境變數** - 最高優先級
2. **`.env` 檔案** - 中等優先級
3. **配置檔設定** - 最低優先級

### 範例

假設有以下設定：

**系統環境變數：**
```bash
export OPENAI_API_KEY="env-key"
```

**`.env` 檔案：**
```env
OPENAI_API_KEY=dotenv-key
```

**配置檔 `audit.yaml`：**
```yaml
endpoint:
  api_key: "config-key"
```

**實際使用的值：**
- 如果配置檔設為 `api_key: null`，則使用 `env-key`（系統環境變數）
- 如果配置檔設為 `api_key: "config-key"`，則使用 `config-key`（配置檔優先）

## 審計模組的環境變數使用

審計模組主要透過 YAML 配置檔設定參數，環境變數主要用於：

1. **敏感資訊**: API 金鑰
2. **環境特定設定**: API 端點、日誌等級
3. **開發便利性**: 避免修改配置檔

### 推薦做法

**配置檔 (`configs/my_audit.yaml`)：**
```yaml
endpoint:
  url: "https://api.example.com/v1/chat/completions"
  model: "meta-llama/Llama-3.1-8B"
  api_key: null  # 從環境變數讀取

tokenizer:
  model_name_or_path: "meta-llama/Llama-3.1-8B"

# ... 其他配置
```

**環境變數 (`.env`)：**
```env
OPENAI_API_KEY=sk-your-actual-api-key-here
```

**執行：**
```bash
llm-testkit audit --config configs/my_audit.yaml
```

這樣可以：
- 將配置檔提交到版本控制（不含敏感資訊）
- 將 API 金鑰保存在本地 `.env` 檔案（不提交）
- 在不同環境使用不同的 API 金鑰

## 驗證環境變數

檢查環境變數是否正確設定：

```bash
# Linux/macOS
echo $OPENAI_API_KEY
echo $OPENAI_BASE_URL

# Windows (PowerShell)
echo $env:OPENAI_API_KEY
echo $env:OPENAI_BASE_URL

# Python
python -c "import os; print('OPENAI_API_KEY:', 'SET' if os.getenv('OPENAI_API_KEY') else 'NOT SET')"
```

## 常見問題

### Q: 為什麼我的 API 金鑰沒有被讀取？

**A:** 檢查以下幾點：
1. 確認 `.env` 檔案在專案根目錄
2. 確認 `.env` 檔案格式正確（`KEY=value`，不要有引號）
3. 確認配置檔中 `api_key: null`
4. 重新啟動終端或重新載入環境變數

### Q: 可以在配置檔中直接寫 API 金鑰嗎？

**A:** 技術上可以，但強烈不建議：
- 容易意外提交到 Git
- 不安全
- 不便於管理多個環境

建議使用環境變數或 `.env` 檔案。

### Q: CI/CD 環境如何設定環境變數？

**A:** 大多數 CI/CD 平台都支援設定環境變數：
- **GitHub Actions**: Repository Settings → Secrets
- **GitLab CI**: Settings → CI/CD → Variables
- **Jenkins**: Credentials 管理
- **Docker**: `docker run -e OPENAI_API_KEY=xxx`

### Q: 如何在 Docker 容器中使用環境變數？

**A:** 使用 `-e` 或 `--env-file` 參數：

```bash
# 方法一：直接傳遞
docker run -e OPENAI_API_KEY=xxx my-image

# 方法二：使用 .env 檔案
docker run --env-file .env my-image
```

或在 `docker-compose.yml` 中：
```yaml
services:
  app:
    image: my-image
    env_file:
      - .env
    # 或
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
```
