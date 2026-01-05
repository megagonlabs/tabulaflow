import matplotlib.pyplot as plt
import numpy as np
from matplotlib.font_manager import FontProperties
from matplotlib.colors import rgb_to_hsv, hsv_to_rgb


def increase_saturation(colors, factor=1.5):
    saturated_colors = []
    for color in colors:
        rgb = color[:3]  # Ignore alpha channel
        hsv = rgb_to_hsv(rgb)
        hsv[1] = min(1, hsv[1] * factor)  # Increase saturation, max out at 1
        saturated_rgb = hsv_to_rgb(hsv)
        saturated_colors.append((*saturated_rgb, color[3]))  # Add alpha channel back
    return np.array(saturated_colors)


def plot_domain_distribution():
    fig = plt.Figure(figsize=(3.75, 3))
    ax = fig.add_subplot(1, 1, 1)

    domains = ["retails", "professional_basketball", "github_repos", "financial", "codebase_community", "student_club"]
    counts = {
        "retails": 84,
        "basketball": 34,
        "github_repos": 71,
        "financial": 41,
        "codebase_community": 36,
        "student_club": 45,
    }

    font_properties = FontProperties(family="monospace")

    colors = plt.colormaps["Set3"](np.linspace(0, 1, len(counts)))
    # set color of codebase_community to purple
    # colors[4] = (145 / 255, 113 / 255, 224 / 255, 1.0)
    # set color of basketball to light orange
    colors[1] = (233 / 255, 158 / 255, 122 / 255, 1.0)

    # Increase saturation of the colors
    colors = increase_saturation(colors, factor=1.3)
    colors = colors[:, :3] * 0.95
    # colors = plt.colormaps['Paired'](np.linspace(0, 1, len(counts)))

    # colors = CMAP_BASIC(np.linspace(0.7, 0.4, 6))
    wedges, texts = ax.pie(
        counts.values(),
        labels=None,
        wedgeprops=dict(edgecolor="w", width=1.2),
        colors=colors,
        textprops={"fontproperties": font_properties},
        startangle=0,
        radius=1.2,
        labeldistance=0.2,
        rotatelabels=True,
    )

    # for t in texts:
    #     # right-aligned
    #     t.set_horizontalalignment('center')

    # Calculate and place the labels with rotation
    for wedge, label in zip(wedges, counts.keys()):
        # Midpoint angle of each wedge
        angle = (wedge.theta2 + wedge.theta1) / 2  # In degrees
        x = 1.15 * np.cos(np.radians(angle))  # Radius = 1.0 (outer edge of the pie)
        y = 1.15 * np.sin(np.radians(angle))

        # Determine horizontal alignment
        if angle > 90 and angle < 270:  # Left side of the pie
            ha = "left"
            rotation = angle + 180  # Rotate for the left side
        else:  # Right side of the pie
            ha = "right"
            rotation = angle  # Keep rotation as is for the right side

        # Add rotated text
        ax.text(
            x,
            y,
            label.replace("_", " "),  # Label text
            ha=ha,
            va="center",  # Align horizontally and vertically
            fontsize=12 if len(label) < 10 else (8 if len(label) < 15 else 6),  # Reduce font size for longer labels
            weight="bold",
            color="white",
            fontproperties=font_properties,
            rotation=rotation,  # Apply the calculated rotation
            rotation_mode="anchor",  # Rotate around the anchor point
        )

    output_path = "figures/domain_distribution.png"
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    fig.savefig(output_path.replace(".png", ".pdf"), bbox_inches="tight")
    print(f"Saved figure to {output_path}")


if __name__ == "__main__":
    plot_domain_distribution()
