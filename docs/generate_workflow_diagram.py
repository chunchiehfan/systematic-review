#!/usr/bin/env python3
"""Generate a clean workflow diagram for the systematic-review skill."""
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import matplotlib.patheffects as pe

# ── Layout constants ──
FIG_W, FIG_H = 18, 28
COL_AGENT = 3.5      # center x for Agent column
COL_SCRIPT = 9.5     # center x for Scripts column
COL_OUTPUT = 15.0    # center x for Outputs column

# ── Colors ──
C = {
    "user":     "#3B82F6",
    "agent":    "#8B5CF6",
    "script":   "#10B981",
    "output":   "#F59E0B",
    "decision": "#EF4444",
    "bg_s1":    "#F1F5F9",
    "bg_s2":    "#FEF2F2",
    "border_s1":"#64748B",
    "border_s2":"#DC2626",
    "text":     "#1E293B",
    "subtle":   "#94A3B8",
    "white":    "#FFFFFF",
    "arrow":    "#64748B",
}

fig, ax = plt.subplots(1, 1, figsize=(FIG_W, FIG_H))
ax.set_xlim(0, FIG_W)
ax.set_ylim(0, FIG_H)
ax.axis("off")
fig.patch.set_facecolor("white")


def rounded_box(x, y, w, h, text, color, fontsize=10, textcolor="white",
                alpha=0.95, bold=False, border=None, border_width=1.5):
    """Draw a rounded rectangle with centered text."""
    ec = border if border else "none"
    rect = FancyBboxPatch((x - w/2, y - h/2), w, h,
                          boxstyle="round,pad=0.2", facecolor=color,
                          edgecolor=ec, linewidth=border_width,
                          alpha=alpha, zorder=2)
    ax.add_patch(rect)
    weight = "bold" if bold else "normal"
    ax.text(x, y, text, ha="center", va="center", fontsize=fontsize,
            color=textcolor, weight=weight, zorder=3,
            linespacing=1.4)


def draw_arrow(x1, y1, x2, y2, color=C["arrow"], lw=1.5, style="-|>"):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle=style, color=color, lw=lw),
                zorder=1)


def draw_arrow_curved(x1, y1, x2, y2, color=C["arrow"], lw=1.5,
                      connectionstyle="arc3,rad=0.15"):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=color, lw=lw,
                                connectionstyle=connectionstyle),
                zorder=1)


# ═══════════════════════════════════════════
# TITLE
# ═══════════════════════════════════════════
ax.text(FIG_W/2, 27.3, "Systematic Review Skill", ha="center", va="center",
        fontsize=22, weight="bold", color=C["text"])
ax.text(FIG_W/2, 26.7, "Two-Stage Autonomous Workflow with Decision Logging",
        ha="center", va="center", fontsize=13, color=C["subtle"])

# ═══════════════════════════════════════════
# USER INPUT
# ═══════════════════════════════════════════
rounded_box(FIG_W/2, 25.8, 10, 0.9,
            'User:  "Systematic review on SGLT2i and heart failure"',
            C["user"], fontsize=12, bold=True)


# ═══════════════════════════════════════════
# STAGE 1 CONTAINER
# ═══════════════════════════════════════════
s1_top, s1_bot = 24.8, 10.2
s1_rect = FancyBboxPatch((0.5, s1_bot), FIG_W - 1, s1_top - s1_bot,
                          boxstyle="round,pad=0.3", facecolor=C["bg_s1"],
                          edgecolor=C["border_s1"], linewidth=2.5,
                          alpha=0.4, zorder=0)
ax.add_patch(s1_rect)
ax.text(FIG_W/2, s1_top - 0.4,
        "STAGE 1 :  Autonomous Execution  (no user interaction)",
        ha="center", va="center", fontsize=14, weight="bold",
        color=C["border_s1"])

# Column headers
header_y = s1_top - 1.1
for cx, label in [(COL_AGENT, "Claude Agent"),
                  (COL_SCRIPT, "Python Scripts"),
                  (COL_OUTPUT, "Outputs")]:
    ax.text(cx, header_y, label, ha="center", va="center",
            fontsize=12, weight="bold", color=C["subtle"],
            path_effects=[pe.withStroke(linewidth=3, foreground="white")])

# Vertical lane dividers
for lx in [6.5, 12.25]:
    ax.plot([lx, lx], [s1_bot + 0.3, header_y - 0.4],
            color="#E2E8F0", lw=1, ls="--", zorder=0)

# ═══════════════════════════════════════════
# PHASE ROWS
# ═══════════════════════════════════════════
phases = [
    {
        "y": 22.6,
        "label": "Phase 1\nTopic Refinement",
        "detail": "PICO(S) + MeSH terms\n+ search string",
        "scripts": None,
        "outputs": "pico.md",
        "log": True,
    },
    {
        "y": 20.8,
        "label": "Phase 2\nLiterature Search",
        "detail": "PubMed search\n+ PMC full text",
        "scripts": "pubmed_search.py\npmc_fulltext.py",
        "outputs": "pubmed_results.json\nfulltext_data/",
        "log": True,
    },
    {
        "y": 19.0,
        "label": "Phase 3\nScreening",
        "detail": "Confidence tiers:\nauto-include / exclude / uncertain",
        "scripts": None,
        "outputs": "screening_results.json\nprisma_data.json",
        "log": True,
    },
    {
        "y": 17.2,
        "label": "Phase 4\nData Extraction",
        "detail": "Effect measure survey\n+ drug stratification",
        "scripts": None,
        "outputs": "extracted_data.csv\nstudy_characteristics.csv",
        "log": True,
    },
    {
        "y": 15.4,
        "label": "Phase 5\nMeta-Analysis",
        "detail": "Pooling, heterogeneity\n+ sensitivity analyses",
        "scripts": "meta_analysis.py\ngenerate_figures.py",
        "outputs": "meta_results.json\nforest_plot.png\nfunnel_plot.png",
        "log": True,
    },
    {
        "y": 13.4,
        "label": "Phase 6\nReport & Review",
        "detail": "PRISMA report\n+ GRADE + decision review",
        "scripts": "generate_review_report.py",
        "outputs": "draft_review.md\ndecisions_log.json",
        "log": True,
    },
]

BOX_W_AGENT = 4.8
BOX_W_SCRIPT = 4.2
BOX_W_OUTPUT = 4.2
BOX_H = 1.3

for i, p in enumerate(phases):
    y = p["y"]

    # Agent box
    rounded_box(COL_AGENT, y, BOX_W_AGENT, BOX_H,
                f"{p['label']}\n{p['detail']}", C["agent"],
                fontsize=9.5, bold=False)

    # Script box (if any)
    if p["scripts"]:
        rounded_box(COL_SCRIPT, y, BOX_W_SCRIPT, BOX_H,
                    p["scripts"], C["script"], fontsize=10)
        draw_arrow(COL_AGENT + BOX_W_AGENT/2, y,
                   COL_SCRIPT - BOX_W_SCRIPT/2, y)

    # Output box
    rounded_box(COL_OUTPUT, y, BOX_W_OUTPUT, BOX_H,
                p["outputs"], C["output"], fontsize=10, textcolor="#333333")
    if p["scripts"]:
        draw_arrow(COL_SCRIPT + BOX_W_SCRIPT/2, y,
                   COL_OUTPUT - BOX_W_OUTPUT/2, y)
    else:
        draw_arrow(COL_AGENT + BOX_W_AGENT/2, y,
                   COL_OUTPUT - BOX_W_OUTPUT/2, y)

    # Decision logger indicator
    if p["log"]:
        ax.text(COL_AGENT + BOX_W_AGENT/2 + 0.15, y + BOX_H/2 - 0.15, "●",
                fontsize=8, color=C["decision"], ha="left", va="top", zorder=4)

    # Vertical arrow to next phase
    if i < len(phases) - 1:
        next_y = phases[i + 1]["y"]
        draw_arrow(COL_AGENT, y - BOX_H/2,
                   COL_AGENT, next_y + BOX_H/2,
                   color=C["agent"], lw=2)

# Decision logger side note
ax.text(COL_AGENT + BOX_W_AGENT/2 + 0.6, 22.6 + BOX_H/2 - 0.15,
        "● = decision logged", fontsize=9, color=C["decision"],
        ha="left", va="top", style="italic")

# Arrow from user to Phase 1
draw_arrow(FIG_W/2, 25.35, COL_AGENT, 22.6 + BOX_H/2,
           color=C["user"], lw=2)


# ═══════════════════════════════════════════
# STAGE 2 CONTAINER
# ═══════════════════════════════════════════
s2_top, s2_bot = 9.6, 1.8
s2_rect = FancyBboxPatch((0.5, s2_bot), FIG_W - 1, s2_top - s2_bot,
                          boxstyle="round,pad=0.3", facecolor=C["bg_s2"],
                          edgecolor=C["border_s2"], linewidth=2.5,
                          alpha=0.3, zorder=0)
ax.add_patch(s2_rect)
ax.text(FIG_W/2, s2_top - 0.4,
        "STAGE 2 :  User Review & Selective Rerun",
        ha="center", va="center", fontsize=14, weight="bold",
        color=C["border_s2"])

# Arrow from Stage 1 to Stage 2
draw_arrow(FIG_W/2, s1_bot - 0.05, FIG_W/2, s2_top + 0.05,
           color=C["arrow"], lw=2)
ax.text(FIG_W/2 + 0.3, (s1_bot + s2_top) / 2,
        "presents draft_review.md", fontsize=10, color=C["subtle"],
        ha="left", va="center", style="italic")

# ── User Review ──
user_review_y = 8.0
rounded_box(FIG_W/2, user_review_y, 12, 1.0,
            "User Reviews draft_review.md\n"
            "✓ Pre-checked = confident decisions      "
            "☐ Unchecked = needs attention      "
            "✎ Override via \"Change to\" fields",
            C["user"], fontsize=10.5, bold=True)

# ── Decision diamond ──
diamond_y = 6.3
diamond_x = FIG_W / 2
ds = 0.7
diamond = plt.Polygon([(diamond_x, diamond_y + ds),
                        (diamond_x + ds * 1.5, diamond_y),
                        (diamond_x, diamond_y - ds),
                        (diamond_x - ds * 1.5, diamond_y)],
                       facecolor="white", edgecolor=C["border_s1"],
                       linewidth=2, zorder=2)
ax.add_patch(diamond)
ax.text(diamond_x, diamond_y, "Changes\nmade?", ha="center", va="center",
        fontsize=10, weight="bold", color=C["text"], zorder=3)

draw_arrow(diamond_x, user_review_y - 0.5, diamond_x, diamond_y + ds,
           color=C["arrow"], lw=2)

# ── No path → Finalize ──
finalize_x = 14
rounded_box(finalize_x, diamond_y, 4.5, 0.9,
            "Finalize Report ✓", C["output"],
            fontsize=12, textcolor="#333333", bold=True)
draw_arrow(diamond_x + ds * 1.5, diamond_y, finalize_x - 2.25, diamond_y,
           color=C["arrow"], lw=2)
ax.text(diamond_x + ds * 1.5 + 0.3, diamond_y + 0.3, "No changes",
        fontsize=10, color=C["border_s1"], weight="bold")

# ── Yes path → Rerun ──
rerun_x = 5
rerun_y = 4.2
rounded_box(rerun_x, rerun_y, 5.5, 1.2,
            "rerun_from_changes.py\nDetect changes → rerun scope",
            C["script"], fontsize=10.5)
draw_arrow(diamond_x - ds * 1.5, diamond_y, rerun_x + 2.75, diamond_y,
           color=C["border_s2"], lw=2)
draw_arrow(rerun_x, diamond_y - ds, rerun_x, rerun_y + 0.6,
           color=C["border_s2"], lw=2)
ax.text(diamond_x - ds * 1.5 - 0.3, diamond_y + 0.3, "Yes",
        fontsize=10, color=C["border_s2"], weight="bold", ha="right")

# ── Rerun phases ──
rerun2_y = 2.7
rounded_box(FIG_W/2, rerun2_y, 8, 1.0,
            "Rerun affected phases (earliest change → Phase 6)  →  Regenerate draft_review.md",
            C["agent"], fontsize=10.5, bold=True)
draw_arrow(rerun_x + 2.75, rerun_y, FIG_W/2 - 4, rerun2_y + 0.5,
           color=C["border_s2"], lw=2)

# Loop arrow back up to user review
ax.annotate("", xy=(FIG_W - 1.5, user_review_y), xytext=(FIG_W - 1.5, rerun2_y),
            arrowprops=dict(arrowstyle="-|>", color=C["border_s2"], lw=2,
                            connectionstyle="arc3,rad=0"),
            zorder=1)
draw_arrow(FIG_W/2 + 4, rerun2_y, FIG_W - 1.5, rerun2_y,
           color=C["border_s2"], lw=2, style="-")
draw_arrow(FIG_W - 1.5, user_review_y, FIG_W/2 + 6, user_review_y,
           color=C["border_s2"], lw=2)
ax.text(FIG_W - 1.1, (user_review_y + rerun2_y) / 2, "loop",
        fontsize=9, color=C["border_s2"], rotation=90, ha="center",
        va="center", style="italic")


# ═══════════════════════════════════════════
# LEGEND
# ═══════════════════════════════════════════
legend_y = 0.8
legend_items = [
    (C["user"], "User"),
    (C["agent"], "Claude Agent"),
    (C["script"], "Python Script"),
    (C["output"], "Output File"),
    (C["decision"], "● Decision Logged"),
]
total_w = len(legend_items) * 3.2
start_x = (FIG_W - total_w) / 2 + 0.5
for i, (color, lbl) in enumerate(legend_items):
    x = start_x + i * 3.2
    if "●" in lbl:
        ax.text(x, legend_y, "●", fontsize=14, color=color, ha="center",
                va="center", weight="bold")
        ax.text(x + 0.4, legend_y, lbl.replace("● ", ""), fontsize=10,
                va="center", color=C["text"])
    else:
        rect = FancyBboxPatch((x - 0.3, legend_y - 0.2), 0.6, 0.4,
                              boxstyle="round,pad=0.05", facecolor=color,
                              edgecolor="none", alpha=0.9, zorder=2)
        ax.add_patch(rect)
        ax.text(x + 0.5, legend_y, lbl, fontsize=10, va="center",
                color=C["text"])

plt.tight_layout(pad=0.5)
plt.savefig("/Users/cfan/.claude/skills/systematic-review/docs/workflow_diagram.png",
            dpi=180, bbox_inches="tight", facecolor="white", edgecolor="none")
print("Saved to docs/workflow_diagram.png")
