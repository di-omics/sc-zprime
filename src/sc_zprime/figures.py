"""Figures, drawn from the exported result tables only.

Style: light surface, hairlines, thin marks, one accent unless the data needs
more. Method tiers use the first three slots of a palette validated for
colour-vision deficiency on all pairs, and each tier also has its own marker
shape so identity never rests on colour alone.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker  # noqa: E402
import pandas as pd  # noqa: E402

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
INK_3 = "#8a8983"
HAIR = "#d9d8d2"
WINDOW = "#eef1f6"
BLUE = "#2a78d6"
BLUE_SOFT = "#9cc1ee"
ORANGE = "#eb6834"
AQUA = "#1baf7a"
GREY = "#b9b8b1"
GREY_SOFT = "#dddcd6"

TIER_STYLE = {
    "intended": {"color": BLUE, "marker": "o", "label": "intended method"},
    "partial": {"color": AQUA, "marker": "D", "label": "right family, missing a required element"},
    "trap": {"color": ORANGE, "marker": "v", "label": "method the task notes name as incorrect"},
    "other": {"color": INK_3, "marker": "s", "label": "not covered by the notes"},
}

PLATFORM = {
    "bd_rhapsody": "BD Rhapsody", "chromium": "10x Chromium", "csgenetics": "CS Genetics",
    "illumina-snrna": "Illumina snRNA", "missionbio-tapestri": "Mission Bio Tapestri", "parsebio": "Parse",
    "atlasxomics": "AtlasXomics", "curio": "Curio Seeker", "xenium": "Xenium", "visium": "Visium", "merfish": "MERFISH",
}
# A task whose category does not say what the traced readout is.
TASK_TITLE = {
    "NORM01_batch_correction": "Batch correction: mean share of the top donor per cluster (AtlasXomics)",
    "DR01_batch_confounded_clustering": "Batch correction: clusters dominated by one donor (AtlasXomics)",
    "curio_ovary_batch_driven_clustering": "Batch correction: largest share of one timepoint in a cluster (Curio Seeker)",
}
CATEGORY = {
    "qc": "Quality control", "normalization": "Normalization", "dimensionality_reduction": "PCA preprocessing",
    "clustering": "Clustering", "cell_typing": "Cell typing", "differential_expression": "Differential expression",
}


def _setup() -> None:
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
        "font.weight": "light",
        "font.size": 9.5,
        "axes.edgecolor": HAIR, "axes.linewidth": 0.6,
        "axes.labelcolor": INK_2, "axes.labelweight": "light",
        "axes.titleweight": "regular",
        "xtick.color": INK_2, "ytick.color": INK_2,
        "xtick.major.width": 0.6, "ytick.major.width": 0.6,
        "xtick.major.size": 3, "ytick.major.size": 0,
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "svg.fonttype": "none",
        "axes.unicode_minus": False,
        "svg.hashsalt": "sc-zprime",
    })


def task_names(results: Path) -> dict[str, str]:
    path = results / "tasks.csv"
    if not path.exists():
        return {}
    t = pd.read_csv(path)
    return {
        r.task: TASK_TITLE.get(r.task) or
        f"{CATEGORY.get(r.category, str(r.category).replace('_', ' ').capitalize())} ({PLATFORM.get(r.platform, r.platform)})"
        for r in t.itertuples()
    }


def _clean(ax, left: bool = False) -> None:
    for side in ("top", "right") + (() if left else ("left",)):
        ax.spines[side].set_visible(False)


def _save(fig, results: Path, stem: str) -> None:
    out = results / "figures"
    out.mkdir(exist_ok=True)
    fig.savefig(out / f"{stem}.png", dpi=220)
    fig.savefig(out / f"{stem}.svg", metadata={"Date": None})
    plt.close(fig)


def _zone_slots(lo: float, hi: float) -> dict[str, tuple[float, float, float]]:
    """For each zone a margin can be published as: where to draw it, and the stretch of the axis it covers."""
    reach = {
        "below, clear of the edge": (lo, -1.25), "below, near the edge": (-1.25, -1.0),
        "inside, near the lower edge": (-1.0, -0.8), "inside": (-0.8, 0.8), "inside, near the upper edge": (0.8, 1.0),
        "above, near the edge": (1.0, 1.25), "above, clear of the edge": (1.25, hi),
    }
    return {name: ((a + b) / 2, a, b) for name, (a, b) in reach.items()}


def fig_method_separation(results: Path) -> None:
    """Answer spectrum per traced task: where each method's answers land."""
    trace = pd.read_csv(results / "method_trace.csv")
    sep = pd.read_csv(results / "method_separation.csv").set_index("task")
    names = task_names(results)
    tasks = list(sep.index)
    lo, hi = -3.5, 4.5
    fig, axes = plt.subplots(len(tasks), 1, figsize=(9.2, 2.35 * len(tasks) + 0.9), sharex=True)
    axes = [axes] if len(tasks) == 1 else list(axes)
    for ax, task in zip(axes, tasks):
        g = trace[trace["task"] == task].copy()
        number = pd.to_numeric(g["margin"], errors="coerce")
        zones = sorted(set(g["margin"][number.isna() & g["margin"].notna()]))
        if zones:
            # A whole-number field with a small tolerance: the table gives each answer's zone, not its margin.
            # Each zone's runs are drawn in the middle of the zone, over a bar that shows how far the zone reaches.
            slot = _zone_slots(lo - 0.15, hi + 0.15)
            g["margin"] = g["margin"].map(lambda z: slot[z][0])
            for z in zones:
                ax.axvspan(slot[z][1], slot[z][2], ymin=0, ymax=0.035, color=GREY, lw=0, zorder=2)
            ax.text(0.998, 0.90, "a count with a small tolerance: placed by zone, not by position", transform=ax.transAxes,
                    ha="right", va="bottom", fontsize=7.5, color=INK_3)
        else:
            g["margin"] = number
        g["x"] = g["margin"].clip(lo, hi)
        g["off"] = (g["margin"] < lo) | (g["margin"] > hi)
        g["bin"] = g["x"].round(2)
        ax.axvspan(-1, 1, color=WINDOW, lw=0, zorder=0)
        ax.axvline(0, color=HAIR, lw=0.6, zorder=1)
        top = 0
        for x, col in g.groupby("bin"):
            base = 0
            for tier in ("intended", "partial", "trap", "other"):
                n = int((col["tier"] == tier).sum())
                if not n:
                    continue
                style = TIER_STYLE[tier]
                ax.plot([x, x], [base + (0.35 if base else 0), base + n], color=style["color"], lw=2.2,
                        solid_capstyle="butt", zorder=3)
                ax.plot([x], [base + n], marker=style["marker"], ms=5.6, color=style["color"],
                        mec=SURFACE, mew=0.9, zorder=4, clip_on=False)
                base += n
            top = max(top, base)
            if base >= 5:
                ax.text(x, base + top * 0.0 + 1.3, f"{base}", ha="center", va="bottom", fontsize=8.5, color=INK_2)
        n_off = int(g["off"].sum())
        if n_off:
            n_hi, n_lo = int((g["margin"] > hi).sum()), int((g["margin"] < lo).sum())
            if n_hi:
                # Sit above a tall spike near the right edge instead of across it.
                crowded = g[g["x"] > hi - 0.8].groupby("bin").size().max() > 0.25 * max(top * 1.28, 6)
                ax.text(0.998, 0.90 if crowded else 0.34, f"{n_hi} further right", transform=ax.transAxes, ha="right",
                        va="bottom", fontsize=7.5, color=INK_3)
            if n_lo:
                ax.text(0.002, 0.34, f"{n_lo} further left", transform=ax.transAxes, ha="left", va="bottom", fontsize=7.5, color=INK_3)
        m = sep.loc[task]
        title = names.get(task, task)
        ax.text(0.0, 1.13, title, transform=ax.transAxes, ha="left", va="bottom", fontsize=11, color=INK, fontweight="regular")
        note = (f"named-trap runs that pass: {int(m['trap_pass'])} of {int(m['trap_runs'])}"
                f"   |   intended-method runs that pass: {int(m['intended_pass'])} of {int(m['intended_runs'])}")
        ax.text(0.0, 1.02, note, transform=ax.transAxes, ha="left", va="bottom", fontsize=8.8, color=INK_2)
        ax.set_ylim(0, max(top * 1.28, 6))
        ax.set_xlim(lo - 0.15, hi + 0.15)
        ax.set_ylabel("runs", fontsize=8.5)
        ax.tick_params(axis="y", labelsize=8)
        ax.yaxis.set_major_locator(matplotlib.ticker.MaxNLocator(4, integer=True))
        ax.grid(axis="y", color=HAIR, lw=0.4, zorder=0)
        ax.set_axisbelow(True)
        _clean(ax)
    axes[0].text(-0.96, axes[0].get_ylim()[1] * 0.97, "pass window", ha="left", va="top", fontsize=8, color=INK_3)
    axes[-1].set_xlabel("submitted answer, in tolerance widths from the reference (0 = reference, -1 and +1 = edges of the pass window)", fontsize=8.8)
    handles = [plt.Line2D([0], [0], color=s["color"], marker=s["marker"], ms=5.6, lw=2.2, mec=SURFACE, mew=0.9, label=s["label"])
               for t, s in TIER_STYLE.items() if (trace["tier"] == t).any()]
    fig.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.065, 0.004), ncol=len(handles), frameon=False,
               fontsize=8.5, handlelength=1.3, columnspacing=1.6, labelcolor=INK_2)
    fig.subplots_adjust(left=0.065, right=0.985, top=0.92, bottom=0.12, hspace=0.58)
    _save(fig, results, "fig1_method_separation")


def _hbar_stack(ax, labels, parts, colors, invert: bool = True) -> None:
    y = range(len(labels))
    left = [0.0] * len(labels)
    totals = [sum(p[i] for p in parts) for i in range(len(labels))]
    for part, color in zip(parts, colors):
        widths = [100 * v / t if t else 0 for v, t in zip(part, totals)]
        ax.barh(y, widths, left=left, height=0.46, color=color, edgecolor=SURFACE, linewidth=1.6, zorder=3)
        for i, (w, v) in enumerate(zip(widths, part)):
            if w >= 5.0:
                dark = color in (BLUE, ORANGE, INK_3)
                ax.text(left[i] + w / 2, i, f"{int(v)}", ha="center", va="center", fontsize=8,
                        color=SURFACE if dark else INK_2, zorder=4)
        left = [a + b for a, b in zip(left, widths)]
    ax.set_yticks(list(y))
    ax.set_yticklabels(labels, fontsize=9, color=INK)
    ax.set_xlim(0, 100)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xticklabels(["0", "25", "50", "75", "100%"], fontsize=8)
    if invert:
        ax.invert_yaxis()
    ax.grid(axis="x", color=HAIR, lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    _clean(ax)
    ax.tick_params(axis="y", length=0, pad=6)


def fig_verdict_stability(results: Path) -> None:
    """Left: verdicts decided at the window edge. Right: verdicts that change on a repeat."""
    sweep = pd.read_csv(results / "tolerance_sweep.csv")
    rep = pd.read_csv(results / "repeatability.csv")
    names = task_names(results)
    tasks = [t for t in rep["task"] if t != "ALL"]
    order = tasks + ["ALL"]
    labels = [names.get(t, t) for t in tasks] + ["All six tasks"]

    def at(task, scale, col):
        row = sweep[(sweep["task"] == task) & (sweep["scale"] == scale)].iloc[0]
        return row[col]

    stable_pass, fragile_pass, fragile_fail, stable_fail = [], [], [], []
    for t in order:
        runs = int(at(t, 1.0, "runs"))
        passes = int(round(at(t, 1.0, "pass_rate") * runs))
        fp, ff = int(at(t, 0.8, "flips")), int(at(t, 1.25, "flips"))
        stable_pass.append(passes - fp)
        fragile_pass.append(fp)
        fragile_fail.append(ff)
        stable_fail.append(runs - passes - ff)

    r = rep.set_index("task").loc[order]
    fig, (a, b) = plt.subplots(1, 2, figsize=(11.2, 3.75), sharey=True)
    _hbar_stack(a, labels, [stable_pass, fragile_pass, fragile_fail, stable_fail], [BLUE, BLUE_SOFT, GREY_SOFT, GREY])
    _hbar_stack(b, labels, [list(r["all_pass"]), list(r["split"]), list(r["all_fail"])], [BLUE, ORANGE, GREY], invert=False)
    for ax in (a, b):
        ax.axhline(len(tasks) - 0.5, color=HAIR, lw=0.6, zorder=1)
    a.set_title("Verdicts that depend on where the window edge sits", loc="left", fontsize=10.5, color=INK, pad=28)
    b.set_title("Verdicts that depend on which repeat you look at", loc="left", fontsize=10.5, color=INK, pad=28)
    a.set_xlabel("share of graded runs", fontsize=8.8)
    b.set_xlabel("share of configurations (same model and harness, three repeats)", fontsize=8.8)
    key_a = [("pass", BLUE), ("pass, fails if 20% tighter", BLUE_SOFT), ("fail, passes if 25% wider", GREY_SOFT), ("fail", GREY)]
    key_b = [("passed every repeat", BLUE), ("split", ORANGE), ("failed every repeat", GREY)]
    for ax, key in ((a, key_a), (b, key_b)):
        handles = [plt.Rectangle((0, 0), 1, 1, color=c, label=l) for l, c in key]
        ax.legend(handles=handles, loc="lower left", bbox_to_anchor=(-0.01, 1.0), ncol=len(key), frameon=False,
                  fontsize=8, handlelength=0.9, handleheight=0.9, columnspacing=1.1, labelcolor=INK_2, borderaxespad=0.2)
    fig.subplots_adjust(left=0.215, right=0.985, top=0.80, bottom=0.14, wspace=0.07)
    _save(fig, results, "fig2_verdict_stability")


def _truthy(value) -> bool:
    """A CSV boolean, which may arrive as a bool or as the text 'True'."""
    return str(value).strip().lower() == "true"


def fig_leaderboard(results: Path) -> None:
    """Published accuracy and interval per configuration, leader's interval shaded.

    Colour says whether an unpaired test of the difference tells a
    configuration apart from the leader, which is a stricter question than
    whether the two intervals overlap."""
    path = results / "leaderboard_implied.csv"
    if not path.exists():
        return
    t = pd.read_csv(path).dropna(subset=["ci_lower", "ci_upper"]).sort_values("accuracy", ascending=False).reset_index(drop=True)
    lead_lo, lead_hi = t.loc[0, "ci_lower"], t.loc[0, "ci_upper"]
    fig, ax = plt.subplots(figsize=(8.6, 0.27 * len(t) + 1.5))
    ax.axvspan(lead_lo, lead_hi, color=WINDOW, lw=0, zorder=0)
    for i, r in t.iterrows():
        tied = i == 0 or not _truthy(r["told_apart_from_leader"])
        color = BLUE if tied else GREY
        ax.plot([r["ci_lower"], r["ci_upper"]], [i, i], color=color, lw=1.1, solid_capstyle="round", zorder=2)
        ax.plot([r["accuracy"]], [i], marker="o", ms=5.2, color=color, mec=SURFACE, mew=0.9, zorder=3)
    ax.set_yticks(range(len(t)))
    ax.set_yticklabels(t["config"], fontsize=8.3, color=INK)
    ax.invert_yaxis()
    ax.set_xlabel("published accuracy on the full task set, with 95% interval (%)\n"
                  "blue: not told apart from the leader by an unpaired test of the difference (5% level, unadjusted)",
                  fontsize=8.8)
    n_tied = int(sum(not _truthy(v) for v in t["told_apart_from_leader"].iloc[1:]))
    ax.set_title(f"{n_tied} of the other {len(t) - 1} configurations cannot be told apart from the leader", loc="left",
                 fontsize=10.5, color=INK, pad=12)
    ax.text((lead_lo + lead_hi) / 2, -0.72, "leader's interval", ha="center", va="center", fontsize=8, color=INK_3)
    ax.grid(axis="x", color=HAIR, lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0, pad=6)
    ax.tick_params(axis="x", labelsize=8)
    ax.set_ylim(len(t) - 0.4, -1.25)
    _clean(ax)
    fig.subplots_adjust(left=0.40, right=0.975, top=0.90, bottom=0.15)
    _save(fig, results, "fig3_leaderboard_intervals")


def fig_family_inventory(results: Path) -> None:
    """What each benchmark repository publishes, read from inventory.csv.

    One row per repository. A filled mark means the repository publishes that
    kind of file for its public tasks, a ring means it does not, and the
    number beside a mark is the count.
    """
    inv = pd.read_csv(results / "inventory.csv")
    for col in ("can_reproduce_verdicts", "can_grade_from_transcripts"):
        inv[col] = inv[col].map(_truthy)
    num = ["public_tasks", "tasks_with_a_public_grader", "transcripts", "runs_with_an_answer_file",
           "runs_with_a_published_verdict", "max_repeats"]
    inv[num] = inv[num].fillna(0).astype(int)
    inv["group"] = 3
    inv.loc[inv["transcripts"] > 0, "group"] = 2
    inv.loc[inv["can_grade_from_transcripts"], "group"] = 1
    inv.loc[inv["can_reproduce_verdicts"], "group"] = 0
    inv["key"] = inv["benchmark"].str.lower()
    inv = inv.sort_values(["group", "transcripts", "key"], ascending=[True, False, True]).reset_index(drop=True)
    group_names = ["verdicts can be reproduced", "runs can be graded once", "runs published, no public grader",
                   "no runs published"]
    headers = ["public grader", "transcripts", "answer files", "verdicts", "repeats"]

    # Laid out in inches, y growing downward: one row per repository, extra room above each group.
    row_h, gap, head, foot = 0.25, 0.34, 0.42, 0.36
    ys, y = [], head
    for i, g in enumerate(inv["group"]):
        if i == 0 or g != inv["group"][i - 1]:
            y += gap
        ys.append(y)
        y += row_h
    height = y + foot
    width = 9.0
    name_x, tasks_x = 0.12, 2.80
    col_x = [3.62 + 1.12 * k for k in range(len(headers))]

    fig = plt.figure(figsize=(width, height))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, width)
    ax.set_ylim(height, 0)
    ax.axis("off")

    def mark(x, yy, on, fill):
        if on:
            ax.plot([x], [yy], marker="o", ms=6.4, color=fill, mec=fill, mew=0.0, zorder=3)
        else:
            ax.plot([x], [yy], marker="o", ms=6.0, mfc=SURFACE, mec=INK_3, mew=0.75, zorder=3)

    for x, h in zip(col_x, headers):
        ax.text(x, head - 0.06, h, ha="center", va="bottom", fontsize=8.8, color=INK_2)
    ax.plot([name_x, width - 0.12], [head + 0.02, head + 0.02], color=HAIR, lw=0.6)

    for i, r in inv.iterrows():
        yy = ys[i]
        g = int(r["group"])
        if i == 0 or g != inv["group"][i - 1]:
            top = yy - gap + 0.04
            if i:
                ax.plot([name_x, width - 0.12], [top, top], color=HAIR, lw=0.5)
            ax.text(name_x, yy - row_h / 2 - 0.035, group_names[g], ha="left", va="bottom", fontsize=7.8, color=INK_3)
        ax.text(name_x, yy, r["benchmark"], ha="left", va="center", fontsize=9, color=INK)
        n = int(r["public_tasks"])
        ax.text(tasks_x, yy, f"{n} task{'s' if n != 1 else ''}", ha="right", va="center", fontsize=8, color=INK_3)
        graded = int(r["tasks_with_a_public_grader"])
        cells = [
            (graded > 0 and graded == n, str(graded) if graded == n else (f"{graded}/{n}" if graded else "")),
            (r["transcripts"] > 0, str(r["transcripts"]) if r["transcripts"] else ""),
            (r["runs_with_an_answer_file"] > 0, str(r["runs_with_an_answer_file"]) if r["runs_with_an_answer_file"] else ""),
            (r["runs_with_a_published_verdict"] > 0,
             str(r["runs_with_a_published_verdict"]) if r["runs_with_a_published_verdict"] else ""),
            (r["max_repeats"] >= 2, str(r["max_repeats"]) if r["transcripts"] > 0 and r["max_repeats"] else ""),
        ]
        fill = ORANGE if g == 0 else INK
        for x, (on, label) in zip(col_x, cells):
            mark(x - 0.13, yy, on, fill)
            if label:
                ax.text(x - 0.02, yy, label, ha="left", va="center", fontsize=7.8, color=INK_2 if on else INK_3)

    # Key, under the last row.
    ky = height - 0.15
    ax.plot([name_x, width - 0.12], [ky - 0.17, ky - 0.17], color=HAIR, lw=0.5)
    mark(name_x + 0.06, ky, True, INK)
    ax.text(name_x + 0.19, ky, "published", ha="left", va="center", fontsize=7.8, color=INK_3)
    mark(name_x + 1.02, ky, False, INK)
    ax.text(name_x + 1.15, ky, "not published", ha="left", va="center", fontsize=7.8, color=INK_3)
    ax.text(name_x + 2.25, ky, "numbers: public tasks with a grader, runs, and repeats per configuration", ha="left",
            va="center", fontsize=7.8, color=INK_3)
    _save(fig, results, "fig_family_inventory")


def draw_all(results: str | Path) -> None:
    results = Path(results)
    _setup()
    if (results / "method_trace.csv").exists():
        fig_method_separation(results)
    fig_verdict_stability(results)
    fig_leaderboard(results)


def draw_family(results: str | Path) -> None:
    """The figure for `sc-zprime inventory`."""
    results = Path(results)
    _setup()
    fig_family_inventory(results)
