"""分詞器模組

提供統一的分詞器介面，使用 Hugging Face transformers 載入官方分詞器。
"""

from transformers import AutoTokenizer


class Tokenizer:
    """分詞器抽象，使用 Hugging Face 官方分詞器

    支援所有 Hugging Face Hub 上的模型分詞器，包括：
    - Llama 系列 (meta-llama/Llama-3.1-8B)
    - Qwen 系列 (Qwen/Qwen2.5-7B)
    - GLM 系列 (THUDM/glm-4-9b)
    - 其他 OpenAI-compatible 模型

    Attributes:
        _tokenizer: Hugging Face AutoTokenizer 實例
    """

    def __init__(self, model_name_or_path: str):
        """初始化分詞器

        Args:
            model_name_or_path: Hugging Face 模型名稱或本地路徑
                例如: "meta-llama/Llama-3.1-8B", "Qwen/Qwen2.5-7B"

        Raises:
            RuntimeError: 當分詞器載入失敗時
        """
        try:
            self._tokenizer = AutoTokenizer.from_pretrained(
                model_name_or_path,
                trust_remote_code=True,  # 支援自訂分詞器（如 Qwen）
            )
        except Exception as e:
            raise RuntimeError(
                f"無法載入分詞器 {model_name_or_path}: {e}\n"
                f"請確認模型名稱正確或已下載到本地。\n"
                f"可使用以下命令預先下載：\n"
                f'  python -c "from transformers import AutoTokenizer; '
                f"AutoTokenizer.from_pretrained('{model_name_or_path}')\""
            ) from e

    def tokenize(self, text: str) -> list[int]:
        """分詞，回傳 token ID 列表

        Args:
            text: 要分詞的文字

        Returns:
            Token ID 列表

        Examples:
            >>> tokenizer = Tokenizer("meta-llama/Llama-3.1-8B")
            >>> tokenizer.tokenize("Hello world")
            [9906, 1917]
        """
        return self._tokenizer.encode(text, add_special_tokens=False)

    def count(self, text: str) -> int:
        """計算 token 數量

        Args:
            text: 要計算的文字

        Returns:
            Token 數量

        Examples:
            >>> tokenizer = Tokenizer("meta-llama/Llama-3.1-8B")
            >>> tokenizer.count("Hello world")
            2
        """
        return len(self.tokenize(text))

    def decode(self, token_ids: list[int]) -> str:
        """解碼 token ID 為文字

        Args:
            token_ids: Token ID 列表

        Returns:
            解碼後的文字

        Examples:
            >>> tokenizer = Tokenizer("meta-llama/Llama-3.1-8B")
            >>> tokenizer.decode([9906, 1917])
            'Hello world'
        """
        return self._tokenizer.decode(token_ids)
