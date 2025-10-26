"""檔案 I/O 工具模組。

提供通用的檔案讀寫功能。
"""

import json
from pathlib import Path
from typing import Any


def read_json(filepath: str | Path) -> dict[str, Any] | list[Any]:
    """讀取 JSON 檔案。

    Args:
        filepath: 檔案路徑

    Returns:
        解析後的資料
    """
    filepath = Path(filepath)
    with filepath.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(data: dict[str, Any] | list[Any], filepath: str | Path) -> None:
    """寫入 JSON 檔案。

    Args:
        data: 要寫入的資料
        filepath: 檔案路徑
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    with filepath.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def read_jsonl(filepath: str | Path) -> list[dict[str, Any]]:
    """讀取 JSONL 檔案。

    Args:
        filepath: 檔案路徑

    Returns:
        資料列表
    """
    filepath = Path(filepath)
    data = []

    with filepath.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))

    return data


def write_jsonl(data: list[dict[str, Any]], filepath: str | Path) -> None:
    """寫入 JSONL 檔案。

    Args:
        data: 資料列表
        filepath: 檔案路徑
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    with filepath.open("w", encoding="utf-8") as f:
        for item in data:
            json.dump(item, f, ensure_ascii=False)
            f.write("\n")


def append_jsonl(data: list[dict[str, Any]], filepath: str | Path) -> None:
    """追加資料到 JSONL 檔案。

    Args:
        data: 資料列表
        filepath: 檔案路徑
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    with filepath.open("a", encoding="utf-8") as f:
        for item in data:
            json.dump(item, f, ensure_ascii=False)
            f.write("\n")
