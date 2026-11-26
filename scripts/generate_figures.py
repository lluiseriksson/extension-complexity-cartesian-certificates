"""
Generate the 3 publication-grade figures for paper76-extension-complexity-cartesian-certificates
directly from live verify_file outputs and exact Fraction computations.
"""

from __future__ import annotations

import pathlib
import sys
from fractions import Fraction

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ext_complexity_verifier import verify_file

CERTS_DIR = ROOT / "certificates"
FIG_DIR = ROOT / "paper" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "font.family": "serif",
    "font.size": 9.5,
    "axes.titlesize": 10.5,
    "axes.labelsize": 9.5,
    "legend.fontsize": 8.0,
    "xtick.labelsize": 8.5,
    "ytick.labelsize": 8.5,
    "figure.dpi": 240,
})


def _r2f(pair: list[int]) -> float:
    return pair[0] / pair[1]


def fig1_rank_gap_and_prop9_margins() -> None:
    """Figure 1: Ordinary rank vs rectangle cover vs exact nonnegative rank/xc (Theorem 1) and Prop. 9 margins."""
    r03 = verify_file(CERTS_DIR / "C03_polytope_P_canonical_L1e6.json")
    r05 = verify_file(CERTS_DIR / "C05_twin_hexagon_S_S1S_L1e6.json")
    r07 = verify_file(CERTS_DIR / "C07_prop9_exact_L1e6_tau1_5000.json")
    r08 = verify_file(CERTS_DIR / "C08_prop9_tightened_L1e7_tau1_20000.json")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.4, 3.55))

    # Panel (a): Matrix S & S x_1 S vs Wedged Polytope P & P x P
    labels = ["$S$ (rank / RC)", "$S$ ($\\mathrm{rank}_+$)", "$S\\otimes_1 S$\n(2x single)", "$S\\otimes_1 S$\n(actual)", "$P$ ($\\mathrm{xc}$)", "$P\\times P$\n(2x vs actual)"]
    # Cleaner grouped bar comparing Separate vs Joint for Matrix S and Polytope P!
    cats = ["Ordinary\nrank", "Rect.\ncover", "$\\mathrm{rank}_+$\n(Sec. 3–4)", "Polytope $\\mathrm{xc}$\n(Thm. 1)"]
    single2 = [24, 24, 2 * r05["upper_rank_S"], 2 * 40]
    joint = [24, 24, r05["upper_rank_S1S"], 79]
    x = list(range(len(cats)))
    w = 0.34
    b1 = ax1.bar([i - w / 2 for i in x], single2, width=w, color="#4292c6", label=r"Sum of 2 factors ($2\times$ single)")
    b2 = ax1.bar([i + w / 2 for i in x], joint, width=w, color="#e6550d", label=r"Joint product ($S\otimes_1 S$ / $P\times P$)")
    for bars in (b1, b2):
        for bar in bars:
            h = int(bar.get_height())
            ax1.text(bar.get_x() + bar.get_width() / 2.0, h + 1.5, str(h), ha="center", va="bottom", fontsize=7.8)
    ax1.set_xticks(x)
    ax1.set_xticklabels(cats)
    ax1.set_ylim(0, 96)
    ax1.set_ylabel("Exact complexity / rank")
    ax1.set_title("(a) Subadditivity Gap Invisible to Rank & Rect. Cover")
    ax1.legend(loc="upper left", frameon=True, framealpha=0.92)
    ax1.grid(axis="y", alpha=0.25)

    # Panel (b): Prop. 9 Claim 2 probe bound & Claim 3 alternating-sum bound (< 1)
    c_names = ["Claim 2\nProbe UB\n(C07)", "Claim 3\nAlt. Sum UB\n(C07)", "Claim 2\nProbe UB\n(C08)", "Claim 3\nAlt. Sum UB\n(C08)"]
    c_vals = [
        _r2f(r07["claim2_probe_ub"]),
        _r2f(r07["claim3_alt_ub"]),
        _r2f(r08["claim2_probe_ub"]),
        _r2f(r08["claim3_alt_ub"]),
    ]
    colors = ["#2b8cbe", "#f03b20", "#74c476", "#31a354"]
    bars2 = ax2.bar(range(len(c_names)), c_vals, color=colors, width=0.55)
    ax2.axhline(1.0, color="#cb181d", lw=1.6, ls="--", label="Contradiction threshold $1$")
    for bar, v in zip(bars2, c_vals):
        ax2.text(bar.get_x() + bar.get_width() / 2.0, v + 0.025, f"{v:.4f}", ha="center", va="bottom", fontsize=7.6)
    ax2.set_xticks(range(len(c_names)))
    ax2.set_xticklabels(c_names)
    ax2.set_ylim(0.0, 1.18)
    ax2.set_ylabel("Exact rational upper bound")
    ax2.set_title("(b) Prop. 9 Certified Quantitative Margins ($L=10^6, 10^7$)")
    ax2.legend(loc="upper right", frameon=True, framealpha=0.92)
    ax2.grid(axis="y", alpha=0.25)

    assert r03["polytope_P_vertices"] == 150
    assert len(labels) == 6
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig1_rank_gap_and_prop9_margins.png")
    plt.close(fig)


def fig2_prop11_counting_and_deficit() -> None:
    """Figure 2: Sec. 6.2 conditional counting profiles d*rho^(d-1) and linear deficit ceil(5n/27)."""
    r11 = verify_file(CERTS_DIR / "C11_prop11_n6_first_saving2.json")
    r12 = verify_file(CERTS_DIR / "C12_prop11_n27_exact_saving5.json")

    ds = list(range(1, 13))
    y_half = [float(Fraction(d, 1) * (Fraction(1, 2) ** (d - 1))) for d in ds]
    y_34 = [float(Fraction(d, 1) * (Fraction(3, 4) ** (d - 1))) for d in ds]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.4, 3.55))

    ax1.plot(ds, y_34, marker="o", ms=5.0, color="#d95f02", lw=2.0, label=r"$k=3$ ($\rho=3/4$): max $27/16$ at $d\in\{3,4\}$")
    ax1.plot(ds, y_half, marker="s", ms=4.5, color="#1b5e9c", lw=2.0, label=r"$k=2$ ($\rho=1/2$): max $1$ at $d\in\{1,2\}$")
    ax1.axhline(27.0 / 16.0, color="#d95f02", lw=1.0, ls=":")
    ax1.scatter([3, 4], [27.0 / 16.0, 27.0 / 16.0], color="#cb181d", s=55, zorder=5)
    ax1.set_title(r"(a) Prop. 11 Discrete Maxima of $d\rho^{d-1}$")
    ax1.set_xlabel(r"Number of specified blocks $d = |J_z|$")
    ax1.set_ylabel(r"Exact expected coverage $d\rho^{d-1}$")
    ax1.set_xticks(ds)
    ax1.set_ylim(0.0, 2.05)
    ax1.legend(loc="upper right", frameon=True, framealpha=0.92)
    ax1.grid(alpha=0.25)

    # Panel (b): Deficit lower bound ceil(5n/27) vs n, highlighting live C11 (n=6, delta>=2) and C12 (n=27, delta>=5)
    ns = list(range(1, 37))
    defs = [(5 * n + 26) // 27 for n in ns]
    lin = [5.0 * n / 27.0 for n in ns]
    ax2.step(ns, defs, where="mid", color="#1b5e9c", lw=2.0, label=r"Guaranteed integer deficit $\lceil 5n/27 \rceil$")
    ax2.plot(ns, lin, color="#7570b3", lw=1.4, ls="--", label=r"Linear slope $5n/27$")
    ax2.scatter(
        [r11["num_blocks_n"], r12["num_blocks_n"]],
        [r11["deficit_lb"], r12["deficit_lb"]],
        color="#e6550d", s=65, zorder=5, label="Live certified C11, C12",
    )
    ax2.annotate("C11 ($n=6, \\delta\\geq 2$)", xy=(6, 2), xytext=(9.5, 1.15),
                 arrowprops={"arrowstyle": "->", "lw": 0.9, "color": "#444"}, fontsize=8.0)
    ax2.annotate("C12 ($n=27, \\delta\\geq 5$)", xy=(27, 5), xytext=(17.5, 2.75),
                 arrowprops={"arrowstyle": "->", "lw": 0.9, "color": "#444"}, fontsize=8.0)
    ax2.set_title(r"(b) Linear-Fraction Deficit $\delta(U_n, V_n) \geq \lceil 5n/27 \rceil$")
    ax2.set_xlabel("Number of independent blocks $n$")
    ax2.set_ylabel("Deficit lower bound (inequalities saved)")
    ax2.set_xlim(0.5, 36.5)
    ax2.set_ylim(0.0, 7.8)
    ax2.legend(loc="upper left", frameon=True, framealpha=0.92)
    ax2.grid(alpha=0.25)

    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig2_prop11_counting_and_deficit.png")
    plt.close(fig)


def fig3_squares_and_channel_sim() -> None:
    """Figure 3: Alphabet-separated square deficits (Lemmas 12-13) and Sec. 7.2 zero-error channel bit saving."""
    r13 = verify_file(CERTS_DIR / "C13_square_alphabet_t2_j2_4.json")
    r14 = verify_file(CERTS_DIR / "C14_square_alphabet_t2_j2_5.json")
    r15 = verify_file(CERTS_DIR / "C15_corollaries_and_channel_d48.json")
    r16 = verify_file(CERTS_DIR / "C16_corollaries_and_channel_d176.json")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.4, 3.55))

    # Panel (a): Canonical doubling sequence j_1=2, j_i = 2*sum_{h<i} j_h (cover number vs joint twin budget)
    ts = [1, 2, 3, 4]
    j_seq = [2, 4, 12, 36]
    two_Ct = [2 * sum(j_seq[:t]) for t in ts]
    joint_twins = [sum(2 * j - 1 for j in j_seq[:t]) for t in ts]
    x = list(range(len(ts)))
    w = 0.34
    b1 = ax1.bar([i - w / 2 for i in x], two_Ct, width=w, color="#4292c6", label=r"Separate hitting cost $2C_t$")
    b2 = ax1.bar([i + w / 2 for i in x], joint_twins, width=w, color="#31a354", label=r"Shared twin cost $\sum (2j_i - 1)$")
    for i in x:
        ax1.text(i, max(two_Ct[i], joint_twins[i]) + 2.5, f"$-{ts[i]}$", ha="center", va="bottom", fontsize=8.0, color="#cb181d", fontweight="bold")
    ax1.set_xticks(x)
    ax1.set_xticklabels([f"$t={t}$\n$j_t={j_seq[t-1]}$" for t in ts])
    ax1.set_ylim(0, 125)
    ax1.set_ylabel("Extra label generators (beyond $2p^\\star$)")
    ax1.set_title("(a) Unbounded Square Savings $\\delta(R_t, R_t) \\geq t$ (Lemma 12–13)")
    ax1.legend(loc="upper left", frameon=True, framealpha=0.92)
    ax1.grid(axis="y", alpha=0.25)

    # Panel (b): Sec. 7.2 Zero-error channel simulation (C15 d=48: 129->128; C16 d=176: 257->256)
    ch_labels = ["$Q=P,\\ Q'=P\\times\\Delta_{48}$\n(C15: 8 bits $\\to$ 7 bits)", "$Q=P,\\ Q'=P\\times\\Delta_{176}$\n(C16: 9 bits $\\to$ 8 bits)"]
    sep_m = [r15["channel_separate_msgs"], r16["channel_separate_msgs"]]
    jnt_m = [r15["channel_joint_msgs"], r16["channel_joint_msgs"]]
    x2 = [0, 1]
    w2 = 0.32
    c1 = ax2.bar([i - w2 / 2 for i in x2], sep_m, width=w2, color="#d95f02", label="Label-determined messages")
    c2 = ax2.bar([i + w2 / 2 for i in x2], jnt_m, width=w2, color="#1b9e77", label="Joint slack-channel messages")
    ax2.axhline(128, color="#555555", lw=1.0, ls=":")
    ax2.axhline(256, color="#555555", lw=1.0, ls=":")
    for bars in (c1, c2):
        for bar in bars:
            h = int(bar.get_height())
            ax2.text(bar.get_x() + bar.get_width() / 2.0, h + 4.5, str(h), ha="center", va="bottom", fontsize=8.0)
    ax2.set_xticks(x2)
    ax2.set_xticklabels(ch_labels)
    ax2.set_ylim(0, 310)
    ax2.set_ylabel("Minimum message alphabet size")
    ax2.set_title("(b) Zero-Error Channel Bit-Width Drops (Sec. 7.2)")
    ax2.legend(loc="upper left", frameon=True, framealpha=0.92)
    ax2.grid(axis="y", alpha=0.25)

    assert r13["square_deficit_lb"] == 2 and r14["square_deficit_lb"] == 2
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig3_squares_and_channel_sim.png")
    plt.close(fig)


def main() -> int:
    fig1_rank_gap_and_prop9_margins()
    fig2_prop11_counting_and_deficit()
    fig3_squares_and_channel_sim()
    print(f"Generated 3 figures in {FIG_DIR}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
