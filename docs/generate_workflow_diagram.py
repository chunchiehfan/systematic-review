#!/usr/bin/env python3
"""Generate a clean workflow diagram for the systematic-review skill."""
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

# ── Layout ──
FIG_W, FIG_H = 20, 30
fig, ax = plt.subplots(1, 1, figsize=(FIG_W, FIG_H))
ax.set_xlim(0, FIG_W)
ax.set_ylim(0, FIG_H)
ax.axis("off")
fig.patch.set_facecolor("white")

# ── Colors (border only) ──
C_USER    = "#2563EB"
C_AGENT   = "#7C3AED"
C_SCRIPT  = "#059669"
C_OUTPUT  = "#D97706"
C_LOG     = "#DC2626"
C_TEXT    = "#111827"
C_ARROW   = "#374151"
C_SUBTLE  = "#6B7280"
C_STAGE1  = "#475569"
C_STAGE2  = "#B91C1C"


def box(cx, cy, w, h, text, border_color, fontsize=12, bold=False, fill=False):
    """Draw a box with border only (no fill), black text."""
    fc = "white" if not fill else border_color + "15"
    rect = FancyBboxPatch(
        (cx - w/2, cy - h/2), w, h,
        boxstyle="round,pad=0.25",
        facecolor=fc, edgecolor=border_color,
        linewidth=2.5, zorder=2,
    )
    ax.add_patch(rect)
    weight = "bold" if bold else "normal"
    ax.text(cx, cy, text, ha="center", va="center",
            fontsize=fontsize, color=C_TEXT, weight=weight,
            zorder=3, linespacing=1.5)


def arrow(x1, y1, x2, y2, color=C_ARROW, lw=2):
    """Draw a clean arrow."""
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=color,
                                lw=lw, shrinkA=2, shrinkB=2),
                zorder=5)


def side_label(x, y, text, fontsize=10, color=C_SUBTLE):
    ax.text(x, y, text, ha="center", va="center",
            fontsize=fontsize, color=color, style="italic")


# ═══════════════════════════════════════════
# TITLE
# ═══════════════════════════════════════════
ax.text(FIG_W/2, 29.2, "Systematic Review Skill — Workflow",
        ha="center", fontsize=24, weight="bold", color=C_TEXT)
ax.text(FIG_W/2, 28.5, "Two-stage autonomous architecture with decision logging",
        ha="center", fontsize=14, color=C_SUBTLE)

# ═══════════════════════════════════════════
# USER INPUT
# ═══════════════════════════════════════════
box(FIG_W/2, 27.3, 14, 1.0,
    'User:  "Systematic review on SGLT2i\nand heart failure"',
    C_USER, fontsize=14, bold=True)

arrow(FIG_W/2, 26.8, FIG_W/2, 26.2)

# ═══════════════════════════════════════════
# STAGE 1
# ═══════════════════════════════════════════
s1_top, s1_bot = 26.0, 10.8
rect = FancyBboxPatch((0.8, s1_bot), FIG_W - 1.6, s1_top - s1_bot,
                       boxstyle="round,pad=0.4", facecolor="#F8FAFC",
                       edgecolor=C_STAGE1, linewidth=3, zorder=0)
ax.add_patch(rect)
ax.text(FIG_W/2, s1_top - 0.5,
        "STAGE 1 :  Autonomous Execution  (no user stops)",
        ha="center", fontsize=16, weight="bold", color=C_STAGE1)

# Column headers
hdr_y = s1_top - 1.3
COL_A, COL_S, COL_O = 4.5, 10.0, 16.0
for cx, lbl in [(COL_A, "Claude Agent"), (COL_S, "Scripts"), (COL_O, "Outputs")]:
    ax.text(cx, hdr_y, lbl, ha="center", fontsize=13,
            weight="bold", color=C_SUBTLE)

# Divider lines
for lx in [7.25, 13.0]:
    ax.plot([lx, lx], [s1_bot + 0.5, hdr_y - 0.5],
            color="#D1D5DB", lw=1, ls="--", zorder=0)

# ── Phases ──
phases = [
    ("Phase 1 — Topic Refinement\nPICO(S), MeSH terms, search string",
     None, "pico.md", 23.3),
    ("Phase 2 — Literature Search\nPubMed + PMC full text",
     "pubmed_search.py\npmc_fulltext.py", "pubmed_results.json\nfulltext_data/", 21.5),
    ("Phase 3 — Screening\nAuto-include / exclude / uncertain",
     None, "screening_results.json\nprisma_data.json", 19.7),
    ("Phase 4 — Data Extraction\nEffect measures, drug stratification",
     None, "extracted_data.csv\nstudy_characteristics.csv", 17.9),
    ("Phase 5 — Meta-Analysis\nPooling, heterogeneity, sensitivity",
     "meta_analysis.py\ngenerate_figures.py", "meta_results.json\nforest_plot.png", 16.1),
    ("Phase 6 — Report & Review\nPRISMA report, GRADE, decision log",
     "generate_review_report.py", "draft_review.md\ndecisions_log.json", 14.3),
]

BW_A, BW_S, BW_O = 5.5, 4.0, 4.5
BH = 1.3

for i, (agent_text, script_text, output_text, y) in enumerate(phases):
    # Agent box
    box(COL_A, y, BW_A, BH, agent_text, C_AGENT, fontsize=11)

    # Script box
    if script_text:
        box(COL_S, y, BW_S, BH, script_text, C_SCRIPT, fontsize=11)
        arrow(COL_A + BW_A/2 + 0.1, y, COL_S - BW_S/2 - 0.1, y)
        arrow(COL_S + BW_S/2 + 0.1, y, COL_O - BW_O/2 - 0.1, y)
    else:
        arrow(COL_A + BW_A/2 + 0.1, y, COL_O - BW_O/2 - 0.1, y)

    # Output box
    box(COL_O, y, BW_O, BH, output_text, C_OUTPUT, fontsize=11)

    # Decision log marker
    ax.text(COL_A + BW_A/2 + 0.3, y + BH/2 + 0.05, "●",
            fontsize=10, color=C_LOG, ha="left", va="center", zorder=4)

    # Vertical arrow to next phase
    if i < len(phases) - 1:
        next_y = phases[i + 1][3]
        arrow(COL_A, y - BH/2 - 0.05, COL_A, next_y + BH/2 + 0.05,
              color=C_AGENT, lw=2.5)

# Log legend note
ax.text(COL_A + BW_A/2 + 0.7, 23.3 + BH/2 + 0.05,
        "= decision logged", fontsize=11, color=C_LOG,
        ha="left", va="center", style="italic")

# ═══════════════════════════════════════════
# Transition arrow
# ═══════════════════════════════════════════
arrow(FIG_W/2, s1_bot - 0.05, FIG_W/2, 10.0, color=C_ARROW, lw=2.5)
side_label(FIG_W/2 + 2, 10.4, "presents draft_review.md to user", fontsize=11)

# ═══════════════════════════════════════════
# STAGE 2
# ═══════════════════════════════════════════
s2_top, s2_bot = 9.8, 1.0
rect2 = FancyBboxPatch((0.8, s2_bot), FIG_W - 1.6, s2_top - s2_bot,
                        boxstyle="round,pad=0.4", facecolor="#FEF2F2",
                        edgecolor=C_STAGE2, linewidth=3, zorder=0)
ax.add_patch(rect2)
ax.text(FIG_W/2, s2_top - 0.5,
        "STAGE 2 :  User Review & Selective Rerun",
        ha="center", fontsize=16, weight="bold", color=C_STAGE2)

# User review box
box(FIG_W/2, 8.0, 14, 1.2,
    "User reviews draft_review.md\n"
    "✓ Pre-checked = confident     ☐ Unchecked = needs review     ✎ Override",
    C_USER, fontsize=13, bold=True)

arrow(FIG_W/2, 7.4, FIG_W/2, 6.6)

# Decision diamond
dx, dy, ds = FIG_W/2, 5.8, 0.8
diamond = plt.Polygon([(dx, dy + ds), (dx + ds*1.5, dy),
                        (dx, dy - ds), (dx - ds*1.5, dy)],
                       facecolor="white", edgecolor=C_STAGE1,
                       linewidth=2.5, zorder=2)
ax.add_patch(diamond)
ax.text(dx, dy, "Changes?", ha="center", va="center",
        fontsize=13, weight="bold", color=C_TEXT, zorder=3)

# No → Finalize
box(15.5, dy, 4.0, 0.9, "Finalize Report ✓", C_OUTPUT, fontsize=13, bold=True)
arrow(dx + ds*1.5 + 0.1, dy, 15.5 - 2.0 - 0.1, dy, lw=2.5)
ax.text(dx + ds*1.5 + 0.5, dy + 0.4, "No", fontsize=12,
        weight="bold", color=C_STAGE1)

# Yes → Rerun
box(5.0, 3.8, 5.5, 1.0,
    "rerun_from_changes.py\nDetermine rerun scope",
    C_SCRIPT, fontsize=12)
arrow(dx - ds*1.5 - 0.1, dy, 5.0 + 2.75 + 0.1, dy, color=C_STAGE2, lw=2.5)
arrow(5.0, dy - ds, 5.0, 3.8 + 0.5 + 0.05, color=C_STAGE2, lw=2.5)
ax.text(dx - ds*1.5 - 0.5, dy + 0.4, "Yes", fontsize=12,
        weight="bold", color=C_STAGE2, ha="right")

# Rerun phases
box(FIG_W/2, 2.2, 10, 0.9,
    "Rerun affected phases → Regenerate draft_review.md",
    C_AGENT, fontsize=13, bold=True)
arrow(5.0 + 2.75, 3.3, FIG_W/2 - 5.0, 2.65, color=C_STAGE2, lw=2.5)

# Loop back arrow (right side)
loop_x = 17.5
ax.plot([FIG_W/2 + 5.0, loop_x], [2.2, 2.2],
        color=C_STAGE2, lw=2, zorder=1)
ax.plot([loop_x, loop_x], [2.2, 8.0],
        color=C_STAGE2, lw=2, zorder=1)
arrow(loop_x, 8.0, FIG_W/2 + 7.0 + 0.1, 8.0, color=C_STAGE2, lw=2.5)
ax.text(loop_x + 0.4, 5.1, "loop", fontsize=11, color=C_STAGE2,
        rotation=90, ha="center", va="center", style="italic")


# ═══════════════════════════════════════════
# LEGEND
# ═══════════════════════════════════════════
ly = 0.3
items = [
    (C_USER, "User"), (C_AGENT, "Claude Agent"), (C_SCRIPT, "Python Script"),
    (C_OUTPUT, "Output File"), (C_LOG, "● Decision Logged"),
]
start_x = 1.5
for i, (color, lbl) in enumerate(items):
    x = start_x + i * 3.6
    if "●" in lbl:
        ax.text(x, ly, "●", fontsize=14, color=color, ha="center", va="center")
        ax.text(x + 0.5, ly, "Decision Logged", fontsize=11, color=C_TEXT, va="center")
    else:
        r = FancyBboxPatch((x - 0.4, ly - 0.22), 0.8, 0.44,
                           boxstyle="round,pad=0.08", facecolor="white",
                           edgecolor=color, linewidth=2.5, zorder=2)
        ax.add_patch(r)
        ax.text(x + 0.7, ly, lbl, fontsize=11, color=C_TEXT, va="center")

plt.tight_layout(pad=0.5)
plt.savefig("/Users/cfan/.claude/skills/systematic-review/docs/workflow_diagram.png",
            dpi=180, bbox_inches="tight", facecolor="white", edgecolor="none")
print("Saved to docs/workflow_diagram.png")
