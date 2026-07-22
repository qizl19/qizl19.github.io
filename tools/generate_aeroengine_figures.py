"""Generate traceable engineering figures for the aeroengine learning series.

Figure contract for briefing 01
--------------------------------
Core conclusion:
    Compressor work, turbine work, and the remaining nozzle energy must be
    balanced; compressor pressure ratio alone cannot describe engine quality.
Figure archetype:
    Schematic-led composite with a T-s hero panel and station-wise validation.
Target/output:
    Chinese technical blog and A4 PDF; SVG editable text plus web PNG/WebP.
Backend:
    Python / matplotlib only.
Final size:
    183 mm wide for article figures; 16:9 for the category/hero cover.
Evidence hierarchy:
    T-s ideal/real comparison -> ideal efficiency trend -> station totals and
    shaft work balance.
Reviewer risk:
    Readers may mistake ideal-cycle trends or normalized station values for a
    real engine data set. Every figure therefore labels its assumptions.
"""

from __future__ import annotations

import argparse
import csv
import json
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


def configure_matplotlib() -> None:
    candidates = [
        Path(r"C:\Windows\Fonts\msyh.ttc"),
        Path(r"C:\Windows\Fonts\simhei.ttf"),
    ]
    family = "DejaVu Sans"
    for candidate in candidates:
        if candidate.is_file():
            font_manager.fontManager.addfont(candidate)
            family = font_manager.FontProperties(fname=candidate).get_name()
            break
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": [family, "Arial", "DejaVu Sans"],
            "axes.unicode_minus": False,
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "font.size": 8.5,
            "axes.titlesize": 10.5,
            "axes.labelsize": 8.5,
            "xtick.labelsize": 7.5,
            "ytick.labelsize": 7.5,
            "axes.spines.right": False,
            "axes.spines.top": False,
            "axes.linewidth": 0.8,
            "legend.frameon": False,
        }
    )


def save_web_figure(fig: plt.Figure, stem: Path, qa_dir: Path) -> None:
    svg_path = stem.with_suffix(".svg")
    fig.savefig(svg_path, bbox_inches="tight", facecolor="white")
    svg_path.write_text(
        "\n".join(line.rstrip() for line in svg_path.read_text(encoding="utf-8").splitlines()) + "\n",
        encoding="utf-8",
    )
    fig.savefig(stem.with_suffix(".png"), dpi=360, bbox_inches="tight", facecolor="white")
    fig.savefig(qa_dir / f"{stem.name}.pdf", bbox_inches="tight", facecolor="white")
    fig.savefig(qa_dir / f"{stem.name}.tiff", dpi=600, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def thermodynamic_states() -> dict[str, object]:
    gamma_a = 1.4
    gamma_g = 1.33
    cp_a = 1.005  # kJ/(kg K)
    cp_g = 1.148  # kJ/(kg K)
    r_a = cp_a * (gamma_a - 1.0) / gamma_a
    r_g = cp_g * (gamma_g - 1.0) / gamma_g
    t2 = 288.0
    p2 = 1.0
    pressure_ratio = 12.0
    eta_c = 0.86
    eta_t = 0.89
    eta_m = 0.99
    burner_pressure_ratio = 0.95
    t4 = 1450.0

    exponent_a = (gamma_a - 1.0) / gamma_a
    t3s = t2 * pressure_ratio**exponent_a
    t3 = t2 + (t3s - t2) / eta_c
    compressor_work = cp_a * (t3 - t2)
    t5 = t4 - compressor_work / (eta_m * cp_g)
    t5s = t4 - (t4 - t5) / eta_t
    p3 = p2 * pressure_ratio
    p4 = p3 * burner_pressure_ratio
    p5 = p4 * (t5s / t4) ** (gamma_g / (gamma_g - 1.0))

    # Entropy is relative to station 2. The values are for diagram placement,
    # not a measured engine data set.
    if np.any(np.asarray([t2, t3s, t3, t4, t5, p2, p3, p4, p5]) <= 0):
        raise ValueError("Thermodynamic temperature and pressure values must be strictly positive")
    s2 = 0.0
    s3s = cp_a * np.log(t3s / t2) - r_a * np.log(p3 / p2)
    s3 = cp_a * np.log(t3 / t2) - r_a * np.log(p3 / p2)
    s4 = s3 + cp_g * np.log(t4 / t3) - r_g * np.log(p4 / p3)
    s5 = s4 + cp_g * np.log(t5 / t4) - r_g * np.log(p5 / p4)

    ideal_t5 = t4 / pressure_ratio**exponent_a
    ideal_s4 = cp_a * np.log(t4 / t3s)
    return {
        "gamma_a": gamma_a,
        "gamma_g": gamma_g,
        "cp_a": cp_a,
        "cp_g": cp_g,
        "pressure_ratio": pressure_ratio,
        "eta_c": eta_c,
        "eta_t": eta_t,
        "eta_m": eta_m,
        "burner_pressure_ratio": burner_pressure_ratio,
        "t2": t2,
        "t3s": t3s,
        "t3": t3,
        "t4": t4,
        "t5": t5,
        "t5s": t5s,
        "p2": p2,
        "p3": p3,
        "p4": p4,
        "p5": p5,
        "compressor_work": compressor_work,
        "real_entropy": [s2, s3, s4, s5],
        "ideal_temperature": [t2, t3s, t4, ideal_t5],
        "ideal_entropy": [0.0, s3s, ideal_s4, ideal_s4],
    }


def draw_brayton_map(output_dir: Path, source_dir: Path, qa_dir: Path) -> dict[str, float]:
    state = thermodynamic_states()
    fig = plt.figure(figsize=(7.20, 3.65), constrained_layout=True)
    grid = fig.add_gridspec(1, 2, width_ratios=[1.32, 1.0])
    ax = fig.add_subplot(grid[0, 0])

    ideal_s = np.asarray(state["ideal_entropy"], dtype=float)
    ideal_t = np.asarray(state["ideal_temperature"], dtype=float)
    ideal_s_closed = np.r_[ideal_s, ideal_s[0]]
    ideal_t_closed = np.r_[ideal_t, ideal_t[0]]
    ax.plot(ideal_s_closed, ideal_t_closed, color=COLORS["gray"], lw=1.6, ls="--", label="理想循环")

    real_s = np.asarray(state["real_entropy"], dtype=float)
    real_t = np.asarray([state["t2"], state["t3"], state["t4"], state["t5"]], dtype=float)
    real_s_closed = np.r_[real_s, real_s[0]]
    real_t_closed = np.r_[real_t, real_t[0]]
    ax.plot(real_s_closed, real_t_closed, color=COLORS["blue"], lw=2.2, label="含部件损失的示意循环")
    labels = ["2", "3", "4", "5"]
    for x, y, label in zip(real_s, real_t, labels):
        ax.scatter(x, y, s=28, color=COLORS["orange"], zorder=5, edgecolor="white", linewidth=0.6)
        ax.annotate(label, (x, y), xytext=(5, 4), textcoords="offset points", weight="bold")
    ax.annotate("压气机做功", xy=(real_s[1], real_t[1]), xytext=(0.12, 900),
                arrowprops=dict(arrowstyle="->", color=COLORS["gray"]), color=COLORS["navy"])
    ax.annotate("燃烧加热\n并伴随总压损失", xy=(real_s[2], real_t[2]), xytext=(0.48, 1160),
                arrowprops=dict(arrowstyle="->", color=COLORS["gray"]), color=COLORS["navy"], ha="center")
    ax.annotate("涡轮输出轴功", xy=(real_s[3], real_t[3]), xytext=(0.78, 820),
                arrowprops=dict(arrowstyle="->", color=COLORS["gray"]), color=COLORS["navy"], ha="center")
    ax.set_xlabel("相对比熵 s - s2  [kJ/(kg·K)]")
    ax.set_ylabel("总温 Tt  [K]")
    ax.set_title("a  Brayton 循环的理想化与真实偏离", loc="left", weight="bold")
    ax.grid(alpha=0.18)
    ax.legend(loc="upper left")
    ax.text(0.01, 0.02, "示意假设：πc=12，ηc=0.86，ηt=0.89，Tt4=1450 K",
            transform=ax.transAxes, color=COLORS["gray"], fontsize=7)

    ax2 = fig.add_subplot(grid[0, 1])
    pressure_ratios = np.linspace(1.2, 40.0, 320)
    ideal_efficiency = 1.0 - pressure_ratios ** (-(state["gamma_a"] - 1.0) / state["gamma_a"])
    ax2.plot(pressure_ratios, ideal_efficiency * 100.0, color=COLORS["orange"], lw=2.3)
    selected = np.asarray([2, 4, 8, 12, 20, 30, 40], dtype=float)
    selected_eff = 1.0 - selected ** (-(state["gamma_a"] - 1.0) / state["gamma_a"])
    ax2.scatter(selected, selected_eff * 100.0, color=COLORS["navy"], s=22, zorder=4)
    ax2.axvline(state["pressure_ratio"], color=COLORS["blue"], lw=1.1, ls=":")
    ax2.annotate("算例 πc=12", xy=(12, (1 - 12 ** (-2 / 7)) * 100), xytext=(18, 38),
                 arrowprops=dict(arrowstyle="->", color=COLORS["gray"]), color=COLORS["navy"])
    ax2.set_xlim(1, 41)
    ax2.set_ylim(0, 70)
    ax2.set_xlabel("压气机总压比 πc")
    ax2.set_ylabel("理想热效率 ηth  [%]")
    ax2.set_title("b  理想效率趋势不是实际推力结论", loc="left", weight="bold")
    ax2.grid(alpha=0.18)
    ax2.text(0.03, 0.04, "仅适用于定比热、无损失的简单 Brayton 循环；\n未包含有限 Tt4、部件效率、冷却、压力损失和重量。",
             transform=ax2.transAxes, color=COLORS["red"], fontsize=7.1)
    save_web_figure(fig, output_dir / "brayton-cycle-map", qa_dir)

    csv_path = source_dir / "brayton-efficiency-ideal.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["compressor_pressure_ratio", "ideal_thermal_efficiency", "assumption"])
        for ratio, efficiency in zip(selected, selected_eff):
            writer.writerow([f"{ratio:.0f}", f"{efficiency:.8f}", "gamma=1.4; ideal simple Brayton"])
    return {key: float(value) for key, value in state.items() if isinstance(value, (float, int, np.floating))}


def draw_station_map(output_dir: Path, state: dict[str, float], qa_dir: Path) -> None:
    fig = plt.figure(figsize=(7.20, 3.45), constrained_layout=True)
    grid = fig.add_gridspec(2, 1, height_ratios=[1.02, 1.0])
    ax = fig.add_subplot(grid[0, 0])
    ax.set_xlim(-0.2, 5.2)
    ax.set_ylim(-0.15, 1.25)
    ax.axis("off")

    components = [
        (0.00, 0.36, 0.62, 0.42, "进气道", COLORS["cyan"]),
        (0.88, 0.27, 0.90, 0.60, "压气机", COLORS["blue"]),
        (2.02, 0.32, 0.78, 0.50, "燃烧室", COLORS["orange"]),
        (3.06, 0.27, 0.82, 0.60, "涡轮", COLORS["red"]),
        (4.12, 0.36, 0.72, 0.42, "喷管", COLORS["green"]),
    ]
    for x, y, w, h, label, color in components:
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.05",
                                    facecolor=color, edgecolor="white", linewidth=1.2, alpha=0.92))
        ax.text(x + w / 2, y + h / 2, label, ha="center", va="center", color="white", weight="bold", fontsize=9)
    for left, right in [(0.62, 0.88), (1.78, 2.02), (2.80, 3.06), (3.88, 4.12)]:
        ax.add_patch(FancyArrowPatch((left, 0.57), (right, 0.57), arrowstyle="-|>", mutation_scale=12,
                                     color=COLORS["navy"], linewidth=1.6))
    station_x = [-0.06, 0.76, 1.90, 2.92, 4.00, 4.96]
    station_labels = ["0", "2", "3", "4", "5", "8"]
    for x, label in zip(station_x, station_labels):
        ax.text(x, 0.05, label, ha="center", va="center", weight="bold", color=COLORS["navy"])
        ax.plot([x, x], [0.13, 0.28], color=COLORS["gray"], lw=0.8)
    ax.add_patch(FancyArrowPatch((3.42, 0.98), (1.30, 0.98), arrowstyle="-|>", mutation_scale=12,
                                 color=COLORS["red"], linewidth=2.1, connectionstyle="arc3,rad=0.0"))
    ax.text(2.36, 1.07, "同轴功率：涡轮 → 压气机与附件", ha="center", color=COLORS["red"], weight="bold")
    ax.set_title("a  站位是部件接口；总参数是可比较的能量账本", loc="left", weight="bold")

    ax2 = fig.add_subplot(grid[1, 0])
    x = np.arange(6)
    total_temperature = np.asarray([288, 288, state["t3"], state["t4"], state["t5"], state["t5"]])
    total_pressure = np.asarray([1.0, 0.98, 0.98 * state["pressure_ratio"],
                                 0.98 * state["pressure_ratio"] * state["burner_pressure_ratio"],
                                 state["p5"] * 0.98, 1.0])
    temp_norm = total_temperature / total_temperature[0]
    press_norm = total_pressure / total_pressure[0]
    ax2.plot(x, temp_norm, color=COLORS["red"], lw=2.2, marker="o", label="总温 Tt / Tt0")
    ax2.plot(x, press_norm, color=COLORS["blue"], lw=2.2, marker="s", label="总压 Pt / Pt0")
    ax2.set_xticks(x, ["0 来流", "2 压气机前", "3 压气机后", "4 涡轮前", "5 涡轮后", "8 喷口"])
    ax2.set_ylabel("归一化总参数")
    ax2.set_title("b  算例的总温与总压沿程趋势（非真实发动机测试数据）", loc="left", weight="bold")
    ax2.set_yscale("log")
    ax2.set_ylim(0.8, 16)
    ax2.grid(alpha=0.18, which="both")
    ax2.legend(ncol=2, loc="upper right")
    ax2.text(0.01, 0.03, "喷管近似绝热：总温近似不变；总压换成速度与静压。燃烧室不“制造总压”。",
             transform=ax2.transAxes, fontsize=7.2, color=COLORS["gray"])
    save_web_figure(fig, output_dir / "engine-stations", qa_dir)


def draw_cover(output_dir: Path) -> None:
    fig, ax = plt.subplots(figsize=(12.8, 7.2))
    fig.patch.set_facecolor("#071521")
    ax.set_facecolor("#071521")
    ax.set_xlim(0, 12.8)
    ax.set_ylim(0, 7.2)
    ax.axis("off")
    for y in np.linspace(0.8, 6.4, 8):
        ax.plot([0.4, 12.4], [y, y], color="#15354a", lw=0.7, alpha=0.65)
    for x in np.linspace(0.8, 12.0, 15):
        ax.plot([x, x], [0.5, 6.7], color="#15354a", lw=0.7, alpha=0.65)
    blocks = [
        (0.9, 2.8, 1.55, 1.3, COLORS["cyan"]),
        (3.0, 2.3, 2.15, 2.3, COLORS["blue"]),
        (5.75, 2.55, 1.75, 1.8, COLORS["orange"]),
        (8.05, 2.3, 1.95, 2.3, COLORS["red"]),
        (10.55, 2.8, 1.35, 1.3, COLORS["green"]),
    ]
    for x, y, w, h, color in blocks:
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.04,rounding_size=0.12",
                                    facecolor=color, edgecolor="#d7ebf6", linewidth=1.4, alpha=0.92))
    for x0, x1 in [(2.45, 3.0), (5.15, 5.75), (7.5, 8.05), (10.0, 10.55)]:
        ax.add_patch(FancyArrowPatch((x0, 3.45), (x1, 3.45), arrowstyle="-|>", mutation_scale=18,
                                     color="#d7ebf6", linewidth=2.0))
    ax.add_patch(FancyArrowPatch((9.0, 5.25), (4.1, 5.25), arrowstyle="-|>", mutation_scale=17,
                                 color="#ffb45b", linewidth=2.8))
    for x, label in zip([0.7, 2.7, 5.45, 7.8, 10.3, 12.15], ["0", "2", "3", "4", "5", "8"]):
        ax.text(x, 1.65, label, color="#b8d5e5", fontsize=15, weight="bold", ha="center")
    ax.plot([0.75, 3.0, 5.75, 8.05, 10.55, 12.1], [1.2, 1.2, 2.0, 5.8, 4.5, 4.5],
            color="#ff866e", lw=3.0, marker="o", markersize=6)
    ax.plot([0.75, 3.0, 5.75, 8.05, 10.55, 12.1], [0.85, 0.82, 5.2, 4.9, 2.4, 0.85],
            color="#5bb9ef", lw=3.0, marker="s", markersize=5)
    out = output_dir / "aeroengine-brayton-cover.webp"
    fig.savefig(out, dpi=360, bbox_inches="tight", facecolor=fig.get_facecolor(), format="webp")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate aeroengine learning figures with Python/matplotlib.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--post-id", default="5d68a0e8")
    parser.add_argument("--qa-dir", type=Path, default=Path("tmp/aeroengine-figure-qa"))
    args = parser.parse_args()
    root = args.root.resolve()
    output_dir = root / "p" / args.post_id
    source_dir = root / "data" / "aeroengine"
    qa_dir = args.qa_dir if args.qa_dir.is_absolute() else root / args.qa_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    source_dir.mkdir(parents=True, exist_ok=True)
    qa_dir.mkdir(parents=True, exist_ok=True)
    configure_matplotlib()
    state = draw_brayton_map(output_dir, source_dir, qa_dir)
    draw_station_map(output_dir, state, qa_dir)
    draw_cover(output_dir)
    notes = {
        "briefing": 1,
        "backend": "Python/matplotlib",
        "coreConclusion": "压气机功、涡轮功与喷管剩余能量必须共同平衡，单独提高压气机总压比不能代表发动机更好。",
        "assumptions": {
            "compressorPressureRatio": state["pressure_ratio"],
            "compressorEfficiency": state["eta_c"],
            "turbineEfficiency": state["eta_t"],
            "mechanicalEfficiency": state["eta_m"],
            "burnerTotalPressureRatio": state["burner_pressure_ratio"],
            "turbineInletTotalTemperatureK": state["t4"],
            "variableCp": False,
            "coolingBleedAccessoryLoads": "omitted in the simplified numerical example",
        },
        "derived": {
            "compressorExitIsentropicK": round(state["t3s"], 2),
            "compressorExitActualK": round(state["t3"], 2),
            "compressorSpecificWorkKJkg": round(state["compressor_work"], 2),
            "turbineExitTotalTemperatureK": round(state["t5"], 2),
            "turbineExitTotalPressureRatioToAmbient": round(state["p5"], 3),
        },
        "integrity": "原创工程示意；曲线由列明公式和假设生成，不是实测发动机数据。",
    }
    (source_dir / "brayton-briefing-01-figure-notes.json").write_text(
        json.dumps(notes, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(notes, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
