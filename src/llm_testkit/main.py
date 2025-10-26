"""統一 CLI 進入點。

提供 llm-testkit 命令列工具的主要進入點，支援多個子命令。
"""

import argparse
import sys


def main() -> int:
    """主 CLI 進入點。

    建立主 parser 並註冊所有子命令，然後路由到對應的 handler。

    Returns:
        退出碼（0 表示成功，非 0 表示失敗）
    """
    parser = argparse.ArgumentParser(
        prog="llm-testkit",
        description="LLM 測試工具包",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
可用的子命令:
  audit     LLM API 黑盒審計工具

使用 'llm-testkit <command> --help' 查看各子命令的詳細說明。
        """,
    )

    # 建立 subparsers 用於註冊子命令
    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
        help="可用的子命令",
    )

    # 註冊 audit subcommand
    from llm_testkit.audit.cli import register_subcommand as register_audit

    register_audit(subparsers)

    # 未來可在此註冊其他 subcommands
    # 例如:
    # from llm_testkit.generation.cli import register_subcommand as register_generation
    # register_generation(subparsers)

    try:
        # 解析參數並執行對應的 handler
        args = parser.parse_args()
        return args.func(args)

    except KeyboardInterrupt:
        print("\n操作已取消", file=sys.stderr)
        return 130

    except Exception as e:
        print(f"執行錯誤: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
