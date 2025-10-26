"""審計 CLI 模組。

提供命令列介面執行 LLM API 黑盒審計。
"""

import argparse
import asyncio
import sys
from pathlib import Path

from llm_testkit.audit.config import AuditConfig
from llm_testkit.audit.runner import AuditRunner


def register_subcommand(subparsers: argparse._SubParsersAction) -> None:
    """註冊 audit subcommand。

    Args:
        subparsers: argparse subparsers 物件
    """
    parser = subparsers.add_parser(
        "audit",
        help="LLM API 黑盒審計工具",
        description="執行 LLM API 黑盒審計，驗證模型一致性",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  llm-testkit audit --config configs/audit_example.yaml
  llm-testkit audit --config configs/audit_example.yaml --suite full
  llm-testkit audit --config configs/audit_example.yaml --output output/my_audit
        """,
    )

    parser.add_argument("--config", required=True, type=str, help="審計配置檔路徑（YAML 格式）")

    parser.add_argument("--suite", default="quick", type=str, help="測試套件名稱（預設: quick）")

    parser.add_argument(
        "--output", default="output/audit", type=str, help="報告輸出目錄（預設: output/audit）"
    )

    parser.set_defaults(func=audit_main)


def audit_main(args: argparse.Namespace) -> int:
    """Audit subcommand handler。

    Args:
        args: 命令列參數

    Returns:
        退出碼（0 表示成功，1 表示失敗）
    """
    return asyncio.run(_async_audit_main(args))


async def _async_audit_main(args: argparse.Namespace) -> int:
    """Async audit 主邏輯。

    Args:
        args: 命令列參數

    Returns:
        退出碼（0 表示成功，1 表示失敗）
    """
    # 驗證配置檔存在
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"錯誤: 配置檔不存在: {config_path}", file=sys.stderr)
        return 1

    try:
        # 載入配置
        print(f"載入配置檔: {config_path}")
        config = AuditConfig.from_yaml(config_path)

        # 建立審計執行器
        runner = AuditRunner(config)

        try:
            # 執行審計
            print(f"\n開始執行審計套件: {args.suite}")
            print("=" * 60)
            results = await runner.run_suite(args.suite)

            # 產生報告
            print("\n" + "=" * 60)
            print("產生報告...")
            runner.generate_report(results, args.output)

            # 顯示摘要
            passed_count = sum(1 for r in results if r.passed)
            total_count = len(results)
            print("\n" + "=" * 60)
            print("審計完成!")
            print(f"通過: {passed_count}/{total_count}")
            print(f"報告位置: {Path(args.output).absolute()}")

            # 根據結果決定退出碼
            return 0 if passed_count == total_count else 1

        finally:
            # 確保關閉資源
            await runner.close()

    except ValueError as e:
        print(f"配置錯誤: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"執行錯誤: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1
