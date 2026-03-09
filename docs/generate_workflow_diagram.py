#!/usr/bin/env python3
"""Generate workflow schema diagram for the systematic-review skill."""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

fig, ax = plt.subplots(1, 1, figsize=(16, 22))
ax.set_xlim(0, 16)
ax.set_ylim(0, 22)
ax.axis("off")
fig.patch.set_facecolor("white")

# Colors
C_USER = "#4A90D9"
C_CLAUDE = "#7B68EE"
C_SCRIPT = "#2ECC71"
C_OUTPUT = "#F39C12"
C_DECISION = "#E74C3C"
C_STAGE = "#34495E"
C_ARROW = "#555555"
C_RERUN = "#E74C3C"

def box(x, y, w, h, text, color, fontsize=8, textcolor="white", alpha=0.9, bold=False):
    rect = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.15",
                          facecolor=color, edgecolor="none", alpha=alpha, zorder=2)
    ax.add_patch(rect)
    weight = "bold" if bold else "normal"
    ax.text(x + w/2, y + h/2, text, ha="center", va="center",
            fontsize=fontsize, color=textcolor, weight=weight, zorder=3,
            wrap=True)

def arrow(x1, y1, x2, y2, color=C_ARROW, style="-|>", lw=1.2, ls="-"):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle=style, color=color, lw=lw, ls=ls),
                zorder=1)

def label(x, y, text, fontsize=7, color="#666666", ha="center"):
    ax.text(x, y, text, ha=ha, va="center", fontsize=fontsize, color=color, style="italic", zorder=4)

# ── Title ──
ax.text(8, 21.5, "Systematic Review Skill — Agent Workflow", ha="center", va="center",
        fontsize=16, weight="bold", color=C_STAGE)
ax.text(8, 21.1, "Two-stage autonomous architecture with decision logging", ha="center", va="center",
        fontsize=9, color="#888888")

# ── User Input ──
box(5.5, 20.2, 5, 0.6, "User Query\n\"Do a systematic review on SGLT2i and heart failure\"", C_USER, fontsize=8, bold=True)
arrow(8, 20.2, 8, 19.9)

# ── Stage 1 Banner ──
rect = FancyBboxPatch((1, 8.6), 14, 11.2, boxstyle="round,pad=0.2",
                       facecolor="#F8F9FA", edgecolor=C_STAGE, linewidth=2, alpha=0.5, zorder=0)
ax.add_patch(rect)
ax.text(8, 19.55, "STAGE 1: Autonomous Run (No User Interaction)", ha="center", va="center",
        fontsize=11, weight="bold", color=C_STAGE)

# ── Phase 1 ──
box(1.5, 18.3, 3.5, 0.9, "Phase 1: Topic Refinement\n• PICO(S) definition\n• MeSH terms\n• Search string", C_CLAUDE, fontsize=7)
box(5.5, 18.5, 2.2, 0.5, "decisions_logger\n.log(phase=1)", C_DECISION, fontsize=6.5)
box(8.2, 18.5, 1.8, 0.5, "pico.md", C_OUTPUT, fontsize=7, textcolor="#333333")
arrow(5, 18.75, 5.5, 18.75)
arrow(7.7, 18.75, 8.2, 18.75)
arrow(3.25, 18.3, 3.25, 17.5)

# ── Phase 2 ──
box(1.5, 16.5, 3.5, 0.9, "Phase 2: PubMed Search\n+ PMC Full-Text Fetch", C_CLAUDE, fontsize=7)
box(5.5, 16.9, 2.5, 0.45, "pubmed_search.py", C_SCRIPT, fontsize=7)
box(5.5, 16.35, 2.5, 0.45, "pmc_fulltext.py", C_SCRIPT, fontsize=7)
box(8.5, 16.5, 2.5, 0.45, "pubmed_results.json", C_OUTPUT, fontsize=6.5, textcolor="#333333")
box(8.5, 16.0, 2.0, 0.4, "fulltext_data/", C_OUTPUT, fontsize=6.5, textcolor="#333333")
arrow(5, 17.1, 5.5, 17.1)
arrow(5, 16.6, 5.5, 16.6)
arrow(8, 17.1, 8.5, 16.7)
arrow(8, 16.6, 8.5, 16.2)
box(11.5, 16.65, 2.2, 0.5, "decisions_logger\n.log(phase=2)", C_DECISION, fontsize=6.5)
arrow(11, 16.7, 11.5, 16.9)
arrow(3.25, 16.5, 3.25, 15.7)

# ── Phase 3 ──
box(1.5, 14.7, 3.5, 0.9, "Phase 3: Screening\n• Auto-include/exclude\n• Uncertain → best guess", C_CLAUDE, fontsize=7)
box(5.5, 14.9, 2.7, 0.5, "screening_results.json", C_OUTPUT, fontsize=6.5, textcolor="#333333")
box(8.7, 14.9, 2.2, 0.5, "decisions_logger\n.log(phase=3)", C_DECISION, fontsize=6.5)
arrow(5, 15.15, 5.5, 15.15)
arrow(8.2, 15.15, 8.7, 15.15)
arrow(3.25, 14.7, 3.25, 13.9)

# ── Phase 4 ──
box(1.5, 12.9, 3.5, 0.9, "Phase 4: Data Extraction\n• Effect measure survey\n• Drug stratification", C_CLAUDE, fontsize=7)
box(5.5, 13.3, 2.5, 0.45, "extracted_data.csv", C_OUTPUT, fontsize=6.5, textcolor="#333333")
box(5.5, 12.75, 2.8, 0.45, "study_characteristics.csv", C_OUTPUT, fontsize=6.5, textcolor="#333333")
box(8.7, 13.1, 2.2, 0.5, "decisions_logger\n.log(phase=4)", C_DECISION, fontsize=6.5)
arrow(5, 13.5, 5.5, 13.5)
arrow(5, 13.0, 5.5, 13.0)
arrow(8.3, 13.3, 8.7, 13.35)
arrow(3.25, 12.9, 3.25, 12.1)

# ── Phase 5 ──
box(1.5, 11.1, 3.5, 0.9, "Phase 5: Meta-Analysis\n• Pooling + heterogeneity\n• Sensitivity analyses", C_CLAUDE, fontsize=7)
box(5.5, 11.5, 2.3, 0.45, "meta_analysis.py", C_SCRIPT, fontsize=7)
box(5.5, 10.95, 2.5, 0.45, "generate_figures.py", C_SCRIPT, fontsize=7)
box(8.5, 11.5, 2.2, 0.45, "meta_results.json", C_OUTPUT, fontsize=6.5, textcolor="#333333")
box(8.5, 10.95, 2.2, 0.45, "forest_plot.png\nfunnel_plot.png", C_OUTPUT, fontsize=5.5, textcolor="#333333")
box(11.5, 11.2, 2.2, 0.5, "decisions_logger\n.log(phase=5)", C_DECISION, fontsize=6.5)
arrow(5, 11.55, 5.5, 11.7)
arrow(5, 11.2, 5.5, 11.2)
arrow(7.8, 11.7, 8.5, 11.7)
arrow(8, 11.2, 8.5, 11.2)
arrow(11, 11.5, 11.5, 11.45)
arrow(3.25, 11.1, 3.25, 10.3)

# ── Phase 6 ──
box(1.5, 9.3, 3.5, 0.9, "Phase 6: Report Generation\n• PRISMA report\n• GRADE assessment", C_CLAUDE, fontsize=7)
box(5.5, 9.65, 3.2, 0.45, "generate_review_report.py", C_SCRIPT, fontsize=7)
box(9.2, 9.65, 2.8, 0.45, "draft_review.md", C_OUTPUT, fontsize=7, textcolor="#333333")
box(9.2, 9.1, 2.8, 0.45, "decisions_log.json", C_DECISION, fontsize=7, textcolor="white")
arrow(5, 9.75, 5.5, 9.87)
arrow(8.7, 9.87, 9.2, 9.87)
arrow(5, 9.5, 9.2, 9.32)

# ── Stage 2 Banner ──
rect2 = FancyBboxPatch((1, 1.5), 14, 6.8, boxstyle="round,pad=0.2",
                        facecolor="#FFF5F5", edgecolor=C_RERUN, linewidth=2, alpha=0.4, zorder=0)
ax.add_patch(rect2)
ax.text(8, 8.0, "STAGE 2: User Review & Selective Rerun", ha="center", va="center",
        fontsize=11, weight="bold", color=C_RERUN)

# ── User Review ──
box(3, 6.9, 4.5, 0.7, "User Reviews draft_review.md\n✓ Pre-checked (auto) — skim    ☐ Unchecked — review", C_USER, fontsize=7, bold=True)
arrow(8, 8.8, 8, 7.6)
label(8.3, 8.2, "presents to user", fontsize=7)

# ── Decision Diamond ──
diamond_x, diamond_y = 8, 5.8
diamond_size = 0.6
diamond = plt.Polygon([(diamond_x, diamond_y + diamond_size),
                        (diamond_x + diamond_size*1.5, diamond_y),
                        (diamond_x, diamond_y - diamond_size),
                        (diamond_x - diamond_size*1.5, diamond_y)],
                       facecolor="#F8F9FA", edgecolor=C_STAGE, linewidth=1.5, zorder=2)
ax.add_patch(diamond)
ax.text(diamond_x, diamond_y, "Changes\nmade?", ha="center", va="center", fontsize=7, weight="bold", color=C_STAGE, zorder=3)

arrow(8, 6.9, 8, 6.4)

# ── No Changes Path ──
box(10.5, 5.5, 3, 0.6, "Finalize Report\nsystematic_review_report.md", C_OUTPUT, fontsize=7, textcolor="#333333")
arrow(9.2, 5.8, 10.5, 5.8)
label(9.85, 6.05, "No", fontsize=7, color=C_STAGE)

# ── Changes Path ──
box(2.5, 4.5, 3.5, 0.7, "rerun_from_changes.py\nDetect changed decisions\nDetermine rerun scope", C_SCRIPT, fontsize=7)
arrow(6.8, 5.8, 6, 5.0)
label(5.8, 5.6, "Yes", fontsize=7, color=C_RERUN)

# ── Rerun ──
box(2.5, 3.2, 3.5, 0.9, "Rerun Affected Phases\n(earliest change → Phase 6)\nwith updated decisions", C_CLAUDE, fontsize=7)
arrow(4.25, 4.5, 4.25, 4.1)

# ── Loop back ──
box(2.5, 2.0, 3.5, 0.7, "Regenerate\ndraft_review.md", C_SCRIPT, fontsize=7)
arrow(4.25, 3.2, 4.25, 2.7)
# Arrow going back up to user review
arrow(6, 2.35, 7.5, 2.35)
arrow(7.5, 2.35, 12.5, 2.35)
arrow(12.5, 2.35, 12.5, 7.25)
arrow(12.5, 7.25, 7.5, 7.25)

# ── Legend ──
legend_y = 0.7
legend_items = [
    (C_USER, "User"),
    (C_CLAUDE, "Claude Agent"),
    (C_SCRIPT, "Python Script"),
    (C_OUTPUT, "Output File"),
    (C_DECISION, "Decision Logger"),
]
for i, (color, lbl) in enumerate(legend_items):
    x = 1.5 + i * 2.8
    rect = FancyBboxPatch((x, legend_y), 0.4, 0.3, boxstyle="round,pad=0.05",
                          facecolor=color, edgecolor="none", alpha=0.9, zorder=2)
    ax.add_patch(rect)
    ax.text(x + 0.55, legend_y + 0.15, lbl, fontsize=7, va="center", color="#333333")

plt.tight_layout()
plt.savefig("/Users/cfan/.claude/skills/systematic-review/docs/workflow_diagram.png", dpi=200, bbox_inches="tight",
            facecolor="white", edgecolor="none")
print("Saved to docs/workflow_diagram.png")
