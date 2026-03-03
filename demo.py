#!/usr/bin/env python3
"""
AgenticBT 端到端 Demo
=====================
8 种策略展示 AI Agent 的认知能力和框架全能力。

快速开始：
    # Mock 策略（无需 API key）
    python demo.py --mock
    python demo.py --mock --strategy bracket_atr
    python demo.py --mock --strategy all

    # LLM 策略（需要 API key）
    ANTHROPIC_API_KEY=sk-ant-... python demo.py --strategy free_play

    # 自定义 CSV
    OPENAI_API_KEY=sk-... python demo.py --provider openai --csv data.csv
"""

import argparse
import os
import sys
import time
from datetime import datetime

import pandas as pd


# ── .env 加载器 ──────────────────────────────────────────────────────────────
def _load_dotenv(path: str = ".env") -> None:
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key   = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
    except FileNotFoundError:
        pass


# ── 路径设置 ─────────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from agenticbt import BacktestConfig, LLMAgent, load_csv, make_sample_data, run
from agenticbt.models import CommissionConfig, RiskConfig
from examples.strategies import STRATEGIES, StrategyDef, get_strategy, list_strategies


# ─────────────────────────────────────────────────────────────────────────────
# 结果报告
# ─────────────────────────────────────────────────────────────────────────────

def print_report(result, elapsed: float, strategy_name: str = "") -> None:
    p = result.performance
    c = result.compliance
    sep = "─" * 55

    header = f"  AgenticBT 回测报告"
    if strategy_name:
        header += f"  [{strategy_name}]"

    print(f"\n{'═' * 55}")
    print(header)
    print(f"{'═' * 55}")

    print(f"\n【绩效指标】")
    print(sep)
    initial = p.equity_curve[0] if p.equity_curve else 100_000
    final   = p.equity_curve[-1] if p.equity_curve else initial
    print(f"  总收益率      {p.total_return * 100:+.2f}%")
    print(f"  初始权益      {initial:,.0f}")
    print(f"  最终权益      {final:,.0f}   ({final - initial:+,.0f})")
    print(f"  最大回撤      {p.max_drawdown * 100:.2f}%")
    print(f"  回撤持续      {p.max_dd_duration} bar")
    print(f"  夏普比率      {p.sharpe_ratio:.3f}  (年化)")
    print(f"  索提诺比率    {p.sortino_ratio:.3f}")
    print(f"  年化波动率    {p.volatility * 100:.2f}%")
    print(f"  CAGR          {p.cagr * 100:+.2f}%")
    print(f"  总交易次数    {p.total_trades}")
    if p.total_trades > 0:
        print(f"  胜率          {p.win_rate * 100:.1f}%")
        pf = p.profit_factor
        print(f"  盈亏比        {pf:.2f}" if pf != float('inf') else "  盈亏比        ∞ (无亏损)")
        print(f"  平均单笔      {p.avg_trade_return:+,.2f}")
        print(f"  最佳单笔      {p.best_trade:+,.2f}")
        print(f"  最差单笔      {p.worst_trade:+,.2f}")

    print(f"\n【遵循度报告】")
    print(sep)
    print(f"  总决策次数    {c.total_decisions}")
    for action, cnt in sorted(c.action_distribution.items()):
        pct = cnt / c.total_decisions * 100
        print(f"  {action:<10}    {cnt:>4} 次  ({pct:.0f}%)")
    print(f"  使用指标次数  {c.decisions_with_indicators} / {c.total_decisions}")

    print(f"\n【回测元信息】")
    print(sep)
    print(f"  耗时          {elapsed:.1f}s")
    print(f"  LLM 调用次数  {result.total_llm_calls}")
    print(f"  Token 消耗    {result.total_tokens:,}")
    print(f"  工作空间      {result.workspace_path}")

    decisions = result.decisions
    sample = decisions[:3] + (["..."] if len(decisions) > 6 else []) + decisions[-3:]
    print(f"\n【决策日志（共 {len(decisions)} 条）】")
    print(sep)
    for d in sample:
        if d == "...":
            print("  ...")
            continue
        dt = d.datetime.strftime("%Y-%m-%d") if isinstance(d.datetime, datetime) else str(d.datetime)
        tag = {"buy": "🔼 买", "sell": "🔽 卖", "close": "⬛ 平", "hold": "⏸ 观"}.get(d.action, d.action)
        print(f"  {dt}  {tag}  {d.reasoning[:50]}")

    print(f"\n{'═' * 55}\n")


def print_comparison(results: list[tuple[str, object, float]]) -> None:
    """打印多策略对比摘要表"""
    print(f"\n{'═' * 86}")
    print("  策略对比摘要")
    print(f"{'═' * 86}")
    print(f"  {'策略':<20s} {'收益率':>8s} {'回撤':>8s} {'夏普':>8s} {'索提诺':>8s} {'波动率':>8s} {'交易':>6s} {'胜率':>6s}")
    print(f"  {'─' * 76}")
    for name, result, _ in results:
        p = result.performance
        wr = f"{p.win_rate*100:.0f}%" if p.total_trades > 0 else "N/A"
        print(
            f"  {name:<20s} {p.total_return*100:>+7.2f}% {p.max_drawdown*100:>7.2f}% "
            f"{p.sharpe_ratio:>7.3f} {p.sortino_ratio:>7.3f} {p.volatility*100:>7.2f}% "
            f"{p.total_trades:>6d} {wr:>6s}"
        )
    print(f"{'═' * 86}\n")


# ─────────────────────────────────────────────────────────────────────────────
# 单策略运行
# ─────────────────────────────────────────────────────────────────────────────

def _build_data(strat: StrategyDef, csv_path: str | None, bars_override: int | None) -> tuple:
    """构建数据和 symbol，返回 (data, symbol)"""
    if csv_path:
        df = load_csv(csv_path)
        bars = bars_override or strat.bars
        return df.head(bars), strat.symbol

    bars = bars_override or strat.bars

    if strat.extra_symbols:
        # 多资产：dict[str, DataFrame]
        data = {strat.symbol: make_sample_data(strat.symbol, periods=bars, seed=strat.seed, regime=strat.regime)}
        for sym, seed in strat.extra_symbols:
            data[sym] = make_sample_data(sym, periods=bars, seed=seed, regime=strat.regime)
        return data, strat.symbol

    return make_sample_data(strat.symbol, periods=bars, seed=strat.seed, regime=strat.regime), strat.symbol


def _run_strategy(
    strat: StrategyDef,
    args,
) -> tuple[object, float] | None:
    """运行单个策略，返回 (result, elapsed) 或 None（跳过）"""
    is_mock = args.mock

    # LLM-only 策略在 mock 模式下跳过
    if is_mock and strat.mock_cls is None:
        print(f"\n跳过 [{strat.name}]: 此策略需要 LLM，请去掉 --mock 并配置 API key\n")
        return None

    data, symbol = _build_data(strat, args.csv, args.bars)

    # Agent
    if is_mock:
        agent = strat.mock_cls()
        print(f"策略: {strat.name} — {strat.description}")
        print(f"模式: Mock Agent | regime={strat.regime} | bars={strat.bars}")
    else:
        base_url, api_key, model = _resolve_provider(args.provider, args.model)
        agent = LLMAgent(model=model, base_url=base_url, api_key=api_key, max_rounds=strat.max_rounds)
        print(f"策略: {strat.name} — {strat.description}")
        print(f"模式: LLM Agent ({args.provider} / {model})")

    config = BacktestConfig(
        data=data,
        symbol=symbol,
        strategy_prompt=strat.llm_prompt,
        risk=strat.risk,
        commission=CommissionConfig(rate=0.001),
        decision_start_bar=strat.decision_start_bar,
    )

    bars_count = len(data) if isinstance(data, pd.DataFrame) else len(next(iter(data.values())))
    print(f"开始回测: {bars_count} 根 bar ...")
    t0 = time.time()
    result = run(config, agent=agent)
    elapsed = time.time() - t0

    return result, elapsed


# ─────────────────────────────────────────────────────────────────────────────
# CLI 入口
# ─────────────────────────────────────────────────────────────────────────────

def main():
    _load_dotenv()
    strategy_names = list_strategies() + ["all"]
    parser = argparse.ArgumentParser(description="AgenticBT 端到端 Demo")
    parser.add_argument("--provider", choices=["claude", "openai", "ollama"], default="claude",
                        help="LLM 提供商 (default: claude)")
    parser.add_argument("--model", default=None, help="模型名称（覆盖默认值）")
    parser.add_argument("--csv",   default=None, help="自定义 CSV 路径")
    parser.add_argument("--bars",  type=int, default=None, help="覆盖策略默认 bar 数量")
    parser.add_argument("--mock",  action="store_true", help="使用 mock agent（无需 API key）")
    parser.add_argument("--strategy", choices=strategy_names, default="rsi",
                        help="策略名称 (default: rsi)")
    args = parser.parse_args()

    if args.strategy == "all":
        # 运行所有策略
        results = []
        for name in list_strategies():
            strat = get_strategy(name)
            outcome = _run_strategy(strat, args)
            if outcome:
                result, elapsed = outcome
                print_report(result, elapsed, strategy_name=name)
                results.append((name, result, elapsed))
        if len(results) > 1:
            print_comparison(results)
    else:
        strat = get_strategy(args.strategy)
        outcome = _run_strategy(strat, args)
        if outcome:
            result, elapsed = outcome
            print_report(result, elapsed, strategy_name=args.strategy)


def _resolve_provider(provider: str, model_override: str | None) -> tuple[str | None, str | None, str]:
    if provider == "claude":
        base_url = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1/")
        api_key  = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY")
        model    = model_override or "claude-sonnet-4-20250514"
    elif provider == "openai":
        base_url = os.environ.get("OPENAI_BASE_URL")
        api_key  = os.environ.get("OPENAI_API_KEY")
        model    = model_override or "gpt-4o-mini"
    elif provider == "ollama":
        base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1/")
        api_key  = "ollama"
        model    = model_override or "qwen2.5:7b"
    else:
        raise ValueError(f"未知提供商: {provider}")

    if not api_key and provider != "ollama":
        print(f"警告: 未找到 API key（环境变量 ANTHROPIC_API_KEY / OPENAI_API_KEY）")
        print("使用 --mock 可跳过 API 调用\n")

    return base_url, api_key, model


if __name__ == "__main__":
    main()
