"""指標計算工具模組

提供各種評估指標的計算函數，用於檢測器中量化模型行為差異。
"""

import json
import re


def exact_match(pred: str, ref: str) -> float:
    """計算精確匹配分數

    比較預測文字與參考文字是否完全相同（忽略前後空白）。

    Args:
        pred: 預測文字
        ref: 參考文字

    Returns:
        1.0 表示完全匹配，0.0 表示不匹配

    Examples:
        >>> exact_match("hello", "hello")
        1.0
        >>> exact_match("hello ", " hello")
        1.0
        >>> exact_match("hello", "world")
        0.0
    """
    return 1.0 if pred.strip() == ref.strip() else 0.0


def rouge_l(pred: str, ref: str) -> float:
    """計算 ROUGE-L F1 分數

    基於最長公共子序列（LCS）計算 ROUGE-L 分數。
    使用字元級別的 LCS，適用於中英文混合文本。

    Args:
        pred: 預測文字
        ref: 參考文字

    Returns:
        ROUGE-L F1 分數（0.0 到 1.0）

    Examples:
        >>> rouge_l("the cat sat", "the cat sat on mat")
        0.8571428571428571
        >>> rouge_l("hello", "world")
        0.4
    """
    if not pred or not ref:
        return 0.0

    # 計算 LCS 長度
    lcs_len = _lcs_length(pred, ref)

    if lcs_len == 0:
        return 0.0

    # 計算 precision 和 recall
    precision = lcs_len / len(pred) if len(pred) > 0 else 0.0
    recall = lcs_len / len(ref) if len(ref) > 0 else 0.0

    # 計算 F1 分數
    if precision + recall == 0:
        return 0.0

    f1 = 2 * precision * recall / (precision + recall)
    return f1


def _lcs_length(s1: str, s2: str) -> int:
    """計算兩個字串的最長公共子序列長度

    使用動態規劃演算法計算 LCS。

    Args:
        s1: 第一個字串
        s2: 第二個字串

    Returns:
        LCS 長度
    """
    m, n = len(s1), len(s2)

    # 建立 DP 表格
    dp = [[0] * (n + 1) for _ in range(m + 1)]

    # 填充 DP 表格
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if s1[i - 1] == s2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])

    return dp[m][n]


def hamming_distance(tokens_a: list[int], tokens_b: list[int], k: int = 10) -> int:
    """計算前 k 個 token 的 Hamming 距離

    比較兩個 token 序列前 k 個位置的差異數量。
    用於檢測微擾穩定性和量化影響。

    Args:
        tokens_a: 第一個 token ID 列表
        tokens_b: 第二個 token ID 列表
        k: 比較的前綴長度（預設 10）

    Returns:
        Hamming 距離（不同位置的數量）

    Examples:
        >>> hamming_distance([1, 2, 3, 4], [1, 2, 5, 4], k=4)
        1
        >>> hamming_distance([1, 2, 3], [4, 5, 6], k=3)
        3
        >>> hamming_distance([1, 2], [1, 2, 3, 4], k=4)
        2
    """
    # 取前 k 個 token
    prefix_a = tokens_a[:k]
    prefix_b = tokens_b[:k]

    # 計算較短序列的長度
    min_len = min(len(prefix_a), len(prefix_b))

    # 計算不同位置的數量
    distance = sum(1 for i in range(min_len) if prefix_a[i] != prefix_b[i])

    # 加上長度差異（較長序列的額外 token）
    distance += abs(len(prefix_a) - len(prefix_b))

    return distance


def json_valid(text: str) -> bool:
    """驗證 JSON 合法性

    檢查文字是否為合法的 JSON 格式。
    用於檢測模型的結構化輸出能力。

    Args:
        text: 要驗證的文字

    Returns:
        True 表示合法 JSON，False 表示非法

    Examples:
        >>> json_valid('{"key": "value"}')
        True
        >>> json_valid('{"key": "value"')
        False
        >>> json_valid('not json')
        False
    """
    try:
        json.loads(text.strip())
        return True
    except (json.JSONDecodeError, ValueError):
        return False


def extract_first_int(text: str) -> int | None:
    """提取文本中第一個整數

    使用正則表達式提取文本中出現的第一個整數（支援負數）。
    用於驗證算術測試的答案。

    Args:
        text: 要提取的文字

    Returns:
        第一個整數，若無整數則回傳 None

    Examples:
        >>> extract_first_int("The answer is 42")
        42
        >>> extract_first_int("Result: -123 and 456")
        -123
        >>> extract_first_int("No numbers here")
        None
        >>> extract_first_int("3.14 is not an integer but 7 is")
        7
    """
    # 匹配整數（支援負數）
    match = re.search(r"-?\d+", text)
    if match:
        return int(match.group())
    return None
