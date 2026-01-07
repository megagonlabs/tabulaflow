import matplotlib.pyplot as plt
import numpy as np
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from PIL import Image
from matplotlib.patches import Circle, RegularPolygon
from matplotlib.path import Path
from matplotlib.projections import register_projection
from matplotlib.projections.polar import PolarAxes
from matplotlib.spines import Spine
from matplotlib.transforms import Affine2D


def radar_factory(num_vars, frame="circle"):
    """
    Create a radar chart with `num_vars` Axes.

    This function creates a RadarAxes projection and registers it.

    Parameters
    ----------
    num_vars : int
        Number of variables for radar chart.
    frame : {'circle', 'polygon'}
        Shape of frame surrounding Axes.

    """
    # calculate evenly-spaced axis angles
    theta = np.linspace(0, 2 * np.pi, num_vars, endpoint=False)

    class RadarTransform(PolarAxes.PolarTransform):
        def transform_path_non_affine(self, path):
            # Paths with non-unit interpolation steps correspond to gridlines,
            # in which case we force interpolation (to defeat PolarTransform's
            # autoconversion to circular arcs).
            if path._interpolation_steps > 1:
                path = path.interpolated(num_vars)
            return Path(self.transform(path.vertices), path.codes)

    class RadarAxes(PolarAxes):
        name = "radar"
        PolarTransform = RadarTransform

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            # rotate plot such that the first axis is at the top
            self.set_theta_zero_location("N")

        def fill(self, *args, closed=True, **kwargs):
            """Override fill so that line is closed by default"""
            return super().fill(closed=closed, *args, **kwargs)

        def plot(self, *args, **kwargs):
            """Override plot so that line is closed by default"""
            lines = super().plot(*args, **kwargs)
            for line in lines:
                self._close_line(line)

        def _close_line(self, line):
            x, y = line.get_data()
            # FIXME: markers at x[0], y[0] get doubled-up
            if x[0] != x[-1]:
                x = np.append(x, x[0])
                y = np.append(y, y[0])
                line.set_data(x, y)

        def set_varlabels(self, labels):
            self.set_thetagrids(np.degrees(theta), labels)

        def _gen_axes_patch(self):
            # The Axes patch must be centered at (0.5, 0.5) and of radius 0.5
            # in axes coordinates.
            if frame == "circle":
                return Circle((0.5, 0.5), 0.5)
            elif frame == "polygon":
                return RegularPolygon((0.5, 0.5), num_vars, radius=0.5, edgecolor="k")
            else:
                raise ValueError("Unknown value for 'frame': %s" % frame)

        def _gen_axes_spines(self):
            if frame == "circle":
                return super()._gen_axes_spines()
            elif frame == "polygon":
                # spine_type must be 'left'/'right'/'top'/'bottom'/'circle'.
                spine = Spine(axes=self, spine_type="circle", path=Path.unit_regular_polygon(num_vars))
                spine.set_edgecolor("gray")
                spine.set_linestyle((0, (3, 2.5)))
                # spine.set_linestyle('--')
                spine.set_linewidth(0.5)
                # unit_regular_polygon gives a polygon of radius 1 centered at
                # (0, 0) but we want a polygon of radius 0.5 centered at (0.5,
                # 0.5) in axes coordinates.
                spine.set_transform(Affine2D().scale(0.5).translate(0.5, 0.5) + self.transAxes)
                return {"polar": spine}
            else:
                raise ValueError("Unknown value for 'frame': %s" % frame)

    register_projection(RadarAxes)
    return theta


MODELS = ["qwen3-coder-480b", "gpt-4.1", "o4-mini (medium)"]

# | Method                                   |   semantic_column |   semantic_table |   semantic_value |   semantic_computation |   syntactic_column |   syntactic_table |   syntactic_value |   syntactic_computation |
# | qwen3-coder-480b_structured              |            0.3762 |           0.5086 |           0.6875 |                 0.169  |             0      |            0.0588 |            0.4167 |                  0.0893 |
# | gpt-4.1_structured                       |            0.604  |           0.8534 |           0.8167 |                 0.4014 |             0.3333 |            0.7647 |            0.6667 |                  0.2857 |
# | o4-mini-medium_structured                |            0.8218 |           0.8879 |           0.9437 |                 0.7007 |             0.8333 |            0.8824 |            0.8333 |                  0.6607 |
DATA = [
    (
        "EX Across RETURN templates",  # n_name	n_prop_combined	n_order_by	n_argmax	n_where	n_agg
        [
            "Semantic Column",
            "Semantic Table",
            "Semantic Value",
            "Semantic Computation",
            "Syntactic Column",
            "Syntactic Table",
            "Syntactic Value",
            "Syntactic Computation",
        ],
        [
            [0.3762, 0.5086, 0.6875, 0.169, 0, 0.0588, 0.4167, 0.0893],
            [0.604, 0.8534, 0.8167, 0.4014, 0.3333, 0.7647, 0.6667, 0.2857],
            [0.8218, 0.8879, 0.9437, 0.7007, 0.8333, 0.8824, 0.8333, 0.6607],
        ],
    )
]

if __name__ == "__main__":
    # theta = radar_factory(len(DATA[0][1]), frame='polygon')

    fig = plt.figure(figsize=(4, 4), dpi=300)

    # fig, axs = plt.subplots(figsize=(9, 9), nrows=2, ncols=2,
    #                         subplot_kw=dict(projection='radar'))
    # axs = fig.subplots(2, 2, subplot_kw=dict(projection='radar'))
    # fig.subplots_adjust(wspace=0.25, hspace=0.20, top=0.85, bottom=0.05)

    # colors = ['b', 'r', 'g', 'm', 'y']
    # colors = ["#a56cbd", "#53c2a2", "#4892bd", "#fe7f2d", "#fcca46"]

    colors = [
        (163/255, 194/255, 65/255, 1.0),  # Green      
        (233/255, 158/255, 122/255, 1.0),  # Light Orange
        (145/255, 113/255, 224/255, 1.0),  # Purple  
    ]

    # Plot the four cases from the example data on separate Axes
    axs = []
    for i, (title, variables, case_data) in enumerate(DATA):
        theta = radar_factory(len(variables), frame="polygon")
        ax = fig.add_subplot(1, 1, i + 1, projection="radar")
        axs.append(ax)
        # ax.set_rgrids([0.2, 0.4, 0.6, 0.8])
        ax.set_ylim(0, 1)
        ax.set_yticks([0.2, 0.4, 0.6, 0.8])
        ax.set_yticklabels(["0.2", "0.4", "0.6", "0.8"], color="gray", size="small")
        # ax.set_title(title, weight='bold', size='medium', position=(0.5, 1.1),
        # horizontalalignment='center', verticalalignment='center')
        # ax.set_title(title, weight="bold")
        ax.xaxis.grid(color="gray", linestyle="solid", linewidth=0.5)
        ax.yaxis.grid(color="gray", linestyle="--", linewidth=0.5)
        ax.tick_params(pad=5)
        for d, color in zip(case_data, colors):
            ax.plot(theta, d, color=color, linewidth=1.5)
            ax.fill(theta, d, facecolor=color, alpha=0.25, label="_nolegend_")
            if "Basic MATCH" not in title:
                ax.set_varlabels(variables)
            else:
                ax.set_varlabels([" "] * len(variables))

        if "Basic MATCH" not in title:
            continue

        radar_position = ax.get_position()
        if i == 0:
            x_shift = -0.025  # Shift left by 5% of figure width
            y_shift = -0.077  # Shift down by 5% of figure height
        else:
            x_shift = -0.025  # Shift left by 5% of figure width
            y_shift = -0.015  # Shift down by 5% of figure height
        radar_position = [
            radar_position.x0 + x_shift,
            radar_position.y0 + y_shift,
            radar_position.width,  # Keep the width the same
            radar_position.height,  # Keep the height the same
        ]
        ax = fig.add_axes(radar_position, frameon=True)
        ax.set_xlim(-1, 1)
        ax.set_ylim(-1, 1)
        ax.axis("off")

        # for idx, angle in enumerate(theta):
        #     # Midpoint angle of each wedge
        #     # print(angle)
        #     x = 0.9 * np.cos(angle + np.pi / 2)  # Radius = 0.5 for positioning
        #     y = 0.9 * np.sin(angle + np.pi / 2)

        #     img_path = f"plots/basic_{idx + 1}.png"

        #     img = Image.open(img_path)

        #     # Load and prepare the image
        #     zoom = 0.07
        #     # Adjust zoom to scale image
        #     # image_width, image_height = img.size
        #     # scaled_width = image_width * zoom  # Adjust width according to scaling
        #     #
        #     # # Determine offset dynamically based on scaled width
        #     # if 90 < angle < 270:  # Left side of the pie
        #     #     offset = (-scaled_width / 2 - 3, 0)  # Offset to the left
        #     # else:  # Right side of the pie
        #     #     offset = (scaled_width / 2 + 3, 0)  # Offset to the right

        #     imagebox = OffsetImage(img, zoom=zoom)
        #     ab = AnnotationBbox(
        #         imagebox,
        #         (x, y),  # Position of the image
        #         # xybox=offset,  # Offset for alignment
        #         xycoords="data",
        #         boxcoords="offset points",
        #         pad=0,
        #         frameon=False,  # Remove frame around the image,
        #         clip_on=False,
        #     )
        #     # ab = AnnotationBbox(imagebox, (angle, 1.05), frameon=False, box_alignment=(0.5, 0.5), clip_on=False)
        #     # Add image to the plot
        #     ax.add_artist(ab)

    fig.subplots_adjust(wspace=0.7, hspace=-0.2, top=0.85, bottom=0.05)

    # add legend relative to top-left plot
    # legend = axs[0].legend(MODELS, loc=(0.9, .95),
    #                           labelspacing=0.1, fontsize='small')

    # legend = axs[1].legend(MODELS, loc='upper left', bbox_to_anchor=(1.2, 1.1),
    #                        labelspacing=0.2, fontsize='medium', markerscale=1.5, frameon=True)
    # legend = axs[1].legend(MODELS, loc='upper left', bbox_to_anchor=(1.4, 1.1), frameon=True)
    # legend = axs[1].legend(MODELS, loc='bottom right', bbox_to_anchor=(2, 1.5), ncol=len(MODELS), frameon=True)
    legend = axs[0].legend(MODELS, loc="upper right", bbox_to_anchor=(1.9, 1.0), ncol=1, frameon=True)

    for legobj in legend.legend_handles:
        legobj.set_linewidth(3)

    frame = legend.get_frame()
    frame.set_linewidth(1.5)
    frame.set_facecolor("#f0f0f0")
    frame.set_edgecolor("#888888")
    # make corner rounder
    frame.set_boxstyle("round,pad=0.1,rounding_size=0.5")

    # fig.text(0.5, 0.965, '5-Factor Solution Profiles Across Four Scenarios',
    #          horizontalalignment='center', color='black', weight='bold',
    #          size='large')

    fig.savefig("figures/result_by_ambig_type.png", bbox_inches="tight", dpi=300)
    print(f"Saved plot to figures/result_by_ambig_type.png")
    fig.savefig("figures/result_by_ambig_type.pdf", bbox_inches="tight")
    print(f"Saved plot to figures/result_by_ambig_type.pdf")
