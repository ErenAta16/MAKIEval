"""Generate result figures for the MAKIEval reproducibility audit.

Numbers are taken verbatim from docs/DATA_QUALITY_REPORT.md (sample=200, seed=42)
and the paper's Table 10. Re-run after regenerating the report to refresh figures.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

# Neutral, print-friendly palette
C_AUDIT = "#2F6DB5"   # this audit (cultural-only)
C_PAPER = "#B5852F"   # paper Table 10
C_ALL = "#9AA7B4"     # all-types (context)
GRID = "#D9DEE3"
plt.rcParams.update({
    "font.size": 11,
    "axes.edgecolor": "#444",
    "axes.linewidth": 0.8,
    "figure.dpi": 150,
})

def style(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_axisbelow(True)


# ---------------------------------------------------------------------------
# Figure 1: Missing-QID rate by topic — cultural-only audit vs paper Table 10
# ---------------------------------------------------------------------------
topics = ["Beverage", "Transportation", "Music", "Book", "Food", "Clothing"]
audit_cultural = [34.15, 28.00, 43.39, 43.76, 44.84, 56.82]   # this audit, cultural-only
paper_t10 =      [30.59, 25.98, 31.11, 33.25, 32.18, 35.92]   # paper Table 10
all_types =      [63.12, 60.26, 70.34, 71.26, 61.68, 63.45]   # all entity types (context)

x = range(len(topics))
w = 0.38
fig, ax = plt.subplots(figsize=(9, 4.6))
b1 = ax.bar([i - w/2 for i in x], audit_cultural, w, label="This audit (cultural entities only)", color=C_AUDIT)
b2 = ax.bar([i + w/2 for i in x], paper_t10, w, label="Paper, Table 10", color=C_PAPER)
# all-types as light reference markers
ax.scatter(list(x), all_types, marker="_", s=420, color=C_ALL, linewidths=2.4,
           label="All entity types (incl. names/places)", zorder=5)
for rects in (b1, b2):
    for r in rects:
        ax.annotate(f"{r.get_height():.0f}%", (r.get_x()+r.get_width()/2, r.get_height()),
                    ha="center", va="bottom", fontsize=8.5, xytext=(0, 1), textcoords="offset points")
ax.set_ylabel("Missing-QID rate")
ax.set_title("Unmatched cultural entities by topic: released data vs. paper",
             fontsize=12.5, fontweight="bold", pad=10)
ax.set_xticks(list(x)); ax.set_xticklabels(topics)
ax.yaxis.set_major_formatter(PercentFormatter())
ax.set_ylim(0, 80)
ax.grid(axis="y", color=GRID)
ax.legend(frameon=False, fontsize=9, loc="upper left", ncol=1)
style(ax)
fig.text(0.01, -0.02,
         "Cultural-only excludes person_name, place, listener_name, reader_name (the metric exclusions). "
         "Measured on a 200-row-per-cell sample of the released HF dataset.",
         fontsize=7.8, color="#555")
fig.tight_layout()
fig.savefig("docs/figures/missing_qid_by_topic.png", bbox_inches="tight")
plt.close(fig)
print("wrote docs/figures/missing_qid_by_topic.png")


# ---------------------------------------------------------------------------
# Figure 2: Surface-form to QID fragmentation (top labels)
# ---------------------------------------------------------------------------
# label gloss (romanized so the figure renders without CJK/Arabic fonts), distinct QIDs
frag = [
    ("shuǐ / 'water' (zh)", 17),
    ("drive (en)", 17),
    ("wasser / 'water' (de)", 15),
    ("bar (en/de)", 14),
    ("tango (es)", 13),
    ("mate (es)", 13),
    ("roman / 'novel' (de)", 13),
    ("ʿarabiyya (ar)", 13),
    ("fisch / 'fish' (de)", 13),
    ("qiṭār / 'train' (ar)", 12),
    ("toramu / 'tram' (ja)", 12),
    ("german (en)", 12),
]
frag = frag[::-1]
labels = [f[0] for f in frag]; vals = [f[1] for f in frag]
fig, ax = plt.subplots(figsize=(8.4, 5))
bars = ax.barh(labels, vals, color=C_AUDIT, height=0.66)
for b in bars:
    ax.annotate(f"{int(b.get_width())}", (b.get_width(), b.get_y()+b.get_height()/2),
                ha="left", va="center", fontsize=9, xytext=(3, 0), textcoords="offset points")
ax.set_xlabel("Number of distinct Wikidata QIDs linked to the same surface form")
ax.set_title("Surface-form to QID fragmentation (top labels)",
             fontsize=12.5, fontweight="bold", pad=10)
ax.set_xlim(0, 20)
ax.grid(axis="x", color=GRID)
style(ax)
fig.text(0.01, -0.03,
         "A single normalized label resolving to many QIDs inflates Diversity and lowers Consensus. "
         "Glosses are romanized; counts from the released HF dataset (sample=200/cell).",
         fontsize=7.8, color="#555")
fig.tight_layout()
fig.savefig("docs/figures/surface_form_fragmentation.png", bbox_inches="tight")
plt.close(fig)
print("wrote docs/figures/surface_form_fragmentation.png")


# ---------------------------------------------------------------------------
# Figure 3: Language mismatch (prompt language != generated language) — worst slices
# ---------------------------------------------------------------------------
leak = [
    ("Qwen2.5-7B / th / beverage", 47.5),
    ("Qwen2.5-7B / th / music", 37.5),
    ("Mistral-7B / it / beverage", 36.5),
    ("Qwen2.5-7B / ar / music", 36.5),
    ("Mistral-7B / it / food", 31.0),
    ("Qwen2.5-7B / fa / clothing", 30.5),
    ("Qwen2.5-7B / ar / food", 30.0),
    ("Qwen2.5-7B / es / transportation", 29.0),
    ("Qwen2.5-7B / ko / transportation", 28.0),
    ("Qwen2.5-7B / th / book", 27.5),
]
leak = leak[::-1]
labels = [f[0] for f in leak]; vals = [f[1] for f in leak]
fig, ax = plt.subplots(figsize=(8.6, 4.8))
bars = ax.barh(labels, vals, color="#9C4F2F", height=0.62)
for b in bars:
    ax.annotate(f"{b.get_width():.1f}%", (b.get_width(), b.get_y()+b.get_height()/2),
                ha="left", va="center", fontsize=9, xytext=(3, 0), textcoords="offset points")
ax.axvline(2.76, color="#444", linestyle="--", linewidth=1)
ax.annotate("dataset overall: 2.8%", (2.76, 0.2), xytext=(6, 0), textcoords="offset points",
            fontsize=8.5, color="#444", va="bottom")
ax.set_xlabel("Share of generations whose detected language differs from the prompt language")
ax.set_title("Language mismatch is concentrated in specific model-language slices",
             fontsize=12, fontweight="bold", pad=10)
ax.set_xlim(0, 52)
ax.grid(axis="x", color=GRID)
style(ax)
fig.text(0.01, -0.03,
         "Worst 10 slices shown; Qwen and Mistral on non-English prompts dominate, "
         "consistent with the paper's Appendix B note. Detector: langid (sample=200/cell).",
         fontsize=7.8, color="#555")
fig.tight_layout()
fig.savefig("docs/figures/language_mismatch_top_slices.png", bbox_inches="tight")
plt.close(fig)
print("wrote docs/figures/language_mismatch_top_slices.png")
