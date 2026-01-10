import matplotlib.pyplot as plt


DATA = {
    "1-5": 12 + 65 + 50 + 52 + 3,
    "6-10": 52 + 46 + 5,
    "11-20": 12 + 2,
    "21+": 5 + 7,
}

assert sum(DATA.values()) == 311, "Total number of queries is not 311"

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

COLOR = COLORS[1]


def plot_num_query_distribution():
    fig = plt.Figure(figsize=(3.75, 3.25))

    ax1 = fig.add_subplot(1, 1, 1)

    query_ranges = list(DATA.keys())
    counts = list(DATA.values())

    x_positions = range(len(query_ranges))
    ax1.bar(x_positions, counts, color=COLOR, edgecolor="#6e6e6e", linewidth=0)

    ax1.set_xlim(-0.5, len(query_ranges) - 0.5)
    ax1.set_ylim(0, max(counts) * 1.1)

    ax1.set_xticks(x_positions)
    ax1.set_xticklabels(query_ranges)

    ax1.set_yticks([0, 50, 100, 150, 200])
    ax1.set_yticklabels(["0", "50", "100", "150", "200"])

    ax1.set_xlabel("Number of Queries")
    ax1.set_ylabel("Number of Questions")

    ax1.grid(color="#d6d6d6", axis="y", alpha=0.7)
    # ax1.grid(color="#d6d6d6", axis="y")
    ax1.spines["bottom"].set_color("#6e6e6e")
    ax1.spines["top"].set_color("#6e6e6e")
    ax1.spines["right"].set_color("#6e6e6e")
    ax1.spines["left"].set_color("#6e6e6e")
    ax1.tick_params(length=0)
    ax1.set_axisbelow(True)

    output_path = "figures/num_query_distribution.png"

    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    fig.savefig(output_path.replace(".png", ".pdf"), bbox_inches="tight")
    print(f"Saved figure to {output_path}")


if __name__ == "__main__":
    plot_num_query_distribution()
