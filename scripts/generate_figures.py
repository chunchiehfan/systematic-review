#!/usr/bin/env python3
"""
Generate meta-analysis figures: forest plot, funnel plot, PRISMA 2020 flow diagram.

Requires: matplotlib, numpy

Usage:
    python generate_figures.py meta_results.json \
        --forest forest_plot.png \
        --funnel funnel_plot.png \
        --prisma prisma_data.json --prisma-out prisma_diagram.png \
        --title "My Review"
"""
import argparse
import json
import math
import sys
from pathlib import Path


def _setup_matplotlib():
    """Import and configure matplotlib for non-interactive (file) output."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import numpy as np
    return plt, mpatches, np


# ---------------------------------------------------------------------------
# Forest plot
# ---------------------------------------------------------------------------

def create_forest_plot(results: dict, output_path: str, title: str = "Forest Plot"):
    """
    Generate a forest plot. Box size is proportional to study weight.
    OR/RR/HR are plotted on a log scale; MD/SMD/PROP on a linear scale.
    """
    plt, mpatches, np = _setup_matplotlib()

    studies = results["studies"]
    pooled = results["pooled"]
    measure = results["measure"]
    hetero = results["heterogeneity"]
    k = len(studies)
    log_scale = measure in ("OR", "RR", "HR")

    # Use raw (log-scale) values for consistent spacing on log axis
    def get_raw(d, key_raw, key_display):
        return d.get(key_raw) if d.get(key_raw) is not None else d[key_display]

    # Figure layout: wide enough for labels + plot + stats column
    fig_height = max(5, k * 0.55 + 3.5)
    fig = plt.figure(figsize=(14, fig_height))

    # Three columns: study labels | forest | stats
    gs = fig.add_gridspec(1, 3, width_ratios=[3, 5, 3], wspace=0.05)
    ax_labels = fig.add_subplot(gs[0])
    ax_plot = fig.add_subplot(gs[1])
    ax_stats = fig.add_subplot(gs[2])

    for ax in [ax_labels, ax_stats]:
        ax.axis("off")

    y_positions = list(range(k, 0, -1))  # top study at highest y
    max_weight = max(s["weight_pct"] for s in studies)

    # --- Forest plot axis ---
    for i, (study, y) in enumerate(zip(studies, y_positions)):
        e_raw = get_raw(study, "_effect_raw", "effect")
        lo_raw = get_raw(study, "_ci_lower_raw", "ci_lower")
        hi_raw = get_raw(study, "_ci_upper_raw", "ci_upper")

        e_disp = study["effect"]
        lo_disp = study["ci_lower"]
        hi_disp = study["ci_upper"]
        w = study["weight_pct"]

        # CI line
        ax_plot.plot([lo_disp, hi_disp], [y, y], "b-", linewidth=1.2, zorder=2, solid_capstyle="butt")

        # Weight square (area proportional to weight)
        box_half = 0.07 + 0.22 * math.sqrt(w / max_weight)
        rect = plt.Rectangle(
            (e_disp - box_half, y - box_half),
            2 * box_half, 2 * box_half,
            color="#003882", zorder=3,
        )
        ax_plot.add_patch(rect)

        # Study label (left panel)
        ax_labels.text(0.95, y, study["study"], ha="right", va="center",
                       fontsize=8.5, transform=ax_labels.get_yaxis_transform())

        # Stats (right panel): effect [lo, hi] weight%
        stats_text = f"{e_disp:.2f} [{lo_disp:.2f}, {hi_disp:.2f}]   {w:.1f}%"
        ax_stats.text(0.05, y, stats_text, ha="left", va="center",
                      fontsize=7.5, transform=ax_stats.get_yaxis_transform(),
                      family="monospace")

    # Pooled diamond
    y_pool = 0
    pe = pooled["effect"]
    pl = pooled["ci_lower"]
    pu = pooled["ci_upper"]
    diamond_h = 0.38
    ax_plot.fill(
        [pl, pe, pu, pe, pl],
        [y_pool, y_pool + diamond_h, y_pool, y_pool - diamond_h, y_pool],
        color="#8B0000", zorder=3,
    )
    ax_labels.text(0.95, y_pool, "Pooled", ha="right", va="center",
                   fontsize=8.5, fontweight="bold",
                   transform=ax_labels.get_yaxis_transform())
    pool_text = f"{pe:.2f} [{pl:.2f}, {pu:.2f}]"
    ax_stats.text(0.05, y_pool, pool_text, ha="left", va="center",
                  fontsize=8, fontweight="bold",
                  transform=ax_stats.get_yaxis_transform(), family="monospace")

    # Null line
    null_val = 1.0 if log_scale else 0.0
    ax_plot.axvline(x=null_val, color="black", linestyle="--", linewidth=0.9, zorder=1)

    # Separator above pooled diamond
    ax_plot.axhline(y=0.6, color="black", linewidth=0.8)

    # Column headers
    ax_labels.text(0.95, k + 0.7, "Study", ha="right", va="center",
                   fontsize=9, fontweight="bold",
                   transform=ax_labels.get_yaxis_transform())
    ax_stats.text(0.05, k + 0.7, f"{measure} [95% CI]         Weight",
                  ha="left", va="center", fontsize=8.5, fontweight="bold",
                  transform=ax_stats.get_yaxis_transform(), family="monospace")

    if log_scale:
        ax_plot.set_xscale("log")

    ax_plot.set_yticks([])
    ax_plot.set_ylim(-0.8, k + 1.2)
    ax_plot.set_xlabel(f"{measure} (95% CI)", fontsize=10)
    for spine in ["top", "right", "left"]:
        ax_plot.spines[spine].set_visible(False)

    # Sync label/stats y-axis limits
    for ax in [ax_labels, ax_stats]:
        ax.set_ylim(-0.8, k + 1.2)

    # Title with heterogeneity stats
    i2 = hetero["I2"]
    tau2 = hetero["tau2"]
    q_p = hetero["Q_pvalue"]
    fig.suptitle(
        f"{title}\n"
        f"I² = {i2:.1f}%,  τ² = {tau2:.4f},  Q-test p = {q_p:.3f}",
        fontsize=11, y=1.01,
    )

    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Forest plot saved to {output_path}")


# ---------------------------------------------------------------------------
# Funnel plot
# ---------------------------------------------------------------------------

def create_funnel_plot(results: dict, output_path: str, title: str = "Funnel Plot"):
    """
    Generate a funnel plot (SE on y-axis, effect on x-axis, inverted).
    Includes 95% pseudo-confidence funnel lines and Egger's test annotation.
    """
    plt, mpatches, np = _setup_matplotlib()

    studies = results["studies"]
    pooled = results["pooled"]
    measure = results["measure"]
    log_scale = measure in ("OR", "RR", "HR")

    # Use raw log values for funnel (so funnel is symmetric on log scale)
    effects_raw = [s.get("_effect_raw") or math.log(s["effect"]) if log_scale else s["effect"]
                   for s in studies]
    ses = [s["_se_raw"] if "_se_raw" in s else s["se"] for s in studies]

    pooled_raw = pooled.get("_effect_raw") or (math.log(pooled["effect"]) if log_scale else pooled["effect"])

    fig, ax = plt.subplots(figsize=(7, 6))

    # Studies scatter
    effects_disp = [math.exp(e) if log_scale else e for e in effects_raw]
    ax.scatter(effects_disp, ses, color="#003882", alpha=0.75, zorder=3, s=50, edgecolors="white", linewidths=0.5)

    # Study labels
    for study, e_disp, se in zip(studies, effects_disp, ses):
        ax.annotate(
            study["study"], xy=(e_disp, se),
            xytext=(4, 0), textcoords="offset points",
            fontsize=6, color="#555555", va="center",
        )

    # Funnel lines: pooled ± 1.96 * SE
    max_se = max(ses) * 1.15 if ses else 1.0
    se_range = np.linspace(0, max_se, 200)
    z = 1.96

    upper_raw = [pooled_raw + z * se for se in se_range]
    lower_raw = [pooled_raw - z * se for se in se_range]

    if log_scale:
        upper_disp = [math.exp(u) for u in upper_raw]
        lower_disp = [math.exp(l) for l in lower_raw]
        pooled_disp = math.exp(pooled_raw)
    else:
        upper_disp = upper_raw
        lower_disp = lower_raw
        pooled_disp = pooled_raw

    ax.plot(upper_disp, se_range, "r--", alpha=0.6, linewidth=1.2, label="95% pseudo-CI")
    ax.plot(lower_disp, se_range, "r--", alpha=0.6, linewidth=1.2)

    # Pooled and null lines
    null_val = 1.0 if log_scale else 0.0
    ax.axvline(x=pooled_disp, color="#888888", linestyle="-", linewidth=1, alpha=0.7, label="Pooled effect")
    ax.axvline(x=null_val, color="black", linestyle="--", linewidth=0.8, alpha=0.6, label="Null")

    ax.invert_yaxis()  # Large studies (small SE) at top
    if log_scale:
        ax.set_xscale("log")

    ax.set_xlabel(f"{measure}", fontsize=10)
    ax.set_ylabel("Standard Error", fontsize=10)
    ax.set_title(title, fontsize=11)
    ax.legend(fontsize=8, loc="lower right")

    # Egger's test annotation
    egger = results.get("publication_bias", {})
    if egger.get("pvalue") is not None:
        ax.text(
            0.02, 0.97,
            f"Egger's test: p = {egger['pvalue']:.3f}",
            transform=ax.transAxes, fontsize=8, va="top",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.7),
        )

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Funnel plot saved to {output_path}")


# ---------------------------------------------------------------------------
# PRISMA 2020 flow diagram
# ---------------------------------------------------------------------------

def create_prisma_diagram(prisma_data: dict, output_path: str):
    """
    Generate a PRISMA 2020 flow diagram with identification, screening,
    eligibility, and inclusion phases.
    """
    plt, mpatches, np = _setup_matplotlib()

    fig, ax = plt.subplots(figsize=(11, 14))
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 14)
    ax.axis("off")

    def box(x, y, w, h, text, fc="lightblue", fontsize=8.5, bold=False):
        rect = mpatches.FancyBboxPatch(
            (x, y), w, h,
            boxstyle="round,pad=0.15",
            facecolor=fc, edgecolor="#333333", linewidth=1.2,
        )
        ax.add_patch(rect)
        ax.text(
            x + w / 2, y + h / 2, text,
            ha="center", va="center", fontsize=fontsize,
            multialignment="center",
            fontweight="bold" if bold else "normal",
            wrap=True,
        )

    def arrow(x1, y1, x2, y2):
        ax.annotate(
            "", xy=(x2, y2), xytext=(x1, y1),
            arrowprops=dict(arrowstyle="-|>", color="#333333", lw=1.5),
        )

    # Data
    identified = prisma_data.get("identified", "?")
    duplicates = prisma_data.get("duplicates_removed", "?")
    screened = prisma_data.get("screened", "?")
    excl_screen = prisma_data.get("excluded_screening", "?")
    full_text = prisma_data.get("full_text_assessed", "?")
    excl_full = prisma_data.get("excluded_full_text", "?")
    included = prisma_data.get("included", "?")
    reasons = prisma_data.get("exclusion_reasons", [])

    reasons_text = "\n".join(
        f"  • {r['reason']}: {r['n']}" for r in reasons[:6]
    )
    excl_full_text = f"Full-text excluded\n(n = {excl_full})\n{reasons_text}" if reasons_text else f"Full-text excluded\n(n = {excl_full})"

    BLUE = "#D0E8F2"
    YELLOW = "#FFF3CD"
    GREEN = "#D4EDDA"
    GRAY = "#E2E3E5"

    # Phase labels (left margin)
    for label, y_center in [
        ("Identification", 11.6),
        ("Screening", 9.6),
        ("Eligibility", 7.6),
        ("Included", 5.3),
    ]:
        ax.text(0.4, y_center, label, ha="center", va="center", fontsize=8.5,
                fontweight="bold", rotation=90, color="#333333",
                bbox=dict(boxstyle="round,pad=0.3", facecolor=GRAY, edgecolor="none"))

    # Title
    ax.text(5.5, 13.6, "PRISMA 2020 Flow Diagram", ha="center", va="center",
            fontsize=14, fontweight="bold")

    # Row 1: Identification
    box(1.0, 11.0, 5.5, 1.2, f"Records identified from PubMed\n(n = {identified})", fc=BLUE)
    box(7.2, 11.0, 3.5, 1.2, f"Duplicates removed\n(n = {duplicates})", fc=YELLOW)
    arrow(3.25 + 2.25, 11.6, 7.2, 11.6)  # -> duplicates

    # Row 2: Screening
    box(1.0, 9.0, 5.5, 1.2, f"Records screened\n(title & abstract)\n(n = {screened})", fc=BLUE)
    box(7.2, 9.0, 3.5, 1.2, f"Records excluded\n(title/abstract)\n(n = {excl_screen})", fc=YELLOW)
    arrow(3.25, 11.0, 3.25, 10.2)   # identified -> screened
    arrow(6.5, 9.6, 7.2, 9.6)       # -> excluded

    # Row 3: Eligibility
    box(1.0, 7.0, 5.5, 1.2, f"Full-text articles assessed\nfor eligibility\n(n = {full_text})", fc=BLUE)
    reasons_h = max(1.2, 0.35 * (len(reasons) + 2))
    box(7.2, 7.0, 3.5, reasons_h, excl_full_text, fc=YELLOW, fontsize=7.5)
    arrow(3.25, 9.0, 3.25, 8.2)     # screened -> full-text
    arrow(6.5, 7.6, 7.2, 7.6)       # -> excluded full text

    # Row 4: Included
    box(1.0, 5.0, 5.5, 1.3, f"Studies included in\nqualitative synthesis\n(n = {included})", fc=GREEN, bold=True)
    box(1.0, 3.2, 5.5, 1.3, f"Studies included in\nmeta-analysis\n(n = {included})", fc=GREEN, bold=True)
    arrow(3.25, 7.0, 3.25, 6.3)     # full-text -> included
    arrow(3.25, 5.0, 3.25, 4.5)     # qualitative -> meta

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"PRISMA diagram saved to {output_path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Generate meta-analysis figures from results JSON.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("results_json", help="meta_results.json from meta_analysis.py")
    parser.add_argument("--forest", help="Output path for forest plot PNG")
    parser.add_argument("--funnel", help="Output path for funnel plot PNG")
    parser.add_argument("--prisma", help="prisma_data.json file")
    parser.add_argument("--prisma-out", help="Output path for PRISMA diagram PNG")
    parser.add_argument("--title", default="Meta-Analysis", help="Title for plots")
    args = parser.parse_args()

    try:
        _setup_matplotlib()
    except ImportError:
        print("Error: matplotlib is required. Install with: pip install matplotlib", file=sys.stderr)
        sys.exit(1)

    results_path = Path(args.results_json)
    if not results_path.exists():
        print(f"Error: {results_path} not found.", file=sys.stderr)
        sys.exit(1)

    with open(results_path) as f:
        results = json.load(f)

    if args.forest:
        create_forest_plot(results, args.forest, title=f"{args.title} — Forest Plot")

    if args.funnel:
        create_funnel_plot(results, args.funnel, title=f"{args.title} — Funnel Plot")

    if args.prisma and args.prisma_out:
        prisma_path = Path(args.prisma)
        if not prisma_path.exists():
            print(f"Error: prisma data file not found: {prisma_path}", file=sys.stderr)
        else:
            with open(prisma_path) as f:
                prisma_data = json.load(f)
            create_prisma_diagram(prisma_data, args.prisma_out)


if __name__ == "__main__":
    main()
