import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Patch


def plot_ambig_type_distribution():
    fig = plt.Figure(figsize=(7.5, 6))
    ax = fig.add_subplot(1, 1, 1)

    counts = {
        "semantic_column": 107,
        "semantic_table": 62,
        "semantic_value": 187,
        "semantic_computation": 189,
        "syntactic_column": 6,
        "syntactic_table": 17,
        "syntactic_value": 12,
        "syntactic_computation": 56,
    }

    colors = {
        "semantic": "#74aa9b",
        "syntactic": "#f8c6a6",
        "column": "#4571c4",
        "table": "#ee7d31",
        "value": "#70ad47",
        "computation": "#ffc001",
    }
    # colors = {
    #     "semantic": "#8ab9ad",
    #     "syntactic": "#f9d4bb",
    #     "column": "#6b8fd4",
    #     "table": "#f29a5a",
    #     "value": "#8fbd6f",
    #     "computation": "#ffcd33",
    # }

    font_properties = FontProperties(family="monospace")

    n_semantic = sum([v for k, v in counts.items() if "semantic" in k])
    n_syntactic = sum([v for k, v in counts.items() if "syntactic" in k])

    # Inner pie chart (semantic vs syntactic)
    # colors_inner = [plt.colormaps["Set3"](0.4), plt.colormaps["Set3"](0.6)]
    # colors_inner[0] = colors_inner[0][:3] + (0.9,)
    # colors_inner[1] = colors_inner[1][:3] + (0.9,)
    colors_inner = [colors["semantic"], colors["syntactic"]]
    wedges, texts, autotexts = ax.pie(
        [n_semantic, n_syntactic],
        radius=0.6,
        wedgeprops=dict(edgecolor="w"),
        colors=colors_inner,
        textprops={"fontproperties": font_properties},
        startangle=0,
        autopct=lambda pct: "Semantic" if pct > 50 else "Syntactic",
    )
    for i, t in enumerate(autotexts):
        t.set_color("w")
        t.set_fontweight("bold")
        t.set_fontsize(16 if i == 0 else 8)
        if i == 0:
            t.set_position((t.get_position()[0] + 0.3, t.get_position()[1]))
        else:
            t.set_position((t.get_position()[0], t.get_position()[1] + 0.06))

    # Outer pie chart (detailed breakdown)
    # Define base colors for each category type
    # base_colors = plt.colormaps["Set3"](np.linspace(0.3, 0.7, 4))

    # Create colors for outer ring: semantic uses base colors, syntactic uses same base colors
    colors_outer = [colors["column"], colors["table"], colors["value"], colors["computation"]]

    # labels_dict = {
    #     "semantic_column": "column",
    #     "semantic_table": "table",
    #     "semantic_value": "value",
    #     "semantic_computation": "computation",
    #     "syntactic_column": "column",
    #     "syntactic_table": "table",
    #     "syntactic_value": "value",
    #     "syntactic_computation": "computation",
    # }

    wedges, texts = ax.pie(
        counts.values(),
        radius=1.0,
        labels=None,
        colors=colors_outer,
        wedgeprops=dict(edgecolor="w", width=0.4),
        # textprops={"fontproperties": font_properties, "color": "#333333", "fontsize": 6},
        startangle=0,
        labeldistance=1.15,
    )

    # Create first legend for semantic vs syntactic
    legend_semantic_syntactic = [
        Patch(facecolor=colors["semantic"], edgecolor="w", label="semantic"),
        Patch(facecolor=colors["syntactic"], edgecolor="w", label="syntactic"),
    ]
    legend1 = ax.legend(
        handles=legend_semantic_syntactic,
        loc="upper left",
        bbox_to_anchor=(1, 0.9),
        prop=font_properties,
        frameon=True,
    )

    # Create second legend for category types
    # legend_categories = [
    #     Patch(facecolor=colors["column"], edgecolor="w", label="column"),
    #     Patch(facecolor=colors["table"], edgecolor="w", label="table"),
    #     Patch(facecolor=colors["value"], edgecolor="w", label="value"),
    #     Patch(facecolor=colors["computation"], edgecolor="w", label="computation"),
    # ]
    # legend2 = ax.legend(
    #     handles=legend_categories,
    #     loc="upper left",
    #     bbox_to_anchor=(1, 0.75),
    #     prop=font_properties,
    #     frameon=True,
    # )

    # Add the first legend back (matplotlib removes it when creating the second)
    ax.add_artist(legend1)

    output_path = "figures/ambig_type_distribution.png"
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    fig.savefig(output_path.replace(".png", ".pdf"), bbox_inches="tight")
    print(f"Saved figure to {output_path}")


if __name__ == "__main__":
    plot_ambig_type_distribution()
