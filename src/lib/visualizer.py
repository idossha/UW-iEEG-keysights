"""
visualizer.py
Generate a publication-quality timeline PNG after a stimulation session.
"""

import datetime


def generate_timeline(timeline, output_path, mode=None, t0=None):
    """
    Generate a publication-quality timeline plot of the stimulation session.

    Parameters
    ----------
    timeline : list of tuples
        Each tuple: (elapsed_s, ch1_mA, ch2_mA, label, cond_info, event).
        Labels are non-empty at condition boundaries. cond_info has the
        condition parameter string at condition_start events.
    output_path : str
        Path to save the PNG file.
    mode : str or None
        'sine' or 'phase' — used for subtitle.
    t0 : float or None
        Session start epoch (time.time()) for wall-clock x-axis.
    """
    if not timeline or len(timeline) < 2:
        return

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    # --- Apply style ---
    for style_name in ("seaborn-v0_8-whitegrid", "seaborn-whitegrid"):
        try:
            plt.style.use(style_name)
            break
        except OSError:
            continue

    # --- Unpack data ---
    elapsed = [pt[0] for pt in timeline]
    ch1 = [pt[1] for pt in timeline]
    ch2 = [pt[2] for pt in timeline]
    labels = [pt[3] for pt in timeline]
    cond_infos = [pt[4] if len(pt) > 4 else '' for pt in timeline]
    events = [pt[5] if len(pt) > 5 else '' for pt in timeline]

    # Convert elapsed → wall-clock datetimes
    if t0 is not None:
        start_dt = datetime.datetime.fromtimestamp(t0)
    else:
        start_dt = datetime.datetime.now() - datetime.timedelta(seconds=elapsed[-1])
    wall_times = [start_dt + datetime.timedelta(seconds=e) for e in elapsed]

    channels_identical = all(a == b for a, b in zip(ch1, ch2))

    # --- Identify rest regions (pairs of rest_start → rest_done) ---
    rest_regions = []
    rest_start_t = None
    for wt, ev in zip(wall_times, events):
        if ev == 'rest_start':
            rest_start_t = wt
        elif ev == 'rest_done' and rest_start_t is not None:
            rest_regions.append((rest_start_t, wt))
            rest_start_t = None

    # --- Build condition annotations ---
    annotations = []
    for i, (lbl, info) in enumerate(zip(labels, cond_infos)):
        if lbl and info:
            annotations.append((wall_times[i], lbl, _format_cond_info(info, mode)))

    # --- Figure size ---
    fig_width = max(12, len(annotations) * 1.2)
    fig, ax = plt.subplots(figsize=(fig_width, 4.5), dpi=150)

    # --- Shade rest regions ---
    for r_start, r_end in rest_regions:
        ax.axvspan(r_start, r_end, alpha=0.08, color="gray")
        mid = r_start + (r_end - r_start) / 2
        ax.text(mid, 0, "REST", fontsize=6, ha="center", va="bottom",
                color="gray", style="italic")

    # --- Plot lines ---
    if channels_identical:
        ax.plot(wall_times, ch1, color="steelblue", linewidth=1.4, label="Amplitude")
        ax.fill_between(wall_times, ch1, alpha=0.15, color="steelblue")
    else:
        ax.plot(wall_times, ch1, color="steelblue", linewidth=1.4, label="Ch 1")
        ax.fill_between(wall_times, ch1, alpha=0.15, color="steelblue")
        ax.plot(wall_times, ch2, color="orangered", linewidth=1.4, label="Ch 2")

    # --- Condition annotations ---
    y_top = ax.get_ylim()[1]
    for wt, lbl, info_text in annotations:
        ax.axvline(wt, color="lightgray", linestyle="--", linewidth=0.8)
        short = lbl.split("/")[0] if "/" in lbl else lbl
        ax.text(
            wt, y_top * 1.02,
            f"{short}  {info_text}",
            fontsize=6, ha="left", va="bottom", color="dimgray",
            rotation=45, rotation_mode="anchor",
        )

    # --- X-axis: wall-clock ---
    total_s = elapsed[-1]
    if total_s < 300:
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))
    else:
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    fig.autofmt_xdate(rotation=0, ha="center")
    ax.set_xlabel("Time")
    ax.set_ylabel("Amplitude (mA)")

    # --- Title ---
    date_str = start_dt.strftime("%Y-%m-%d")
    title = f"Stimulation Timeline — {date_str}"
    if mode:
        title += f"  ({mode} mode)"
    ax.set_title(title, fontsize=11)

    # --- Legend & layout ---
    ax.legend(loc="upper right", fontsize=8, framealpha=0.9)
    ax.margins(y=0.25)
    fig.tight_layout()

    # --- Save ---
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def _format_cond_info(info, mode):
    """Turn a raw condition string into a compact annotation label."""
    if mode == 'sine':
        parts = {}
        for tok in info.split():
            if '=' in tok:
                k, v = tok.split('=', 1)
                parts[k] = v
        f1 = parts.get('f1', '?')
        f2 = parts.get('f2', '?')
        a1 = parts.get('a1', '?')
        a2 = parts.get('a2', '?')
        beat = parts.get('beat', '')
        return f"{f1}+{f2}Hz  {a1}/{a2}mA  Δ{beat}"
    elif mode == 'phase':
        parts = {}
        extra = []
        for tok in info.split():
            if '=' in tok:
                k, v = tok.split('=', 1)
                parts[k] = v
            else:
                extra.append(tok)
        carrier = parts.get('carrier', '?')
        a1 = parts.get('a1', '?')
        a2 = parts.get('a2', '?')
        pulses = ' '.join(extra)
        return f"{carrier}  {a1}/{a2}mA  {pulses}"
    else:
        return info
