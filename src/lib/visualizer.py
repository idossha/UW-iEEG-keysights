"""
visualizer.py
Generate a publication-quality timeline PNG after a stimulation session.
"""

import datetime


# Events worth labelling on the x-axis (mapped to short display names)
_EVENT_LABELS = {
    'condition_start': 'start',
    'ramp_up_start':   'ramp ↑',
    'ramp_up_done':    'ramp ↑ done',
    'stim_start':      'stim',
    'stim_done':       'stim done',
    'ramp_down_start': 'ramp ↓',
    'ramp_down_done':  'ramp ↓ done',
    'rest_start':      'rest',
    'rest_done':       'rest done',
    'pulse_train_start': 'pulses',
    'pulse_train_done':  'pulses done',
}


def generate_timeline(timeline, output_path, mode=None, t0=None):
    """
    Generate a publication-quality timeline plot of the stimulation session.

    Parameters
    ----------
    timeline : list of tuples
        Each tuple: (elapsed_s, ch1_mA, ch2_mA, label, cond_info, event).
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

    # --- Identify rest regions ---
    rest_regions = []
    rest_start_t = None
    for wt, ev in zip(wall_times, events):
        if ev == 'rest_start':
            rest_start_t = wt
        elif ev == 'rest_done' and rest_start_t is not None:
            rest_regions.append((rest_start_t, wt))
            rest_start_t = None

    # --- Condition info annotations (like REST, placed near the line) ---
    cond_annotations = []
    for i, (lbl, info) in enumerate(zip(labels, cond_infos)):
        if lbl and info:
            cond_annotations.append(
                (wall_times[i], lbl, _format_cond_info(info, mode)))

    # --- Figure size ---
    n_conds = len(cond_annotations)
    fig_width = max(12, n_conds * 1.5)
    fig, ax = plt.subplots(figsize=(fig_width, 5), dpi=150)

    # --- Plot lines (dashed so both are visible when overlapping) ---
    ax.plot(wall_times, ch1, color="steelblue", linewidth=1.4,
            linestyle="--", label="Ch 1")
    ax.plot(wall_times, ch2, color="orangered", linewidth=1.4,
            linestyle=":", label="Ch 2")

    # --- Condition vertical lines ---
    for wt_start, lbl, info_text in cond_annotations:
        ax.axvline(wt_start, color="lightgray", linestyle="--", linewidth=0.8)

    # --- Build condition info lookup per timeline point ---
    cond_info_by_idx = {}
    for i, (lbl, info) in enumerate(zip(labels, cond_infos)):
        if lbl and info:
            short = lbl.split("/")[0] if "/" in lbl else lbl
            cond_info_by_idx[i] = f"#{short} {_format_cond_info(info, mode)}"

    current_cond_info = ''
    cond_info_per_point = []
    for i, ev in enumerate(events):
        if i in cond_info_by_idx:
            current_cond_info = cond_info_by_idx[i]
        cond_info_per_point.append(current_cond_info)

    # --- X-axis: tilted time ticks at each step event ---
    tick_positions = []
    for i, (wt, ev) in enumerate(zip(wall_times, events)):
        if ev in _EVENT_LABELS:
            tick_positions.append(wt)

    ax.set_xticks(tick_positions)
    ax.set_xticklabels([t.strftime("%H:%M:%S") for t in tick_positions],
                       fontsize=6.5, rotation=45, ha="right")

    # --- Centered horizontal info labels below axis for stim and rest ---
    # Find stim (start→done) and rest (start→done) spans, place label centered.
    spans = []  # (start_wt, end_wt, label_text)
    for i, ev in enumerate(events):
        if ev == 'stim_start':
            # find matching stim_done
            for j in range(i + 1, len(events)):
                if events[j] == 'stim_done':
                    spans.append((wall_times[i], wall_times[j],
                                  cond_info_per_point[i]))
                    break
        elif ev == 'rest_start':
            for j in range(i + 1, len(events)):
                if events[j] == 'rest_done':
                    spans.append((wall_times[i], wall_times[j], 'REST'))
                    break

    for s, e, txt in spans:
        mid = s + (e - s) / 2
        ax.annotate(txt, xy=(mid, 0), xycoords=('data', 'axes fraction'),
                    xytext=(0, -42), textcoords='offset points',
                    fontsize=6.5, ha='center', va='top', color='dimgray',
                    annotation_clip=False)

    ax.set_xlabel("")
    ax.set_ylabel("Amplitude (mA)")

    # --- Title ---
    date_str = start_dt.strftime("%Y-%m-%d")
    title = f"Stimulation Timeline — {date_str}"
    if mode:
        title += f"  ({mode} mode)"
    ax.set_title(title, fontsize=11)

    # --- Legend & layout ---
    ax.legend(loc="upper right", fontsize=8, framealpha=0.9)
    ax.margins(y=0.15)
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
