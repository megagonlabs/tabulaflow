import matplotlib.pyplot as plt
import numpy as np

category_names = [
    "Invalid Output",
    "Not Executable",
    "Executable but Matches no Gold SQL",
    "Matches a Non-intended SQL",
    "Correct (Matches the Intended SQL)",
]


results = {
    "gpt-oss-20b": [0.8199, 0, 0.0868, 0.0193, 0.074],
    "gpt-oss-120b": [0.2508, 0.0129, 0.2862, 0.1897, 0.2605],
    "qwen3-8b": [0.164, 0.1318, 0.5209, 0.1254, 0.0579],
    "qwen3-235b-a22b-instruct-2507": [0.0547, 0.0322, 0.492, 0.2186, 0.2026],
    "qwen3-coder-480b": [0.1833, 0.0322, 0.4084, 0.2186, 0.1576],
    "deepseek-v3.1": [0.135, 0.0257, 0.4148, 0.1897, 0.2347],
    "deepseek-r1-0528": [0.0064, 0.0257, 0.5209, 0.2154, 0.2315],
    "kimi-k2-thinking": [0.2572, 0.0161, 0.3441, 0.1897, 0.1929],
    "gemini-2.5-flash": [0.0322, 0.0193, 0.4695, 0.2026, 0.2765],
    "gemini-2.5-pro": [0.0032, 0.0257, 0.4952, 0.1672, 0.3087],
    "gemini-3-pro-preview (high)": [0.0161, 0.0129, 0.3312, 0.1994, 0.4405],
    "claude-haiku-4.5 (high)": [0.0193, 0.0225, 0.4212, 0.2508, 0.2862],
    "claude-sonnet-4.5 (high)": [0, 0, 0.3762, 0.1865, 0.4373],
    "claude-opus-4.5 (high)": [0.1672, 0, 0.283, 0.164, 0.3859],
    "gpt-4.1-nano": [0.1125, 0.0804, 0.6174, 0.119, 0.0707],
    "gpt-4.1-mini": [0, 0.045, 0.5113, 0.2251, 0.2186],
    "gpt-4.1": [0, 0.0322, 0.4373, 0.2315, 0.299],
    "o4-mini (low)": [0, 0.0225, 0.4084, 0.209, 0.3601],
    "o4-mini (medium)": [0, 0.0257, 0.3762, 0.1736, 0.4244],
    "o4-mini (high)": [0, 0.0193, 0.3408, 0.1994, 0.4405],
    "gpt-5-nano (medium)": [0.0032, 0.0354, 0.4534, 0.2154, 0.2926],
    "gpt-5-mini (medium)": [0, 0.0354, 0.3698, 0.1511, 0.4437],
    "gpt-5 (minimal)": [0, 0.0032, 0.4084, 0.2122, 0.3762],
    "gpt-5 (low)": [0, 0.0289, 0.328, 0.1576, 0.4855],
    "gpt-5 (medium)": [0, 0.0193, 0.299, 0.1029, 0.5788],
    "gpt-5 (high)": [0, 0.0257, 0.3119, 0.0868, 0.5756],
}

# sum to 1
for model in results.values():
    assert abs(sum(model) - 1) < 1e-3, f"Model {model} sum to {sum(model)}"

assert all(len(v) == len(category_names) for v in results.values()), (
    "All models must have the same number of categories"
)


def main():
    labels = list(results.keys())
    data = np.array(list(results.values()))
    # category_colors = plt.colormaps["RdYlGn"](np.linspace(0.15, 0.85, data.shape[1]))
    # category_colors = plt.colormaps["Set3"](np.linspace(0, 1, len(category_names)))
    # category_colors = plt.colormaps["Paired"](np.linspace(0, 1, len(category_names)))
    # # category_colors = plt.colormaps['Accent'](np.linspace(0, 1, len(category_names)))

    # category_colors = np.concatenate(
    #     (
    #         category_colors[4:5],
    #         category_colors[:4],
    #         category_colors[5:],
    #     ),
    #     axis=0,
    # )

    category_colors = [
        (0.839, 0.153, 0.157, 1.0),  # Rich red - Invalid Output
        (0.957, 0.643, 0.376, 1.0),  # Warm coral - Not Executable
        (0.992, 0.906, 0.667, 1.0),  # Soft gold - Executable but Matches no Gold SQL
        (0.698, 0.875, 0.541, 1.0),  # Sage green - Matches a Non-intended SQL
        (0.302, 0.686, 0.290, 1.0),  # Luxurious emerald green - Correct
    ]
    category_colors = [
        (145/255, 113/255, 224/255, 1.0),  # Purple
        (0.85, 0.85, 0.85, 1.0),  # Dark Grey
        (233/255, 158/255, 122/255, 1.0),  # Light Orange
        (193/255, 225/255, 193/255, 1.0),  # Light Green
        (163/255, 194/255, 65/255, 1.0),  # Green        
    ]

    # Generate LaTeX color definitions
    latex_colors = []
    for name, color in zip(category_names, category_colors):
        r, g, b, _ = color  # Extract RGBA values
        latex_color = f"\\definecolor{{{name.replace(' ', '').replace('/', '').replace('-', '').lower()}}}{{rgb}}{{{r:.3f}, {g:.3f}, {b:.3f}}}"
        latex_colors.append(latex_color)

    # Output LaTeX color definitions
    for latex_color in latex_colors:
        print(latex_color)

    fig = plt.figure(figsize=(11.5, 20))

    ax = fig.add_subplot(111)
    ax.invert_yaxis()
    ax.xaxis.set_visible(False)
    ax.set_xlim(0, np.sum(data, axis=1).max())
    ax.set_ylim(len(labels) - 0.5, -0.5)

    for model_idx, model_name in enumerate(labels):
        cumulative_width = 0
        for category_idx, (colname, color) in enumerate(zip(category_names, category_colors)):
            width = data[model_idx][category_idx]
            if width == 0:
                continue
            rect = ax.barh(
                model_name,
                width,
                left=cumulative_width,
                height=0.5,
                color=color,
                label=colname if model_idx == 1 else None,  # Only add labels once for the legend
            )

            r, g, b, _ = color
            text_color = "white" if r * g * b < 0.5 else "darkgrey"

            # Format label: 0.23 -> 23%, 0.057 -> 6%
            if width >= 0.01:
                label = f"{width * 100:.0f}%"
            else:
                label = f"{width * 100:.1f}%"

            if width > 0.02:
                ax.bar_label(rect, labels=[label], label_type="center", color=text_color)

            cumulative_width += width

    ax.spines["top"].set_color("white")
    ax.spines["right"].set_color("white")
    ax.spines["bottom"].set_color("white")
    ax.spines["left"].set_color("gray")
    ax.tick_params(axis="x", colors="gray")
    ax.tick_params(axis="y", colors="gray")
    ax.tick_params(axis="x", labelcolor="black")
    ax.tick_params(axis="y", labelcolor="black")

    legend = ax.legend(ncols=3, bbox_to_anchor=(0, 1.02), loc="lower left")

    frame = legend.get_frame()
    frame.set_linewidth(1.5)
    frame.set_facecolor("#f0f0f0")
    frame.set_edgecolor("#888888")
    # make corner rounder
    frame.set_boxstyle("round,pad=0.1,rounding_size=0.5")

    fig.savefig("figures/error_distribution_all.png", dpi=300, bbox_inches="tight")
    fig.savefig("figures/error_distribution_all.pdf", bbox_inches="tight")
    print("Saved plot to figures/error_distribution_all.png")


if __name__ == "__main__":
    main()
