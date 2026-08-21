"""Generate the traceable control figure for aeroengine briefing 11.

The curves are deterministic teaching data, not a certified engine schedule.
They show how an acceleration command is clipped by operability limiters and
how the same logic can be represented as an auditable FADEC state machine.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


COLORS = {
    "navy": "#17324d",
    "blue": "#2878b5",
    "cyan": "#4ca6c7",
    "orange": "#e38b2c",
    "red": "#c9574d",
    "green": "#3b8d78",
    "gray": "#667784",
    "light": "#edf3f6",
}


def configure() -> None:
    family = "DejaVu Sans"
    for candidate in (Path(r"C:\Windows\Fonts\msyh.ttc"), Path(r"C:\Windows\Fonts\simhei.ttf")):
        if candidate.is_file():
            font_manager.fontManager.addfont(candidate)
            family = font_manager.FontProperties(fname=candidate).get_name()
            break
    mpl.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": [family, "Arial", "DejaVu Sans"],
        "axes.unicode_minus": False,
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "font.size": 8.2,
        "axes.titlesize": 10.2,
        "axes.labelsize": 8.2,
        "xtick.labelsize": 7.2,
        "ytick.labelsize": 7.2,
        "axes.spines.right": False,
        "axes.spines.top": False,
    })


def rounded_box(ax, xy, size, text, color, fontsize=8.2) -> None:
    x, y = xy
    width, height = size
    ax.add_patch(FancyBboxPatch(
        (x, y), width, height,
        boxstyle="round,pad=0.02,rounding_size=0.04",
        facecolor=color, edgecolor="white", linewidth=1.0,
    ))
    ax.text(x + width / 2, y + height / 2, text, ha="center", va="center",
            color="white", weight="bold", fontsize=fontsize)


def arrow(ax, start, end, color=COLORS["navy"], connection="arc3,rad=0") -> None:
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=11,
                                 color=color, linewidth=1.25, connectionstyle=connection))


def teaching_profile() -> tuple[np.ndarray, ...]:
    time = np.linspace(0.0, 5.0, 101)
    demand = np.where(time < 0.5, 0.28, 0.28 + 0.62 * (1.0 - np.exp(-(time - 0.5) / 0.55)))
    acceleration_limit = 0.50 + 0.075 * time
    temperature_limit = 0.86 - 0.035 * np.exp(-((time - 2.0) / 0.75) ** 2)
    overspeed_limit = np.full_like(time, 0.94)
    scheduled = np.minimum.reduce([demand, acceleration_limit, temperature_limit, overspeed_limit])
    normalized_speed = 0.30 + 0.64 * (1.0 - np.exp(-np.maximum(time - 0.55, 0.0) / 1.15))
    surge_margin = 18.0 - 5.2 * np.exp(-((time - 1.7) / 0.85) ** 2)
    return time, demand, acceleration_limit, temperature_limit, overspeed_limit, scheduled, normalized_speed, surge_margin


def draw(output_dir: Path, qa_dir: Path, data_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    qa_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    values = teaching_profile()
    time, demand, accel, temp, speed_limit, scheduled, rotor_speed, surge_margin = values

    fig = plt.figure(figsize=(7.35, 7.15), constrained_layout=True)
    grid = fig.add_gridspec(3, 2, height_ratios=[1.05, 1.0, 0.92], width_ratios=[1.0, 1.0])

    ax0 = fig.add_subplot(grid[0, :])
    ax0.set_xlim(0, 10)
    ax0.set_ylim(0, 3.2)
    ax0.axis("off")
    rounded_box(ax0, (0.15, 1.98), (1.45, 0.65), "驾驶员/自动推力\n功率请求", COLORS["navy"])
    rounded_box(ax0, (2.00, 1.98), (1.48, 0.65), "目标生成\nNref / 推力", COLORS["blue"])
    rounded_box(ax0, (3.94, 1.98), (1.56, 0.65), "候选燃油\nWf,cand", COLORS["cyan"])
    rounded_box(ax0, (6.08, 1.98), (1.55, 0.65), "最小值选择器\n上限裁剪", COLORS["orange"])
    rounded_box(ax0, (8.28, 1.98), (1.50, 0.65), "燃油计量阀\n与可调几何", COLORS["green"])
    for start, end in [((1.60, 2.31), (2.00, 2.31)), ((3.48, 2.31), (3.94, 2.31)),
                       ((5.50, 2.31), (6.08, 2.31)), ((7.63, 2.31), (8.28, 2.31))]:
        arrow(ax0, start, end)
    limiter_boxes = [
        (0.38, "加速/喘振上限", COLORS["red"]),
        (2.30, "温度上限", COLORS["red"]),
        (4.22, "转速上限", COLORS["red"]),
        (6.14, "减速/熄火下限", COLORS["blue"]),
        (8.06, "执行机构/故障限值", COLORS["gray"]),
    ]
    for x, label, color in limiter_boxes:
        rounded_box(ax0, (x, 0.45), (1.55, 0.55), label, color, fontsize=7.6)
        arrow(ax0, (x + 0.78, 1.00), (6.78, 1.98), color=color, connection="arc3,rad=-0.16")
    ax0.text(0.02, 3.05, "a  FADEC 的核心不是单一闭环，而是请求、限制器与执行机构的仲裁",
             transform=ax0.transData, weight="bold", color=COLORS["navy"], fontsize=10.2)
    ax0.text(0.16, 0.08, "加速时选最小允许上限；减速时还要守住最低稳定燃油。故障逻辑可改变可用通道或进入保底模式。",
             color=COLORS["gray"], fontsize=7.4)

    ax1 = fig.add_subplot(grid[1, 0])
    ax1.plot(time, demand, color=COLORS["gray"], lw=1.6, ls="--", label="请求燃油")
    ax1.plot(time, accel, color=COLORS["red"], lw=1.5, label="加速/喘振上限")
    ax1.plot(time, temp, color=COLORS["orange"], lw=1.5, label="温度上限")
    ax1.plot(time, speed_limit, color=COLORS["navy"], lw=1.2, ls=":", label="转速上限")
    ax1.plot(time, scheduled, color=COLORS["green"], lw=2.5, label="最终燃油指令")
    ax1.fill_between(time, scheduled, demand, where=demand > scheduled, color=COLORS["red"], alpha=0.10)
    ax1.set_xlabel("时间 [s]")
    ax1.set_ylabel("归一化燃油指令 [-]")
    ax1.set_ylim(0.2, 1.0)
    ax1.grid(alpha=0.18)
    ax1.legend(ncol=2, fontsize=6.8, loc="lower right")
    ax1.set_title("b  教学加速：请求被瞬态约束逐段接管", loc="left", weight="bold")

    ax2 = fig.add_subplot(grid[1, 1])
    ax2.plot(time, rotor_speed * 100.0, color=COLORS["blue"], lw=2.2, label="转子修正转速")
    ax2.set_xlabel("时间 [s]")
    ax2.set_ylabel("归一化转速 [%]", color=COLORS["blue"])
    ax2.tick_params(axis="y", labelcolor=COLORS["blue"])
    ax2.grid(alpha=0.18)
    margin_ax = ax2.twinx()
    margin_ax.plot(time, surge_margin, color=COLORS["red"], lw=1.9, label="HPC 喘振裕度")
    margin_ax.axhline(12.0, color=COLORS["gray"], lw=1.0, ls="--")
    margin_ax.set_ylabel("喘振裕度 [%]", color=COLORS["red"])
    margin_ax.tick_params(axis="y", labelcolor=COLORS["red"])
    margin_ax.set_ylim(10, 20)
    ax2.set_title("c  响应时间与最小喘振裕度必须同时验收", loc="left", weight="bold")
    ax2.text(0.03, 0.06, "虚线 12% 仅为示教门槛", transform=ax2.transAxes, color=COLORS["gray"], fontsize=7)

    ax3 = fig.add_subplot(grid[2, :])
    ax3.set_xlim(0, 10)
    ax3.set_ylim(0, 2.45)
    ax3.axis("off")
    states = [
        (0.10, "停止", COLORS["gray"]), (1.70, "盘车/清吹", COLORS["blue"]),
        (3.30, "点火供油", COLORS["orange"]), (4.90, "Light-off\n加速至慢车", COLORS["red"]),
        (6.65, "稳态调节", COLORS["green"]), (8.25, "减速/关车", COLORS["navy"]),
    ]
    for x, label, color in states:
        rounded_box(ax3, (x, 1.18), (1.25, 0.58), label, color, fontsize=7.5)
    for index in range(len(states) - 1):
        arrow(ax3, (states[index][0] + 1.25, 1.47), (states[index + 1][0], 1.47))
    arrow(ax3, (8.88, 1.18), (3.93, 0.62), COLORS["red"], connection="arc3,rad=0.22")
    ax3.text(6.45, 0.43, "异常温升、无点火、转速不增长或传感器/执行机构故障 → 切油、清吹或保底模式",
             ha="center", color=COLORS["red"], fontsize=7.5, weight="bold")
    ax3.text(0.02, 2.25, "d  可审计状态机：每次转换都需要进入条件、超时、退出条件和失败处置",
             weight="bold", color=COLORS["navy"], fontsize=10.2)
    ax3.text(0.12, 0.06, "所有数值曲线均为透明教学数据；不对应任何型号的认证控制律、真实裕度或操作程序。",
             color=COLORS["red"], fontsize=7.5)

    stem = output_dir / "fadec-transient-state-machine"
    svg_path = stem.with_suffix(".svg")
    fig.savefig(svg_path, bbox_inches="tight", facecolor="white")
    svg_path.write_text(
        "\n".join(line.rstrip() for line in svg_path.read_text(encoding="utf-8").splitlines()) + "\n",
        encoding="utf-8",
    )
    fig.savefig(stem.with_suffix(".png"), dpi=330, bbox_inches="tight", facecolor="white")
    fig.savefig(qa_dir / "fadec-transient-state-machine.pdf", bbox_inches="tight", facecolor="white")
    fig.savefig(qa_dir / "fadec-transient-state-machine.tiff", dpi=600, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    with (data_dir / "fadec-transient-teaching-profile.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["time_s", "fuel_demand_norm", "accel_limit_norm", "temperature_limit_norm",
                         "overspeed_limit_norm", "scheduled_fuel_norm", "rotor_speed_norm", "surge_margin_percent",
                         "scope"])
        for row in zip(*values):
            writer.writerow([*(f"{value:.6f}" for value in row), "deterministic teaching data; not a certified schedule"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--qa-dir", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    configure()
    draw(root / "p" / "f39e6def", args.qa_dir.resolve(), root / "data" / "aeroengine")


if __name__ == "__main__":
    main()
