import matplotlib.pyplot as plt
import numpy as np
from matplotlib.font_manager import FontProperties


def plot_ambig_type_distribution():
    fig = plt.Figure(figsize=(3.75, 3))
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

    font_properties = FontProperties(family="monospace")

    n_semantic = sum([v for k, v in counts.items() if "semantic" in k])
    n_syntactic = sum([v for k, v in counts.items() if "syntactic" in k])

    # Inner pie chart (semantic vs syntactic)
    colors_inner = [plt.colormaps["Set3"](0.4), plt.colormaps["Set3"](0.6)]
    colors_inner[0] = colors_inner[0][:3] + (0.9,)
    colors_inner[1] = colors_inner[1][:3] + (0.9,)
    wedges, texts, autotexts = ax.pie(
        [n_semantic, n_syntactic],
        radius=0.7,
        wedgeprops=dict(edgecolor="w"),
        colors=colors_inner,
        textprops={"fontproperties": font_properties},
        startangle=0,
        autopct=lambda pct: "semantic" if pct > 50 else "syntactic",
    )
    for t in autotexts:
        t.set_color("w")
        t.set_fontweight("bold")
        t.set_fontsize(6)

    # Outer pie chart (detailed breakdown)
    colors_semantic = plt.colormaps["Set3"](np.linspace(0.3, 0.5, 4))
    colors_syntactic = plt.colormaps["Set3"](np.linspace(0.5, 0.7, 4))
    colors_outer = np.concatenate([colors_semantic, colors_syntactic])
    colors_outer[:, 3] = 0.9

    labels_dict = {
        "semantic_column": "column",
        "semantic_table": "table",
        "semantic_value": "value",
        "semantic_computation": "computation",
        "syntactic_column": "column",
        "syntactic_table": "table",
        "syntactic_value": "value",
        "syntactic_computation": "computation",
    }

    wedges, texts = ax.pie(
        counts.values(),
        radius=1.0,
        labels=[labels_dict[k] for k in counts.keys()],
        colors=colors_outer,
        wedgeprops=dict(edgecolor="w", width=0.3),
        textprops={"fontproperties": font_properties, "color": "#333333", "fontsize": 6},
        startangle=0,
        labeldistance=1.15,
    )

    output_path = "figures/ambig_type_distribution.png"
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    fig.savefig(output_path.replace(".png", ".pdf"), bbox_inches="tight")
    print(f"Saved figure to {output_path}")


if __name__ == "__main__":
    plot_ambig_type_distribution()
