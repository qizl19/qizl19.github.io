from __future__ import annotations

"""Draw the teaching schematic for aeroengine briefing issue 10.

The curves are explicitly qualitative and do not represent an engine certification
map.  All labels, paths and exports are produced with matplotlib (Python backend).
"""

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch, Polygon


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "p" / "0ef0310c"
QA_OUT = ROOT / "tmp" / "aeroengine-10-qa"

mpl.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Microsoft YaHei", "Noto Sans CJK SC", "Arial", "DejaVu Sans"],
        "font.size": 8,
        "axes.titlesize": 10,
        "axes.labelsize": 8,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
    }
)

NAVY = "#17324d"
BLUE = "#2878b5"
CYAN = "#5bb8d4"
ORANGE = "#e98b2a"
RED = "#c9473a"
GREEN = "#3b8b6e"
PALE = "#eef4f7"
GRAY = "#5f6b73"


def arrow(ax, start, end, color=NAVY, lw=1.6, style="-|>", rad=0.0):
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle=style,
            mutation_scale=10,
            linewidth=lw,
            color=color,
            connectionstyle=f"arc3,rad={rad}",
        )
    )


def panel_a(ax):
    ax.set_title("a  回流区为什么能稳焰", loc="left", fontweight="bold", color=NAVY)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 7)
    ax.axis("off")

    duct = FancyBboxPatch((0.25, 1.1), 9.45, 4.8, boxstyle="round,pad=0.03", fc=PALE, ec=NAVY, lw=1)
    ax.add_patch(duct)
    ax.add_patch(Polygon([[2.2, 1.15], [2.2, 5.85], [3.35, 4.75], [3.35, 2.25]], fc="#c9d7df", ec=NAVY, lw=1))
    for y in (2.25, 3.5, 4.75):
        arrow(ax, (0.45, y), (2.0, y), color=BLUE, lw=1.3)
    ax.text(0.5, 6.15, "压气机来流", color=BLUE)

    ax.plot([2.0, 3.1], [3.5, 3.5], color=ORANGE, lw=3)
    for x, y, s in [(3.5, 3.9, 40), (3.8, 3.1, 28), (4.2, 4.25, 20), (4.45, 2.75, 18)]:
        ax.scatter(x, y, s=s, color=ORANGE, edgecolor="white", linewidth=0.4, zorder=4)
    ax.text(2.1, 0.55, "雾化 → 蒸发 → 混合", color=ORANGE)

    flame = Polygon(
        [[4.6, 2.0], [5.0, 3.1], [5.25, 2.6], [5.65, 4.9], [6.1, 3.2], [6.5, 4.0], [6.8, 2.0]],
        closed=True,
        fc="#f3a43b",
        ec=RED,
        lw=1.1,
        alpha=0.9,
    )
    ax.add_patch(flame)
    ax.text(5.15, 5.3, "主反应区", color=RED, fontweight="bold")

    arrow(ax, (6.55, 3.5), (4.0, 3.5), color=GREEN, lw=2.2, rad=0.55)
    arrow(ax, (4.0, 3.5), (6.55, 3.5), color=GREEN, lw=2.2, rad=0.55)
    ax.text(4.15, 1.35, "高温产物回卷：输送热量与活性基", color=GREEN)
    for y in (2.4, 3.5, 4.6):
        arrow(ax, (7.0, y), (9.35, y), color=GRAY, lw=1.3)

    ax.text(0.4, 6.65, "核心判据：Da = τflow / τchem；Da 下降，熄火风险上升", color=NAVY, fontweight="bold")


def panel_b(ax):
    ax.set_title("b  稳定边界：同一油气比在低压下未必可燃", loc="left", fontweight="bold", color=NAVY)
    phi = np.linspace(0.28, 1.08, 240)
    lean = 0.78 - 0.75 * (phi - 0.28) ** 0.65
    rich = 0.10 + 0.80 * np.exp(-((phi - 0.88) / 0.25) ** 2)
    lower = np.maximum(lean, 0.10)
    upper = np.maximum(rich, lower + 0.04)
    ax.fill_between(phi, lower, upper, color="#cce7dc", alpha=0.9, label="可持续燃烧区（定性）")
    ax.plot(phi, lower, color=RED, lw=2, label="稀熄边界")
    ax.plot(phi, upper, color=ORANGE, lw=1.7, ls="--", label="富油/排放与温度边界")
    ax.annotate("低压、低温、短停留时间\n使稀熄边界向右移动", xy=(0.43, 0.56), xytext=(0.64, 0.78),
                arrowprops=dict(arrowstyle="->", color=RED, lw=1), color=RED, ha="center")
    ax.annotate("减油轨迹", xy=(0.39, 0.43), xytext=(0.66, 0.43),
                arrowprops=dict(arrowstyle="->", color=BLUE, lw=1.5), color=BLUE)
    ax.scatter([0.44], [0.45], color=BLUE, s=35, zorder=5)
    ax.set_xlim(0.25, 1.12)
    ax.set_ylim(0.05, 1.0)
    ax.set_xlabel("局部当量比 φ（由稀到富）")
    ax.set_ylabel("归一化燃烧室入口总压（定性）")
    ax.grid(color="#d7e0e5", lw=0.6)
    ax.legend(frameon=False, loc="lower right", fontsize=7)
    ax.text(0.26, 0.97, "教学示意 · 非具体型号/认证包线", va="top", color=GRAY, fontsize=7)


def panel_c(ax):
    ax.set_title("c  FADEC 的任务：让燃油指令留在多重约束内", loc="left", fontweight="bold", color=NAVY)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 7)
    ax.axis("off")
    boxes = [
        (0.35, 4.5, 2.1, 1.2, "推力请求\n环境/状态"),
        (3.0, 4.5, 2.25, 1.2, "燃油与点火\n候选调度"),
        (7.1, 4.5, 2.4, 1.2, "发动机响应\nN、T、P、火焰"),
    ]
    for x, y, w, h, label in boxes:
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.08", fc=PALE, ec=NAVY, lw=1.2))
        ax.text(x + w / 2, y + h / 2, label, ha="center", va="center", color=NAVY, fontweight="bold")
    arrow(ax, (2.45, 5.1), (2.95, 5.1))
    arrow(ax, (5.25, 5.1), (7.05, 5.1))
    arrow(ax, (8.3, 4.45), (4.15, 3.7), color=GREEN, rad=-0.20)

    limits = [
        (0.55, 1.7, "稀熄/再点火\n下限", RED),
        (2.95, 1.7, "加速与喘振\n裕度", BLUE),
        (5.35, 1.7, "温度/超转\n上限", ORANGE),
        (7.75, 1.7, "执行机构/传感器\n有效性", GRAY),
    ]
    for x, y, label, color in limits:
        ax.add_patch(FancyBboxPatch((x, y), 1.75, 1.05, boxstyle="round,pad=0.08", fc="white", ec=color, lw=1.3))
        ax.text(x + 0.875, y + 0.525, label, ha="center", va="center", color=color, fontsize=7.5)
        arrow(ax, (x + 0.875, y + 1.05), (4.15, 4.45), color=color, lw=1.0)
    ax.text(0.45, 0.55, "控制律不是追求一个“最佳喷油量”，而是在可点燃、可持续、不过温、不喘振之间实时裁剪。",
            color=NAVY, fontweight="bold")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    QA_OUT.mkdir(parents=True, exist_ok=True)
    fig = plt.figure(figsize=(7.2, 5.2), constrained_layout=True)
    gs = fig.add_gridspec(2, 2, height_ratios=[1, 1], width_ratios=[1.05, 1])
    panel_a(fig.add_subplot(gs[0, 0]))
    panel_b(fig.add_subplot(gs[0, 1]))
    panel_c(fig.add_subplot(gs[1, :]))
    fig.suptitle("燃烧室稀熄、回流稳焰与加速控制：一张图读懂边界", fontsize=15, fontweight="bold", color=NAVY)
    fig.text(0.5, 0.01, "依据 NASA 稀熄/再点火研究与 FAA/EASA 控制要求绘制；所有曲线均为教学定性示意。", ha="center", color=GRAY, fontsize=7)
    fig.savefig(OUT / "combustor-stability-map.svg", bbox_inches="tight")
    fig.savefig(OUT / "combustor-stability-map.png", dpi=360, bbox_inches="tight")
    fig.savefig(QA_OUT / "combustor-stability-map.pdf", bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
