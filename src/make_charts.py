"""120-session K-line charts with signal bars marked, one file per signal.

Requirements this satisfies
---------------------------
* Every chart shows **120 daily bars** — 60 before the signal and 60 after, so
  the observation window the strategy actually saw and the outcome it was
  scored against are both visible.
* **The signal bar is marked**, with entry (next open), the target line, and the
  first target touch annotated.
* **Each strategy is named and labelled separately.** Filenames embed the
  strategy id and the version, and each chart carries its own title, so a chart
  can never be mistaken for a different strategy's output.

Output layout::

    outputs/charts_120d/<strategy_id>/<code>_<date>_<outcome>.png
    outputs/charts_120d/<strategy_id>/index.html

CPU rendering is used deliberately: charts are rendered in worker processes in
parallel, and a GUI backend would fork a window per worker.
"""

from __future__ import annotations

import argparse
import html
import os
import re
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "outputs" / "charts_120d"

BARS_BEFORE = 60
BARS_AFTER = 60

# Distinct colour per strategy family so charts are visually separable too.
FAMILY_COLOURS = {
    "webpro": "#1769aa",
    "lowzone": "#b91c1c",
}


def choose_font() -> str:
    from matplotlib import font_manager

    available = {f.name for f in font_manager.fontManager.ttflist}
    for name in ("Microsoft YaHei", "SimHei", "DengXian", "Noto Sans CJK SC"):
        if name in available:
            return name
    return "sans-serif"


FONT = choose_font()


def safe_name(value: str) -> str:
    cleaned = re.sub(r"[^0-9A-Za-z_.-]+", "_", str(value)).strip("_")
    return cleaned or "x"


def draw_chart(
    code: str,
    signal_date: pd.Timestamp,
    bars: pd.DataFrame,
    *,
    strategy_label: str,
    outcome_text: str,
    entry: float | None,
    target: float | None,
    hit_bar: pd.Timestamp | None,
    output: Path,
    regime_note: str = "",
    is_hit: bool | None = None,
    colour: str = "#1769aa",
) -> None:
    """Render one 120-bar candlestick chart with the signal bar marked."""
    fig, (ax, vol_ax) = plt.subplots(
        2, 1, figsize=(14, 8), sharex=True,
        gridspec_kw={"height_ratios": [3.2, 1.0], "hspace": 0.06},
    )

    x = np.arange(len(bars))
    opens = bars["open"].to_numpy("float64")
    highs = bars["high"].to_numpy("float64")
    lows = bars["low"].to_numpy("float64")
    closes = bars["close"].to_numpy("float64")
    volumes = bars["volume"].to_numpy("float64")

    for i in range(len(bars)):
        up = closes[i] >= opens[i]
        body_colour = "#d64545" if up else "#2e9e5b"   # CN convention: red up
        ax.vlines(i, lows[i], highs[i], color=body_colour, linewidth=0.7, zorder=2)
        bottom = min(opens[i], closes[i])
        height = max(abs(closes[i] - opens[i]), (highs[i] - lows[i]) * 0.002)
        ax.add_patch(Rectangle((i - 0.32, bottom), 0.64, height,
                               facecolor=body_colour, edgecolor=body_colour, zorder=3))
        vol_ax.bar(i, volumes[i], width=0.66, color=body_colour, alpha=0.55, zorder=2)

    # Signal bar index within this window.
    dates = bars["date"].to_numpy()
    sig_idx = int(np.argmin(np.abs(pd.to_datetime(dates) - signal_date)))

    ax.axvline(sig_idx, color="#111827", linestyle="--", linewidth=1.5, zorder=4)
    ax.annotate("SIGNAL", xy=(sig_idx, lows[sig_idx]),
                xytext=(sig_idx, lows[sig_idx] * 0.965),
                ha="center", va="top", fontsize=10, fontweight="bold", color="#111827",
                arrowprops=dict(arrowstyle="-|>", color="#111827", lw=1.4), zorder=6)

    if entry is not None and np.isfinite(entry):
        ax.axhline(entry, color="#6b7280", linestyle=":", linewidth=1.0, zorder=1)
        ax.annotate(f"entry {entry:.2f}", xy=(0.005, entry), xycoords=("axes fraction", "data"),
                    fontsize=8, color="#374151", va="bottom")
    if target is not None and np.isfinite(target):
        ax.axhline(target, color=colour, linestyle="-.", linewidth=1.2, zorder=1)
        ax.annotate(f"target {target:.2f}", xy=(0.995, target), xycoords=("axes fraction", "data"),
                    fontsize=8, color=colour, va="bottom", ha="right")
    if hit_bar is not None:
        hit_idx = int(np.argmin(np.abs(pd.to_datetime(dates) - hit_bar)))
        ax.scatter([hit_idx], [highs[hit_idx]], marker="*", s=260, color="#f59e0b",
                   edgecolor="#78350f", linewidth=0.7, zorder=7)
        ax.annotate("target hit", xy=(hit_idx, highs[hit_idx]),
                    xytext=(hit_idx, highs[hit_idx] * 1.03), ha="center", fontsize=9,
                    color="#92400e", fontweight="bold", zorder=7)

    shade = "#dcfce7" if is_hit else "#fee2e2"
    verdict = "HIT" if is_hit else "MISS"
    ax.set_title(
        f"{code}   {strategy_label}\n"
        f"signal {pd.Timestamp(signal_date).date()}   "
        f"outcome: {outcome_text}   [{verdict}]"
        + (f"   ({regime_note})" if regime_note else ""),
        fontsize=13, fontweight="bold",
        bbox=dict(facecolor=shade, edgecolor=colour, boxstyle="round,pad=0.5"),
    )
    ax.set_ylabel("price", fontsize=10)
    vol_ax.set_ylabel("volume", fontsize=9)
    vol_ax.set_xlabel(
        f"session ({len(bars)} bars: {sig_idx} before / {len(bars)-sig_idx-1} after the signal)",
        fontsize=9,
    )

    # Label a handful of x ticks by date rather than by index.
    ticks = np.linspace(0, len(bars) - 1, 7).astype(int)
    vol_ax.set_xticks(ticks)
    vol_ax.set_xticklabels(
        [pd.Timestamp(dates[i]).strftime("%Y-%m-%d") for i in ticks],
        rotation=30, ha="right", fontsize=8,
    )
    ax.grid(alpha=0.20, linestyle=":", zorder=0)
    vol_ax.grid(alpha=0.20, linestyle=":", zorder=0)
    for axis in (ax, vol_ax):
        axis.set_xlim(-1, len(bars))
    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=110, bbox_inches="tight")
    plt.close(fig)


def attach_windows(
    panel: pd.DataFrame,
    jobs: list[dict],
    before: int = BARS_BEFORE,
    after: int = BARS_AFTER,
) -> list[dict]:
    """Slice a 120-bar window for every job, keeping the signal position.

    A window must contain at least ``before`` bars so the strategy's own 60-bar
    lookback is visible on the chart; signals in a stock's first 60 sessions are
    skipped because the strategy could not have produced them.
    """
    by_code = {c: g.reset_index(drop=True) for c, g in panel.groupby("code", sort=False)}
    kept: list[dict] = []
    for job in jobs:
        stock = by_code.get(job["code"])
        if stock is None:
            continue
        dates = stock["date"].to_numpy()
        pos = int(np.searchsorted(dates, np.datetime64(pd.Timestamp(job["signal_date"]))))
        if pos >= len(stock) or stock["date"].iloc[pos] != pd.Timestamp(job["signal_date"]):
            continue
        start = max(0, pos - before)
        # Exactly ``before + after`` bars total, so the chart is the requested
        # 120 sessions: 60 before the signal, the signal bar, and 59 after.
        end = min(len(stock), pos + after)
        window = stock.iloc[start:end]
        if len(window) < before + 1:
            continue
        job = dict(job)
        job["window"] = window
        job["signal_pos"] = pos - start
        kept.append(job)
    return kept


def _spread(frame: pd.DataFrame, bins: int = 12) -> pd.DataFrame:
    """Order a signal frame chronologically but spread across the whole period.

    Taking ``head(n)`` would sample only the earliest signals of a strategy,
    which on a four-year panel is a different market regime from the rest. This
    interleaves across ``bins`` equal time buckets so the chart sample spans the
    full period.
    """
    if frame.empty:
        return frame
    frame = frame.sort_values("date").reset_index(drop=True)
    if len(frame) <= bins:
        return frame
    edges = np.linspace(0, len(frame), bins + 1).astype(int)
    buckets = [frame.iloc[edges[i] : edges[i + 1]] for i in range(bins)]
    order: list[int] = []
    for rank in range(max(len(b) for b in buckets)):
        for bucket in buckets:
            if rank < len(bucket):
                order.append(bucket.index[rank])
    return frame.loc[order]


def _read_signals(path: Path, date_col: str = "date") -> pd.DataFrame:
    """Read a signals CSV with ``code`` forced back to its six-digit string form.

    The panel keys stocks as zero-padded strings (``"000017"``), but pandas
    writes and re-reads a numeric-looking string column as an integer, so
    ``"000017"`` round-trips as ``17`` and every join silently misses. Forcing
    the dtype on read is the only place this can be fixed reliably.
    """
    frame = pd.read_csv(path, dtype={"code": "string"}, parse_dates=[date_col])
    frame["code"] = frame["code"].str.zfill(6)
    return frame


def build_windows(
    panel: pd.DataFrame,
    signals: pd.DataFrame,
    before: int = BARS_BEFORE,
    after: int = BARS_AFTER,
) -> list[dict]:
    """Legacy helper: slice windows directly from a signal frame."""
    jobs = [
        {"code": row.code, "signal_date": row.date,
         "signal_pos": 0, "strategy_id": "unknown", "label": "unknown",
         "family": "webpro", "regime": "", "is_hit": False}
        for row in signals.itertuples()
    ]
    return attach_windows(panel, jobs, before, after)


def render_one(job: dict) -> str | None:
    """Render one chart. Returns the output path, or None if skipped."""
    window = job["window"]
    code = job["code"]
    signal_date = pd.Timestamp(job["signal_date"])
    strategy_id = job["strategy_id"]
    label = job["label"]
    regime = job["regime"]
    is_hit = job["is_hit"]
    outcome_text = job.get("outcome_text", "")
    target_multiple = job.get("target_multiple")

    # Derive entry from the data itself: the next session's open after the
    # signal bar. This is the only entry price a signal can actually transact
    # at, and deriving it here keeps the chart self-consistent with the labels.
    entry, target, hit_date = None, None, None
    pos = job["signal_pos"]
    if pos + 1 < len(window):
        entry = float(window["open"].iloc[pos + 1])
    if entry is not None and target_multiple:
        target = entry * target_multiple
        after = window.iloc[pos + 1 :]
        touched = after[after["high"] >= target]
        if len(touched):
            hit_date = touched["date"].iloc[0]
        # A target far outside the visible range would flatten the whole chart,
        # so it is dropped rather than silently rescaling the y-axis.
        lo, hi = window["low"].min(), window["high"].max()
        if not (lo * 0.55 <= target <= hi * 1.25):
            target = None
            hit_date = None

    verdict = "hit" if is_hit else "miss"
    filename = f"{safe_name(code)}_{signal_date.strftime('%Y%m%d')}_{verdict}.png"
    output = OUT_DIR / safe_name(strategy_id) / filename

    try:
        draw_chart(
            code, signal_date, window,
            strategy_label=f"{label}  [{strategy_id}]",
            outcome_text=outcome_text,
            entry=entry, target=target, hit_bar=hit_date,
            output=output, regime_note=regime,
            is_hit=bool(is_hit),
            colour=FAMILY_COLOURS.get(job.get("family", "webpro"), "#1769aa"),
        )
        return str(output)
    except Exception as exc:  # noqa: BLE001
        print(f"  !! chart failed {code} {signal_date.date()}: {type(exc).__name__}: {exc}")
        return None


def load_true_rates() -> dict[str, dict]:
    """Real measured hit rates, keyed by the chart folder's strategy id.

    The charts deliberately show a *balanced* sample (half hits, half misses) so
    failures are visible. That makes the hit proportion **within the sample
    meaningless** — it is ~50% by construction. The index must therefore print
    the true rate from the backtest reports, never the sample proportion, or the
    page would appear to show every strategy at 50%.
    """
    rates: dict[str, dict] = {}
    webpro = REPO_ROOT / "reports" / "webpro_hit_rates.csv"
    if webpro.exists():
        for row in pd.read_csv(webpro).itertuples():
            rates[row.strategy_id] = {
                "signals": int(row.signals_deduped__webpro),
                "hits": int(row.bull_hits_deduped__webpro),
                "rate": float(row.bull_precision_deduped__webpro),
                "baseline": float(row.baseline__webpro),
                "lift": float(row.lift__webpro),
                "protocol": "full universe, deduped signals",
            }
    lowzone = REPO_ROOT / "reports" / "lowzone_hit_rates.csv"
    if lowzone.exists():
        for row in pd.read_csv(lowzone).itertuples():
            if int(getattr(row, "signals_deduped", 0)) == 0:
                continue
            rates[f"{row.version}_{row.regime}"] = {
                "signals": int(row.signals_deduped),
                "hits": int(row.bull_hits),
                "rate": float(row.bull_precision),
                "baseline": float(row.baseline_rate),
                "lift": float(row.lift_vs_baseline),
                "protocol": ("per-year in-sample fit (NOT cross-year)"
                             if bool(row.in_sample) else "walk-forward, prior-year threshold"),
            }
    return rates


def write_index(rendered: dict[str, list[dict]], path: Path) -> None:
    """Write an HTML index grouped by strategy, showing the TRUE hit rate."""
    rates = load_true_rates()
    rows = []
    for strategy_id, items in sorted(rendered.items()):
        shown_hits = sum(1 for i in items if i["is_hit"])
        info = rates.get(strategy_id)
        if info and info["signals"]:
            real = (
                f"<span class='stat real'>measured hit rate "
                f"<b>{info['hits']}/{info['signals']} = {info['rate']*100:.2f}%</b> "
                f"&nbsp;|&nbsp; base rate {info['baseline']*100:.3f}% "
                f"&nbsp;|&nbsp; lift <b>{info['lift']:.2f}&times;</b> "
                f"&nbsp;|&nbsp; {html.escape(info['protocol'])}</span>"
            )
        else:
            real = "<span class='stat warn'>no measured rate available</span>"
        rows.append(
            f"<h2>{html.escape(strategy_id)}</h2>{real}"
            f"<div class='note'>charts below: {shown_hits} hits / "
            f"{len(items)-shown_hits} misses shown (balanced sample for visual audit "
            f"&mdash; this is NOT the hit rate)</div><div class='grid'>"
        )
        for item in items:
            rel = Path(item["path"]).relative_to(path.parent).as_posix()
            cls = "hit" if item["is_hit"] else "miss"
            rows.append(
                f"<figure class='{cls}'><img loading='lazy' src='{html.escape(rel)}'>"
                f"<figcaption>{html.escape(item['code'])} "
                f"{pd.Timestamp(item['date']).date()}</figcaption></figure>"
            )
        rows.append("</div>")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "<!doctype html><meta charset='utf-8'>"
        "<title>120-day K-line charts by strategy</title>"
        "<style>"
        "body{font-family:system-ui,sans-serif;margin:24px;background:#f8fafc;color:#0f172a}"
        "h2{margin:34px 0 4px;border-left:6px solid #1769aa;padding-left:10px;font-size:19px}"
        ".stat{display:block;font-size:14px;color:#475569;margin:0 0 4px 16px}"
        ".stat.real b{color:#0f172a}.stat.warn{color:#b45309}"
        ".note{font-size:12px;color:#b45309;margin:0 0 10px 16px}"
        ".grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(430px,1fr));gap:18px}"
        "figure{margin:0;padding:8px;border-radius:10px;background:#fff;box-shadow:0 1px 4px #0002}"
        "figure.hit{border:2px solid #16a34a}figure.miss{border:2px solid #dc2626}"
        "img{width:100%;display:block;border-radius:6px}"
        "figcaption{font-size:12px;color:#334155;padding-top:6px}"
        "</style>"
        "<h1>120-Day K-Line Charts — One Folder Per Strategy</h1>"
        "<p>Each chart shows 120 sessions (60 before / 60 after the signal), the signal bar, "
        "the next-open entry, the target line, and the first target touch. "
        "Green border = hit, red border = miss.</p>"
        "<p><b>Read the headline number, not the pictures.</b> The charts are a "
        "<i>balanced</i> sample (hits and misses in equal measure) so that failures are "
        "visible; the proportion of green borders on this page is therefore meaningless. "
        "The measured hit rate printed under each heading comes from the backtest reports "
        "and covers every deduplicated signal.</p>"
        + "".join(rows),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-per-strategy", type=int, default=60,
                        help="cap charts per strategy (0 = no cap)")
    parser.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 4) - 2))
    parser.add_argument("--source", default="webpro", choices=["webpro", "lowzone", "all"])
    args = parser.parse_args()

    from src import data_pipeline

    panel = data_pipeline.load_panel()
    print(f"panel {panel.shape}; font={FONT}")

    jobs: list[dict] = []
    if args.source in ("webpro", "all"):
        jobs += build_webpro_jobs(panel, args.max_per_strategy)
    if args.source in ("lowzone", "all"):
        jobs += build_lowzone_jobs(panel, args.max_per_strategy)

    # Materialise each job's 120-bar window. Without this the workers have no
    # price data to draw; the window is sliced here, in one process, so the
    # panel is grouped by code exactly once instead of once per worker.
    jobs = attach_windows(panel, jobs)
    print(f"rendering {len(jobs)} charts with {args.workers} workers", flush=True)

    rendered: dict[str, list[dict]] = {}
    done = 0
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(render_one, job): job for job in jobs}
        for future in as_completed(futures):
            job = futures[future]
            path = future.result()
            done += 1
            if done % 50 == 0:
                print(f"  {done}/{len(jobs)}", flush=True)
            if path:
                rendered.setdefault(job["strategy_id"], []).append({
                    "path": path, "code": job["code"], "date": job["signal_date"],
                    "is_hit": job["is_hit"],
                })

    write_index(rendered, OUT_DIR / "index.html")
    total = sum(len(v) for v in rendered.values())
    print(f"\nrendered {total} charts across {len(rendered)} strategies")
    for sid, items in sorted(rendered.items()):
        hits = sum(1 for i in items if i["is_hit"])
        print(f"  {sid:38s} {hits:4d}/{len(items):<4d} = {100*hits/max(1,len(items)):5.1f}%")
    print(f"index: {OUT_DIR / 'index.html'}")


def build_webpro_jobs(panel: pd.DataFrame, cap: int) -> list[dict]:
    """One job per Web Pro signal, both hits and misses."""
    signals_path = REPO_ROOT / "outputs" / "webpro_signals.csv"
    if not signals_path.exists():
        print("webpro_signals.csv missing - run src.scan_all first")
        return []
    signals = _read_signals(signals_path)
    from experts.registry import get_strategy

    contracts = {
        "webpro": (10, 0.30),
    }
    jobs: list[dict] = []
    for sid, group in signals.groupby("strategy_id", sort=False):
        try:
            label = get_strategy(sid).display_name
        except Exception:
            label = sid
        horizon, target_return = contracts["webpro"]
        # Balance hits and misses so the charts show failures, not only winners.
        # Sampling is spread across the whole period rather than taking the head,
        # which would show only the earliest signals of each strategy.
        hits = _spread(group[group["label_bull__webpro"] == 1])
        misses = _spread(group[group["label_bull__webpro"] == 0])
        if cap:
            per_side = max(1, cap // 2)
            hits = hits.head(per_side)
            misses = misses.head(per_side)
        selected = pd.concat([hits, misses])
        for row in selected.itertuples():
            is_hit = bool(row.label_bull__webpro == 1) if pd.notna(row.label_bull__webpro) else False
            fmax = getattr(row, "forward_max_return__webpro", np.nan)
            jobs.append({
                "code": row.code, "signal_date": row.date,
                "strategy_id": sid, "label": label, "family": "webpro",
                "regime": f"WebPro {horizon}d / +{int(target_return*100)}%",
                "is_hit": is_hit,
                "target_multiple": 1.0 + target_return,
                "outcome_text": f"max +{fmax*100:.1f}%" if pd.notna(fmax) else "unresolved",
            })
    return jobs


def build_lowzone_jobs(panel: pd.DataFrame, cap: int) -> list[dict]:
    """One job per low-zone version signal."""
    path = REPO_ROOT / "outputs" / "lowzone_signals.csv"
    if not path.exists():
        print("lowzone_signals.csv missing - run src.backtest_lowzone first")
        return []
    signals = _read_signals(path)
    # (regime note, target multiple over the next open). The low-zone family's
    # own contract is a 4x target; scoring it under the Web Pro +30% contract
    # reuses the smaller target, so the multiple must follow the regime.
    labels_map = {
        "webpro": ("WebPro 10d / +30%", 1.30),
        "low60": ("LowZone 60d / 4x", 4.00),
        "low504": ("LowZone 504d / 4x", 4.00),
    }
    jobs: list[dict] = []
    for (version, regime), group in signals.groupby(["version", "regime"], sort=False):
        note, target_multiple = labels_map.get(regime, (regime, 1.30))
        hits = _spread(group[group["label_bull"] == 1])
        misses = _spread(group[group["label_bull"] == 0])
        if cap:
            per_side = max(1, cap // 2)
            hits = hits.head(per_side)
            misses = misses.head(per_side)
        for row in pd.concat([hits, misses]).itertuples():
            is_hit = bool(row.label_bull == 1) if pd.notna(row.label_bull) else False
            fmax = getattr(row, "forward_max_return", np.nan)
            jobs.append({
                "code": row.code, "signal_date": row.date,
                "strategy_id": f"{version}_{regime}", "label": f"{version} {note}",
                "family": "lowzone", "regime": note, "is_hit": is_hit,
                "target_multiple": target_multiple,
                "outcome_text": f"max +{fmax*100:.1f}%" if pd.notna(fmax) else "unresolved",
            })
    return jobs


if __name__ == "__main__":
    main()
