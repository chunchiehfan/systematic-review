#!/usr/bin/env python3
"""Generate a clean workflow diagram for the systematic-review skill."""
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

# ── Layout ──
FIG_W, FIG_H = 22, 36
fig, ax = plt.subplots(1, 1, figsize=(FIG_W, FIG_H))
ax.set_xlim(0, FIG_W)
ax.set_ylim(0, FIG_H)
ax.axis("off")
fig.patch.set_facecolor("white")

# ── Colors (border only, no fills) ──
C_USER   = "#2563EB"
C_AGENT  = "#7C3AED"
C_SCRIPT = "#059669"
C_OUTPUT = "#D97706"
C_LOG    = "#DC2626"
C_TEXT   = "#111827"
C_ARROW  = "#374151"
C_SUBTLE = "#6B7280"
C_S1     = "#475569"
C_S2     = "#B91C1C"

FONT = 14          # base font for all box text
FONT_TITLE = 28
FONT_SECTION = 18
FONT_HEADER = 15
FONT_LABEL = 13
LW_BOX = 2.5
LW_ARROW = 2.5


def box(cx, cy, w, h, text, border_color, fontsize=FONT, bold=False):
    rect = FancyBboxPatch(
        (cx - w/2, cy - h/2), w, h,
        boxstyle="round,pad=0.3",
        facecolor="white", edgecolor=border_color,
        linewidth=LW_BOX, zorder=2,
    )
    ax.add_patch(rect)
    ax.text(cx, cy, text, ha="center", va="center",
            fontsize=fontsize, color=C_TEXT,
            weight="bold" if bold else "normal",
            zorder=3, linespacing=1.5)


def arrow(x1, y1, x2, y2, color=C_ARROW, lw=LW_ARROW):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=color,
                                lw=lw, shrinkA=4, shrinkB=4),
                zorder=5)


# ─────────────────────────────────────────
# TITLE
# ─────────────────────────────────────────
ax.text(FIG_W/2, 35.0, "Systematic Review Skill — Workflow",
        ha="center", fontsize=FONT_TITLE, weight="bold", color=C_TEXT)
ax.text(FIG_W/2, 34.2, "Two-stage autonomous architecture with decision logging",
        ha="center", fontsize=FONT_HEADER, color=C_SUBTLE)

# ─────────────────────────────────────────
# USER INPUT
# ─────────────────────────────────────────
box(FIG_W/2, 33.0, 15, 1.2,
    'User:  "Systematic review on SGLT2i and heart failure"',
    C_USER, fontsize=FONT_HEADER, bold=True)

arrow(FIG_W/2, 32.4, FIG_W/2, 31.8)

# ─────────────────────────────────────────
# STAGE 1 CONTAINER
# ─────────────────────────────────────────
s1_top, s1_bot = 31.5, 12.5
rect = FancyBboxPatch((0.8, s1_bot), FIG_W - 1.6, s1_top - s1_bot,
                       boxstyle="round,pad=0.4", facecolor="#FAFAFA",
                       edgecolor=C_S1, linewidth=3, zorder=0)
ax.add_patch(rect)
ax.text(FIG_W/2, s1_top - 0.6,
        "STAGE 1 :  Autonomous Execution  (no user stops)",
        ha="center", fontsize=FONT_SECTION, weight="bold", color=C_S1)

# Column positions
COL_A = 5.0
COL_S = 11.5
COL_O = 18.0

# Column headers
hdr_y = s1_top - 1.5
for cx, lbl in [(COL_A, "Claude Agent"), (COL_S, "Scripts"), (COL_O, "Outputs")]:
    ax.text(cx, hdr_y, lbl, ha="center", fontsize=FONT_HEADER,
            weight="bold", color=C_SUBTLE)

# Dividers
for lx in [8.25, 14.75]:
    ax.plot([lx, lx], [s1_bot + 0.5, hdr_y - 0.6],
            color="#E5E7EB", lw=1, ls="--", zorder=0)

# ─────────────────────────────────────────
# PHASES
# ─────────────────────────────────────────
BW_A = 6.0
BW_S = 5.0
BW_O = 5.0
BH = 1.6
PHASE_GAP = 2.5

phases = [
    ("Phase 1 — Topic Refinement\nPICO(S), MeSH, search string",
     None,
     "pico.md",
     28.2),
    ("Phase 2 — Literature Search\nPubMed + PMC full text",
     "pubmed_search.py\npmc_fulltext.py",
     "pubmed_results.json\nfulltext_data/",
     25.7),
    ("Phase 3 — Screening\nAuto-include / exclude / uncertain",
     None,
     "screening_results.json\nprisma_data.json",
     23.2),
    ("Phase 4 — Data Extraction\nEffect measures, drug stratification",
     None,
     "extracted_data.csv\nstudy_characteristics.csv",
     20.7),
    ("Phase 5 — Meta-Analysis\nPooling, heterogeneity, sensitivity",
     "meta_analysis.py\ngenerate_figures.py",
     "meta_results.json\nforest_plot.png",
     18.2),
    ("Phase 6 — Report & Review\nPRISMA report, GRADE, decision log",
     "generate_review_report.py",
     "draft_review.md\ndecisions_log.json",
     15.7),
]

for i, (agent_txt, script_txt, output_txt, y) in enumerate(phases):
    # Agent
    box(COL_A, y, BW_A, BH, agent_txt, C_AGENT, fontsize=FONT)

    # Script
    if script_txt:
        box(COL_S, y, BW_S, BH, script_txt, C_SCRIPT, fontsize=FONT)
        arrow(COL_A + BW_A/2, y, COL_S - BW_S/2, y)
        arrow(COL_S + BW_S/2, y, COL_O - BW_O/2, y)
    else:
        arrow(COL_A + BW_A/2, y, COL_O - BW_O/2, y)

    # Output
    box(COL_O, y, BW_O, BH, output_txt, C_OUTPUT, fontsize=FONT)

    # Decision log dot
    ax.text(COL_A + BW_A/2 + 0.25, y + BH/2 + 0.1, "●",
            fontsize=13, color=C_LOG, ha="left", va="center", zorder=4)

    # Down arrow to next phase
    if i < len(phases) - 1:
        next_y = phases[i + 1][3]
        arrow(COL_A, y - BH/2, COL_A, next_y + BH/2, color=C_AGENT)

# Log legend
ax.text(COL_A + BW_A/2 + 0.7, 28.2 + BH/2 + 0.1,
        "= decision logged", fontsize=FONT_LABEL, color=C_LOG,
        ha="left", va="center", style="italic")

# ─────────────────────────────────────────
# TRANSITION
# ─────────────────────────────────────────
arrow(FIG_W/2, s1_bot, FIG_W/2, 11.8, color=C_ARROW)
ax.text(FIG_W/2 + 0.5, 12.15, "presents draft_review.md to user",
        fontsize=FONT_LABEL, color=C_SUBTLE, ha="left", style="italic")

# ─────────────────────────────────────────
# STAGE 2 CONTAINER
# ─────────────────────────────────────────
s2_top, s2_bot = 11.5, 1.2
rect2 = FancyBboxPatch((0.8, s2_bot), FIG_W - 1.6, s2_top - s2_bot,
                        boxstyle="round,pad=0.4", facecolor="#FFFBFB",
                        edgecolor=C_S2, linewidth=3, zorder=0)
ax.add_patch(rect2)
ax.text(FIG_W/2, s2_top - 0.6,
        "STAGE 2 :  User Review & Selective Rerun",
        ha="center", fontsize=FONT_SECTION, weight="bold", color=C_S2)

# User review
box(FIG_W/2, 9.3, 16, 1.4,
    "User reviews draft_review.md\n"
    "✓ Confident     ☐ Needs review     ✎ Override via \"Change to\"",
    C_USER, fontsize=FONT, bold=True)

arrow(FIG_W/2, 8.6, FIG_W/2, 7.6)

# Diamond
dx, dy, ds = FIG_W/2, 6.8, 0.9
diamond = plt.Polygon([(dx, dy + ds), (dx + ds*1.5, dy),
                        (dx, dy - ds), (dx - ds*1.5, dy)],
                       facecolor="white", edgecolor=C_S1,
                       linewidth=LW_BOX, zorder=2)
ax.add_patch(diamond)
ax.text(dx, dy, "Changes?", ha="center", va="center",
        fontsize=FONT, weight="bold", color=C_TEXT, zorder=3)

# No → Finalize
box(17.5, dy, 5.0, 1.1, "Finalize Report ✓",
    C_OUTPUT, fontsize=FONT, bold=True)
arrow(dx + ds*1.5, dy, 17.5 - 2.5, dy)
ax.text(dx + ds*1.5 + 0.4, dy + 0.5, "No",
        fontsize=FONT, weight="bold", color=C_S1)

# Yes → Rerun
box(5.5, 4.5, 6.5, 1.3,
    "rerun_from_changes.py\nDetermine rerun scope",
    C_SCRIPT, fontsize=FONT)
arrow(dx - ds*1.5, dy, 5.5 + 3.25, dy, color=C_S2)
arrow(5.5, dy - ds, 5.5, 4.5 + 0.65, color=C_S2)
ax.text(dx - ds*1.5 - 0.4, dy + 0.5, "Yes",
        fontsize=FONT, weight="bold", color=C_S2, ha="right")

# Rerun box
box(FIG_W/2, 2.5, 12, 1.1,
    "Rerun affected phases → Regenerate draft_review.md",
    C_AGENT, fontsize=FONT, bold=True)
arrow(5.5 + 3.25, 3.85, FIG_W/2 - 6, 3.05, color=C_S2)

# Loop back
loop_x = 19.5
ax.plot([FIG_W/2 + 6, loop_x], [2.5, 2.5], color=C_S2, lw=2, zorder=1)
ax.plot([loop_x, loop_x], [2.5, 9.3], color=C_S2, lw=2, zorder=1)
arrow(loop_x, 9.3, FIG_W/2 + 8, 9.3, color=C_S2)
ax.text(loop_x + 0.5, 5.9, "loop", fontsize=FONT_LABEL, color=C_S2,
        rotation=90, ha="center", va="center", style="italic")

# ─────────────────────────────────────────
# LEGEND
# ─────────────────────────────────────────
ly = 0.4
items = [
    (C_USER, "User"),
    (C_AGENT, "Claude Agent"),
    (C_SCRIPT, "Python Script"),
    (C_OUTPUT, "Output File"),
    (C_LOG, "● Decision Logged"),
]
start_x = 1.5
for i, (color, lbl) in enumerate(items):
    x = start_x + i * 4.2
    if "●" in lbl:
        ax.text(x, ly, "●", fontsize=16, color=color,
                ha="center", va="center")
        ax.text(x + 0.5, ly, "Decision Logged",
                fontsize=FONT_LABEL, color=C_TEXT, va="center")
    else:
        r = FancyBboxPatch((x - 0.45, ly - 0.25), 0.9, 0.5,
                           boxstyle="round,pad=0.08", facecolor="white",
                           edgecolor=color, linewidth=LW_BOX, zorder=2)
        ax.add_patch(r)
        ax.text(x + 0.75, ly, lbl, fontsize=FONT_LABEL,
                color=C_TEXT, va="center")

plt.tight_layout(pad=0.5)
plt.savefig("/Users/cfan/.claude/skills/systematic-review/docs/workflow_diagram.png",
            dpi=150, bbox_inches="tight", facecolor="white", edgecolor="none")
print("Saved to docs/workflow_diagram.png")
