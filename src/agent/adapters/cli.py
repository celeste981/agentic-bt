"""
[INPUT]: dotenv, agent.runtime
[OUTPUT]: main — CLI 入口（使用 runtime 统一组装 Kernel；Session 落盘到 state_dir）
[POS]: 用户交互通道（CLI），尽量薄；业务组装逻辑下沉到 runtime
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

import os
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from agent.kernel import Session
from agent.runtime import AgentConfig, build_kernel_bundle
from agent.session_store import SessionStore


# ─────────────────────────────────────────────────────────────────────────────
# 启动流程
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    """CLI REPL — 完整 Agent 生命周期"""

    # ── 1. 加载环境变量 ──
    load_dotenv()

    config = AgentConfig.from_env()
    # 兼容：CLI 历史行为默认启用 bash；IM 入口仍默认关闭。
    raw_enable_bash = os.getenv("ENABLE_BASH")
    if raw_enable_bash is None or not raw_enable_bash.strip():
        config = replace(config, enable_bash=True)
    if not config.api_key:
        print("错误: 未设置 API_KEY，请配置 .env 文件")
        sys.exit(1)
    if not config.tushare_token:
        print("警告: 未设置 TUSHARE_TOKEN，market_ohlcv 将不可用")

    # ── 2. 组装 Kernel（runtime） ──
    bundle = build_kernel_bundle(
        config=config,
        adapter_name="cli",
        conversation_id="cli",
        cwd=Path.cwd(),
    )
    kernel = bundle.kernel
    workspace = bundle.workspace

    # ── 3. 确认回调 ──
    def _cli_confirm(path: str) -> bool:
        answer = input(f"\n确认操作 {path}? [y/n] ").strip().lower()
        return answer in ("y", "yes")

    kernel.on_confirm(_cli_confirm)

    # ── 4. Session 持久化（state_dir） + 兼容迁移 ──
    legacy_path = workspace / ".session.json"
    if legacy_path.exists() and not bundle.session_path.exists():
        legacy = Session.load(legacy_path)
        bundle.session_store.save(legacy)

    session = bundle.session_store.load()
    session.id = "cli"
    if session.history:
        print(f"已恢复会话（{len(session.history)} 条历史）")
    else:
        session = Session(session_id="cli")

    # ── 9. REPL ──
    print(f"投资助手已启动 | 模型: {config.model} | trace → {bundle.trace_path}")
    print("输入 quit 退出，/help 查看命令")
    try:
        _repl(kernel, session, bundle.session_store, bundle)
    finally:
        bundle.session_store.save(session)
        # 保存路径由 store 决定；CLI 不需要额外打印绝对路径


def _repl(
    kernel: Any,
    session: Session,
    store: SessionStore,
    bundle: Any,
) -> None:
    """交互循环"""
    while True:
        try:
            user_input = input("\n你: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见。")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("再见。")
            break

        # 命令路由
        if user_input.startswith("/"):
            cmd = user_input.split()[0].lower()
            if cmd in ("/new", "/reset"):
                session.history.clear()
                session.summary = None
                store.save(session)
                print("已开始新会话。")
                continue
            if cmd == "/compact":
                from agent.context_ops import compact_history, estimate_tokens

                before_tokens = estimate_tokens(session.history)
                result = compact_history(
                    client=kernel.client, model=kernel.model,
                    history=session.history,
                )
                session.history = result.retained
                if result.summary:
                    session.summary = (
                        f"{session.summary}\n\n{result.summary}"
                        if session.summary else result.summary
                    )
                after_tokens = estimate_tokens(session.history)
                store.save(session)
                kernel.emit("context.compacted", {
                    "trigger": "manual",
                    "messages_compressed": result.compressed_count,
                    "messages_retained": result.retained_count,
                    "tokens_before": before_tokens,
                    "tokens_after": after_tokens,
                    "summary": result.summary,
                })
                print(
                    f"已压缩上下文。\n"
                    f"消息: {result.compressed_count + result.retained_count} → {result.retained_count}\n"
                    f"Token 估算: ~{before_tokens} → ~{after_tokens}"
                )
                continue
            if cmd == "/context":
                from agent.context_ops import context_info

                info = context_info(session.history, kernel.context_window)
                print(
                    f"消息数: {info.message_count}（user: {info.user_message_count}）\n"
                    f"估算 Token: ~{info.estimated_tokens}\n"
                    f"Context Window: {info.context_window}\n"
                    f"使用率: {info.usage_pct}%"
                )
                continue
            if cmd == "/help":
                print(
                    "可用命令:\n"
                    "  /new, /reset  — 开始新会话\n"
                    "  /compact      — 压缩上下文\n"
                    "  /context      — 显示上下文统计\n"
                    "  /help         — 显示此帮助\n"
                    "  quit          — 退出"
                )
                continue

        reply = kernel.turn(user_input, session)
        print(f"\n助手: {reply}")

        # 每轮自动保存（防崩溃丢失）
        store.save(session)


if __name__ == "__main__":
    main()
