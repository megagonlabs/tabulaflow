import numpy as np
import matplotlib.pyplot as plt



DATA = {
    "Conversational": [0.6355, 0.4037, 0.2526],
    "Unstructured": [0.5327, 0.1927, 0.1263],
    "Structured": [0.5981, 0.3761, 0.2842],
}
COLORS = [
    '#9B59B6',  # Vibrant purple
    '#D81B60',  # Vibrant pink
    '#16A085',  # Vibrant teal
]

COLORS = [
    '#16A085',  # Vibrant teal
    '#9B59B6',  # Vibrant purple
    '#B84821',  # Red brick
]

def plot_ex_by_num_ap():
    fig = plt.Figure(figsize=(3.75, 3))

    ax1 = fig.add_subplot(1, 1, 1)
    num_aps = [1, 2, 3]
    for i, (label, data) in enumerate(DATA.items()):
        ax1.scatter(num_aps, data, color=COLORS[i], zorder=3)
        ax1.plot(num_aps, data, color=COLORS[i], label=label)

    ax1.legend()
    ax1.set_xlim(0.8, 3.2)
    ax1.set_ylim(0.0, 0.7)
    # ax1.set_ylim(min(DATA.values()), max(DATA.values()))
    # ax1.tick_params(axis="y", direction="in", pad=6)
    # ax1.tick_params(axis="x", direction="in", pad=6)
    ax1.set_xticks(num_aps)
    ax1.set_yticks([0.0, 0.2, 0.4, 0.6, 0.7])

    ax1.set_xlabel('Number of Ambiguous Points')
    ax1.set_ylabel('EX')

    ax1.set_xticklabels(["1", "2", "3+"])
    ax1.set_yticklabels(["0.0", "0.2", "0.4", "0.6", "0.7"])

    ax1.grid(color='#d6d6d6')
    ax1.spines['bottom'].set_color('#6e6e6e')
    ax1.spines['top'].set_color('#6e6e6e')
    ax1.spines['right'].set_color('#6e6e6e')
    ax1.spines['left'].set_color('#6e6e6e')
    ax1.tick_params(length=0)
    
    # ax1.legend(loc='lower right', frameon=True, fancybox=False, edgecolor='#6e6e6e')
    ax1.legend()

    output_path = 'figures/ex_by_num_ap.png'

    fig.savefig(output_path, bbox_inches='tight')
    fig.savefig(output_path.replace('.png', '.pdf'), bbox_inches='tight')
    print(f"Saved figure to {output_path}")



if __name__ == '__main__':
    plot_ex_by_num_ap()