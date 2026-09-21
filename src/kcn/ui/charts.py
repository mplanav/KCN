"""Gráficas como imagen PNG (matplotlib) para mostrar en la app."""

from __future__ import annotations

import base64
import io

import matplotlib
matplotlib.use("Agg")            # sin ventana: solo genera imágenes
import matplotlib.pyplot as plt

from kcn.ui import theme as t


def line_png_b64(series: list[tuple], color: str) -> str:
    """Genera una gráfica de líneas y la devuelve como PNG en base64."""
    dates = [d for d, _ in series]
    values = [v for _, v in series]

    fig, ax = plt.subplots(figsize=(5.2, 2.7), dpi=110)
    fig.patch.set_facecolor(t.SURFACE)
    ax.set_facecolor(t.SURFACE)

    ax.plot(range(len(values)), values, color=color, linewidth=2.5,
            marker="o", markersize=4)
    ax.tick_params(colors=t.MUTED, labelsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(t.BORDER)
    ax.spines["bottom"].set_color(t.BORDER)

    n = len(values)
    step = max(1, n // 5)
    ax.set_xticks(range(0, n, step))
    ax.set_xticklabels([dates[i].strftime("%d/%m") for i in range(0, n, step)])
    ax.grid(True, color=t.BORDER, linewidth=0.5, alpha=0.5)

    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor=fig.get_facecolor())
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()
