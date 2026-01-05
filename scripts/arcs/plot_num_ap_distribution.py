import numpy as np
import matplotlib.pyplot as plt


DATA = {
    1: 107,
    2: 109,
    3: 75,
    4: 14,
    5: 6,
}
COLORS = [
    "#9B59B6",  # Vibrant purple
    "#D81B60",  # Vibrant pink
    "#16A085",  # Vibrant teal
]

COLORS = [
    "#16A085",  # Vibrant teal
    "#9B59B6",  # Vibrant purple
    "#B84821",  # Red brick
]

COLORS = [
    (163 / 255, 194 / 255, 65 / 255, 1.0),  # Green
    (233 / 255, 158 / 255, 122 / 255, 1.0),  # Light Orange
    (145 / 255, 113 / 255, 224 / 255, 1.0),  # Purple
]

COLOR = COLORS[2]


def plot_num_ap_distribution():
    fig = plt.Figure(figsize=(3.75, 3))

    ax1 = fig.add_subplot(1, 1, 1)

    num_aps = list(DATA.keys())
    counts = list(DATA.values())

    ax1.bar(num_aps, counts, color=COLOR, edgecolor="#6e6e6e", linewidth=0.5)

    ax1.set_xlim(0.5, 5.5)
    ax1.set_ylim(0, max(counts) * 1.1)

    ax1.set_xticks(num_aps)
    ax1.set_xticklabels([str(x) for x in num_aps])

    ax1.set_xlabel("Number of Ambiguity Points")
    ax1.set_ylabel("Number of Questions")

    ax1.grid(color="#d6d6d6", axis="y", alpha=0.7)
    # ax1.grid(color="#d6d6d6", axis="y")
    ax1.spines["bottom"].set_color("#6e6e6e")
    ax1.spines["top"].set_color("#6e6e6e")
    ax1.spines["right"].set_color("#6e6e6e")
    ax1.spines["left"].set_color("#6e6e6e")
    ax1.tick_params(length=0)
    ax1.set_axisbelow(True)

    output_path = "figures/num_ap_distribution.png"

    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    fig.savefig(output_path.replace(".png", ".pdf"), bbox_inches="tight")
    print(f"Saved figure to {output_path}")


if __name__ == "__main__":
    plot_num_ap_distribution()
