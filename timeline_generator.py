import argparse
import ast
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FixedLocator, FuncFormatter
import textwrap

def set_defaults(options):
    defaults = {
        "color": "darkblue",  # Color of the marker, vertical line, or horizontal span line. Accepts any Matplotlib color value.
        "textcolor": "black",  # Color of the title and description text. Accepts any Matplotlib color value.
        "text_wrap": 30,  # Number of characters before wrapping the description text
        "title_fontsize": 8,  # Font size of the title text
        "description_fontsize": 7,  # Font size of the description text
        "linewidth": 5,  # Width of horizontal span lines. Larger values create thicker bars.
        "horizontalalignment": "left",  # Text alignment relative to the annotation anchor: left, center, or right
        "x_offset": 0,  # Horizontal distance in points between the marker/bar anchor and the start of the label
        "y_offset": 36,  # Vertical distance in points between the marker/bar anchor and the start of the label
        "marker": True,  # Use False to hide a milestone marker
        "markerfmt": "o",  # Marker shape/style for milestones, e.g. "o" circle, "s" square, "^" triangle, "D" diamond, "x" cross
        "markersize": 5,  # Size of the milestone marker
        "vline": True,  # Use False to hide the vertical line descending from a milestone marker
        "vlinewidth": 0.5, # Width of vertical line descending from a milestone marker
        "annotation_anchor": "left",  # left: start time of span. right: end time of span. start: chart start time. end: chart end time.
        "alpha": 1,  # Transparency value from 0 to 1, where 0 is fully transparent and 1 is fully opaque
        "arrowprops": None,  # Dict describing the arrow between the text and marker. See matplotlib.pyplot.annotate for details.
        "placement": "center",  # Label placement behavior. Use "left" to place label left of the marker; otherwise uses configured alignment/offset.
    }

    result = defaults.copy()

    if not isinstance(options, dict):
        options = {}

    for option in options:
        result[option] = options[option]

    return result

def get_timeline(
    data,
    start=None,
    end=None,
    granularity="hours",
    interval=24,

    ylim=None,
    y_padding=0.08, # 0.5
    y_padding_ratio=0.02, # 0.15
    y_bottom_padding=None,
    y_top_padding=None,

    dateformat="%a %d %b %Y",
    fig_height=5,
    fig_width=14,
    filename=None,

    x_tick_labelsize=6,
    x_tick_wrap=True,
    x_tick_wrap_width=10,
    x_tick_horizontalalignment="center",
    x_tick_multialignment="center",
    x_tick_rotation=0,
    x_tick_bottom_margin=0.18,

    # Timeline title
    timeline_title=None,
    timeline_title_fontsize=12,
    timeline_title_fontweight="bold",
    timeline_title_loc="center",
    timeline_title_pad=12,

    # Legend
    legend_items=None,
    legend_x=0.9,
    legend_y=1.0,
    legend_width=0.12,
    legend_row_spacing=0.08,
    legend_label_x=0.0,
    legend_marker_x=0.8,
    legend_fontsize=7,
    legend_markersize=7,
    legend_title=None,

    # X-axis compression
    compress_xaxis=True, # Boolean to implement X-axis compression
    gap_threshold="48h", # Any inactive gap larger than this will be compressed.
    compressed_gap="6h", # Large inactive gaps will be visually reduced to this width.

    # Visual x-axis break marks
    show_axis_breaks=True,
    axis_break_marker_size=0.006,
    axis_break_marker_height=0.035,
    axis_break_linewidth=1.0,
):
    data = data.copy()

    data["start_datetime"] = pd.to_datetime(data.start, format="mixed", dayfirst=True)
    data["end_datetime"] = pd.to_datetime(data.end, format="mixed", dayfirst=True)

    offset_args = {}
    offset_args[granularity] = interval

    if not start:
        start_datetime = min(data.start_datetime) - pd.DateOffset(**offset_args)
    else:
        start_datetime = pd.to_datetime(start)

    if not end:
        end_datetime = max(
            max(data.start_datetime),
            max(data.end_datetime),
        ) + pd.DateOffset(**offset_args)
    else:
        end_datetime = pd.to_datetime(end)

    start_datetime = _as_naive_timestamp(start_datetime)
    end_datetime = _as_naive_timestamp(end_datetime)

    # -----------------------------
    # Apply option defaults
    # -----------------------------
    if "options" not in data.columns:
        data["options"] = [{} for _ in range(len(data))]

    data["options"] = data["options"].apply(set_defaults)
    data_options = pd.DataFrame(data["options"].tolist(), index=data.index)

    for column in data_options.columns:
        # Option columns from the CSV have been normalized inside row_to_options()
        # and then passed through set_defaults(). Prefer those normalized values
        # over the raw CSV strings so fields like arrowprops become dicts instead
        # of remaining as unparsed strings.
        data[column] = data_options[column]

    data = data.where(pd.notnull(data), None)

    # -----------------------------
    # Build x-axis compressor
    # -----------------------------
    compressor = None

    if compress_xaxis:
        gaps = _build_compression_gaps(
            data=data,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            gap_threshold=pd.to_timedelta(gap_threshold),
            compressed_gap=pd.to_timedelta(compressed_gap),
        )

        if gaps:
            compressor = XAxisCompressor(gaps)

    if compressor:
        data["plot_start_datetime"] = data["start_datetime"].apply(compressor.compress)
        data["plot_end_datetime"] = data["end_datetime"].apply(compressor.compress)

        plot_start_datetime = compressor.compress(start_datetime)
        plot_end_datetime = compressor.compress(end_datetime)
    else:
        data["plot_start_datetime"] = data["start_datetime"]
        data["plot_end_datetime"] = data["end_datetime"]

        plot_start_datetime = start_datetime
        plot_end_datetime = end_datetime

    # -----------------------------
    # Plot
    # -----------------------------
    fig, ax = plt.subplots(figsize=(fig_width, fig_height), dpi=300)

    if timeline_title:
        ax.set_title(
            str(timeline_title),
            fontsize=timeline_title_fontsize,
            fontweight=timeline_title_fontweight,
            loc=timeline_title_loc,
            pad=timeline_title_pad,
        )

    ax.set_xlim([plot_start_datetime, plot_end_datetime])

    if ylim is None:
        visible_data = data[
            (
                (data.start_datetime >= start_datetime)
                & (data.start_datetime <= end_datetime)
            )
            |
            (
                pd.notnull(data.end_datetime)
                & (data.end_datetime >= start_datetime)
                & (data.end_datetime <= end_datetime)
            )
        ]

        visible_heights = pd.to_numeric(visible_data["height"], errors="coerce").dropna()

        if visible_heights.empty:
            ax.set_ylim(-1, 1)
        else:
            min_height = visible_heights.min()
            max_height = visible_heights.max()

            # Include zero so the time axis remains visible even when all events
            # are above or below it. Padding is configurable because negative
            # heights can otherwise create too much empty space below the axis.
            height_range = max_height - min_height
            auto_padding = max(y_padding, height_range * y_padding_ratio)

            bottom_padding = auto_padding if y_bottom_padding is None else y_bottom_padding
            top_padding = auto_padding if y_top_padding is None else y_top_padding

            y_min = min(0, min_height) - bottom_padding
            y_max = max(0, max_height) + top_padding

            ax.set_ylim(y_min, y_max)
    else:
        # Backward compatible behavior:
        #   ylim=5       -> y-axis from 0 to 5
        #   ylim=(-3, 5) -> explicit lower and upper limits
        if isinstance(ylim, (list, tuple)) and len(ylim) == 2:
            ax.set_ylim(ylim[0], ylim[1])
        else:
            ax.set_ylim(0, ylim)

    spans = data[data.end_datetime.notnull()]

    if spans.shape[0] > 0:
        ax.hlines(
            spans.height,
            spans.plot_start_datetime,
            spans.plot_end_datetime,
            linewidth=spans.linewidth,
            capstyle="butt",
            alpha=spans.alpha,
            color=spans.color,
        )

    milestones = data[data.end_datetime.isnull()]

    vlines = milestones[milestones.vline == True]
    plots = milestones[milestones.marker == True]

    for index, row in plots.iterrows():
        ax.plot(
            row.plot_start_datetime,
            row.height,
            row.markerfmt,
            color=row.color,
            markerfacecolor=row.color,
            markersize=row.markersize,
        )

    ax.vlines(
        vlines.plot_start_datetime,
        0,
        vlines.height,
        color=vlines.color,
        linewidth=vlines.vlinewidth,
    )

    data.apply(lambda row: annotate(ax, row), axis=1)

    # -----------------------------
    # Axis styling
    # -----------------------------
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.spines["bottom"].set_position("zero")
    ax.get_yaxis().set_ticks([])

    _apply_xaxis_ticks(
        ax=ax,
        start_datetime=start_datetime,
        end_datetime=end_datetime,
        granularity=granularity,
        interval=interval,
        dateformat=dateformat,
        compressor=compressor,
        x_tick_wrap_width=x_tick_wrap_width if x_tick_wrap else None,
    )

    if compressor and show_axis_breaks:
        _draw_xaxis_breaks(
            ax=ax,
            compressor=compressor,
            marker_size=axis_break_marker_size,
            marker_height=axis_break_marker_height,
            linewidth=axis_break_linewidth,
        )

    ax.tick_params(axis="x", labelsize=x_tick_labelsize)

    for tick_label in ax.get_xticklabels():
        tick_label.set_rotation(x_tick_rotation)
        tick_label.set_horizontalalignment(x_tick_horizontalalignment)
        tick_label.set_multialignment(x_tick_multialignment)

    # if compressor:
    #     ax.set_xlabel("Time axis compressed where there is no activity", fontsize=x_tick_labelsize)

    if legend_items:
        add_custom_legend(
            ax=ax,
            legend_items=legend_items,
            x=legend_x,
            y=legend_y,
            width=legend_width,
            row_spacing=legend_row_spacing,
            label_x=legend_label_x,
            marker_x=legend_marker_x,
            fontsize=legend_fontsize,
            markersize=legend_markersize,
            title=legend_title,
        )

    if x_tick_wrap:
        # Wrapped tick labels need vertical space, but should not be auto-rotated.
        fig.subplots_adjust(bottom=x_tick_bottom_margin)
    else:
        fig.autofmt_xdate()

    if filename:
        plt.savefig(filename, bbox_inches="tight")

    return ax

class XAxisCompressor:
    """
    Compresses long periods of inactivity on the x-axis.

    Data is still stored as real datetimes, but plotted at compressed datetime
    positions. Tick labels are converted back to the original real datetimes.
    """

    def __init__(self, gaps):
        self.gaps = gaps

    def compress(self, value):
        if value is None or pd.isna(value):
            return pd.NaT

        ts = _as_naive_timestamp(value)
        reduction = pd.Timedelta(0)

        for gap_start, gap_end, old_gap, new_gap in self.gaps:
            if ts >= gap_end:
                reduction += old_gap - new_gap
            elif gap_start < ts < gap_end:
                ratio = new_gap / old_gap
                return gap_start - reduction + ((ts - gap_start) * ratio)
            else:
                break

        return ts - reduction

    def decompress(self, value):
        if value is None or pd.isna(value):
            return pd.NaT

        compressed_ts = _as_naive_timestamp(value)
        reduction = pd.Timedelta(0)

        for gap_start, gap_end, old_gap, new_gap in self.gaps:
            compressed_gap_start = gap_start - reduction
            compressed_gap_end = compressed_gap_start + new_gap

            if compressed_ts > compressed_gap_end:
                reduction += old_gap - new_gap
            elif compressed_gap_start <= compressed_ts <= compressed_gap_end:
                ratio = old_gap / new_gap
                return gap_start + ((compressed_ts - compressed_gap_start) * ratio)
            else:
                break

        return compressed_ts + reduction

    def is_inside_compressed_gap(self, value):
        if value is None or pd.isna(value):
            return False

        ts = _as_naive_timestamp(value)

        for gap_start, gap_end, _, _ in self.gaps:
            if gap_start < ts < gap_end:
                return True

        return False

def safe_text(value):
    return "" if value is None or pd.isna(value) else str(value)

def wrap_text(
    value,
    width,
    break_long_words=True,
    break_on_hyphens=True,
):
    """Convert a value to safe text and wrap it onto multiple lines."""
    text = safe_text(value)

    if not text:
        return ""

    try:
        width = int(width)
    except (TypeError, ValueError):
        return text

    if width <= 0:
        return text

    wrapped = textwrap.wrap(
        text,
        width=width,
        break_long_words=break_long_words,
        break_on_hyphens=break_on_hyphens,
    )

    return "\n".join(wrapped) if wrapped else text

def annotate(ax, row):
    title = safe_text(row.get("title"))
    description = safe_text(row.get("description"))

    wrapped_title = wrap_text(title, row["text_wrap"])
    wrapped_description = wrap_text(description, row["text_wrap"])

    plot_start = row.get("plot_start_datetime", row.get("start_datetime"))
    plot_end = row.get("plot_end_datetime", row.get("end_datetime"))

    if row["annotation_anchor"] == "left":
        anchor = plot_start
    elif row["annotation_anchor"] == "right":
        anchor = plot_end if plot_end is not None and not pd.isna(plot_end) else plot_start
    elif row["annotation_anchor"] == "start":
        anchor = mdates.num2date(ax.get_xlim()[0])
    elif row["annotation_anchor"] == "end":
        anchor = mdates.num2date(ax.get_xlim()[1])
    else:
        anchor = plot_start

    if row["placement"] == "left":
        row["horizontalalignment"] = "right"
        row["x_offset"] = -10

    arrowprops = _parse_arrowprops(row.get("arrowprops"))

    # Draw title separately so it can be bold.
    # The title uses the same text_wrap setting as the description.
    if wrapped_title:
        ax.annotate(
            wrapped_title,
            xy=(anchor, row.height),
            xytext=(row.x_offset, row.y_offset),
            textcoords="offset points",
            horizontalalignment=row.horizontalalignment,
            verticalalignment="top",
            color=row.textcolor,
            fontweight="bold",
            fontsize=row.title_fontsize,
            arrowprops=arrowprops,
        )

    # Draw description below the wrapped title.
    if wrapped_description:
        title_lines = wrapped_title.count("\n") + 1 if wrapped_title else 0
        desc_y_offset = row.y_offset - (title_lines * row.title_fontsize * 1.2)

        ax.annotate(
            wrapped_description,
            xy=(anchor, row.height),
            xytext=(row.x_offset, desc_y_offset),
            textcoords="offset points",
            horizontalalignment=row.horizontalalignment,
            verticalalignment="top",
            color=row.textcolor,
            fontsize=row.description_fontsize,
            arrowprops=None,
        )

def _build_compression_gaps(
    data,
    start_datetime,
    end_datetime,
    gap_threshold,
    compressed_gap,
):
    """
    Build compressed x-axis gaps from the timestamp anchors in the CSV.

    Earlier versions treated a row with both start and end values as one
    continuous active interval. That prevented compression inside long spans.

    This version treats every CSV start and end value as an important timestamp
    anchor. Long empty gaps between anchors are compressed, even when those
    anchors are the start and end of the same span. The span will still draw
    from its compressed start to compressed end, but the inactive middle portion
    can be visually shortened.
    """
    points = []

    for _, row in data.iterrows():
        for column in ("start_datetime", "end_datetime"):
            value = row.get(column)

            if value is None or pd.isna(value):
                continue

            timestamp = _as_naive_timestamp(value)

            if timestamp < start_datetime or timestamp > end_datetime:
                continue

            points.append(timestamp)

    if len(points) < 2:
        return []

    # Remove duplicates while preserving chronological order.
    points = sorted(set(points))

    gaps = []

    for raw_gap_start, raw_gap_end in zip(points, points[1:]):
        if raw_gap_end <= raw_gap_start:
            continue

        # Important:
        # End the compressed gap at midnight of the day activity resumes,
        # not at the next timestamp itself.
        #
        # Example:
        # raw_gap_end = 16 Mar 2026 10:18:28
        # compression_gap_end = 16 Mar 2026 00:00:00
        #
        # This preserves the visual distance between:
        # 16 Mar 2026 00:00:00 and 16 Mar 2026 10:18:28
        compression_gap_start = raw_gap_start
        compression_gap_end = raw_gap_end.normalize()

        # If midnight is before or equal to the previous timestamp,
        # fall back to the actual next timestamp.
        if compression_gap_end <= compression_gap_start:
            compression_gap_end = raw_gap_end

        old_gap = compression_gap_end - compression_gap_start

        if old_gap > gap_threshold and compressed_gap < old_gap:
            gaps.append(
                (
                    compression_gap_start,
                    compression_gap_end,
                    old_gap,
                    compressed_gap,
                )
            )

    return gaps

def _apply_xaxis_ticks(
    ax,
    start_datetime,
    end_datetime,
    granularity,
    interval,
    dateformat,
    compressor=None,
    x_tick_wrap_width=None,
):
    locator = _get_locator(granularity, interval)

    if compressor is None:
        ax.xaxis.set_major_locator(locator)

        def formatter(x, pos):
            real_tick = _as_naive_timestamp(mdates.num2date(x))
            return _format_tick_label(real_tick, dateformat, x_tick_wrap_width)

        ax.xaxis.set_major_formatter(FuncFormatter(formatter))
        return

    tick_values = locator.tick_values(
        start_datetime.to_pydatetime(),
        end_datetime.to_pydatetime(),
    )

    tick_candidates = []

    # Regular ticks from Matplotlib's locator.
    for tick_value in tick_values:
        real_tick = _as_naive_timestamp(mdates.num2date(tick_value))

        if real_tick < start_datetime or real_tick > end_datetime:
            continue

        # Do not put regular ticks inside the removed/compressed gap.
        if compressor.is_inside_compressed_gap(real_tick):
            continue

        compressed_tick = compressor.compress(real_tick)

        tick_candidates.append(
            {
                "real": real_tick,
                "compressed": compressed_tick,
                "priority": 1,
            }
        )

    # Add one post-break tick at midnight on the day activity resumes.
    #
    # gap_end is already the midnight boundary selected by
    # _build_compression_gaps(), for example 16 Mar 2026 00:00:00.
    for gap_start, gap_end, _, _ in compressor.gaps:
        post_break_tick = gap_end
        compressed_tick = compressor.compress(post_break_tick)

        tick_candidates.append(
            {
                "real": post_break_tick,
                "compressed": compressed_tick,
                "priority": 0,
            }
        )

    # Sort so forced post-break ticks are kept before regular duplicate labels.
    tick_candidates.sort(
        key=lambda item: (
            item["priority"],
            item["compressed"],
        )
    )

    kept_entries = []
    seen_labels = set()
    seen_positions = set()

    for item in tick_candidates:
        label = _format_tick_label(item["real"], dateformat, x_tick_wrap_width)
        position = round(mdates.date2num(item["compressed"].to_pydatetime()), 8)

        # Avoid duplicate visible labels such as:
        # Mon 16 Mar 2026   Mon 16 Mar 2026
        if label in seen_labels:
            continue

        # Avoid duplicate positions after compression.
        if position in seen_positions:
            continue

        seen_labels.add(label)
        seen_positions.add(position)
        kept_entries.append((position, label))

    kept_entries.sort(key=lambda item: item[0])

    tick_positions = [position for position, label in kept_entries]
    tick_label_by_position = dict(kept_entries)

    ax.xaxis.set_major_locator(FixedLocator(tick_positions))

    def compressed_formatter(x, pos):
        # Prefer the exact real date associated with each generated tick.
        # This avoids floating-point boundary errors where a compressed tick at
        # midnight can decompress to a tiny moment before midnight and display
        # as the previous day.
        rounded_x = round(x, 8)

        if rounded_x in tick_label_by_position:
            return tick_label_by_position[rounded_x]

        # Fallback for unexpected ticks.
        compressed_tick = _as_naive_timestamp(mdates.num2date(x))
        real_tick = compressor.decompress(compressed_tick)
        return _format_tick_label(real_tick, dateformat, x_tick_wrap_width)

    ax.xaxis.set_major_formatter(FuncFormatter(compressed_formatter))

def _format_tick_label(timestamp, dateformat, wrap_width=None):
    """Format a datetime tick label and optionally wrap it onto multiple lines."""
    label = timestamp.strftime(dateformat)

    if wrap_width is None:
        return label

    try:
        wrap_width = int(wrap_width)
    except (TypeError, ValueError):
        return label

    if wrap_width <= 0:
        return label

    return wrap_text(
        label,
        wrap_width,
        break_long_words=False,
        break_on_hyphens=False,
    )

def _get_locator(granularity, interval):
    if granularity == "minutes":
        return mdates.MinuteLocator(interval=interval)

    if granularity == "hours":
        # If the user asks for 24-hour intervals, use calendar-day ticks.
        # This is more stable than HourLocator(interval=24).
        if interval % 24 == 0:
            return mdates.DayLocator(interval=max(1, interval // 24))

        return mdates.HourLocator(interval=interval)

    if granularity == "weeks":
        return mdates.WeekLocator(interval=interval)

    if granularity == "months":
        return mdates.MonthLocator(interval=interval)

    raise ValueError(
        "Invalid granularity. Use one of: minutes, hours, weeks, months."
    )

def _as_naive_timestamp(value):
    ts = pd.Timestamp(value)

    if ts.tzinfo is not None:
        ts = ts.tz_convert(None)

    return ts

def _is_missing(value):
    if value is None:
        return True

    try:
        return bool(pd.isna(value))
    except Exception:
        return False

def _parse_arrowprops(value):
    """Return a Matplotlib-compatible arrowprops dict, or None.

    CSV cells are read as strings, but matplotlib.axes.Axes.annotate expects
    arrowprops to be either a dict or None. This helper accepts an actual dict
    or a string representation of a dict such as:

        {"arrowstyle": "->", "color": "black", "linewidth": 0.8}

    Invalid values are treated as None so one bad CSV cell does not crash the
    whole timeline generation.
    """
    if _is_missing(value):
        return None

    if isinstance(value, dict):
        return value

    if isinstance(value, str):
        stripped = value.strip()

        if stripped.lower() in {"", "none", "null", "nan"}:
            return None

        try:
            parsed = ast.literal_eval(stripped)
        except (SyntaxError, ValueError):
            return None

        if isinstance(parsed, dict):
            return parsed

    return None

def _draw_xaxis_breaks(
    ax,
    compressor,
    marker_size=0.006,
    marker_height=0.035,
    linewidth=1.0,
):
    """
    Draw one // mark per compressed x-axis gap.

    The mark is placed at y=0 in data coordinates so it follows the time axis
    even when events with negative heights move the axis upward.
    """

    xmin, xmax = ax.get_xlim()
    ymin, ymax = ax.get_ylim()

    dx = (xmax - xmin) * marker_size
    dy = (ymax - ymin) * marker_height

    y_axis = 0
    y_low = y_axis - dy
    y_high = y_axis + dy

    for gap_start, gap_end, _, _ in compressor.gaps:
        compressed_gap_start = compressor.compress(gap_start)
        compressed_gap_end = compressor.compress(gap_end)

        x_start = mdates.date2num(compressed_gap_start.to_pydatetime())
        x_end = mdates.date2num(compressed_gap_end.to_pydatetime())

        # One break marker at the center of the compressed gap.
        x = (x_start + x_end) / 2

        # First slash.
        ax.plot(
            [x - dx, x + dx],
            [y_low, y_high],
            transform=ax.transData,
            color="black",
            linewidth=linewidth,
            clip_on=False,
            zorder=10,
        )

        # Second slash.
        ax.plot(
            [x - dx * 1.8, x + dx * 0.2],
            [y_low, y_high],
            transform=ax.transData,
            color="black",
            linewidth=linewidth,
            clip_on=False,
            zorder=10,
        )


def normalize_legend_item(label, markerfmt=None, color=None):
    """
    Normalize one legend entry and apply marker/color defaults through set_defaults().
    """
    legend_options = {}

    if not _is_missing(markerfmt) and str(markerfmt).strip() != "":
        legend_options["markerfmt"] = str(markerfmt).strip()

    if not _is_missing(color) and str(color).strip() != "":
        legend_options["color"] = str(color).strip()

    legend_defaults = set_defaults(legend_options)

    return {
        "label": str(label).strip(),
        "markerfmt": legend_defaults["markerfmt"],
        "color": legend_defaults["color"],
    }

def add_custom_legend(
    ax,
    legend_items,
    x=1.02,
    y=1.0,
    width=0.28,
    row_spacing=0.08,
    label_x=0.0,
    marker_x=0.9,
    fontsize=8,
    markersize=7,
    title=None,
):
    """
    Draw a two-column custom legend.

    First column: text label
    Second column: markerfmt shape with user-specified color

    legend_items example:
        [
            {"label": "Successful VPN", "markerfmt": "o", "color": "green"},
            {"label": "Suspicious VPN", "markerfmt": "D", "color": "red"},
        ]
    """

    if not legend_items:
        return

    row_count = len(legend_items) + (1 if title else 0)

    # Height scales with the number of rows. Width is intentionally fixed so the
    # x, label_x, and marker_x coordinates remain predictable.
    legend_height = max(0.18, row_count * row_spacing + 0.12)
    legend_width = width

    legend_ax = ax.inset_axes([x, y - legend_height, legend_width, legend_height])
    legend_ax.axis("off")

    # Start slightly below the top edge so the first marker is not clipped.
    top_padding = row_spacing * 0.7
    current_y = 1.0 - top_padding

    if title:
        legend_ax.text(
            label_x,
            current_y,
            str(title),
            fontsize=fontsize,
            fontweight="bold",
            va="center",
            ha="left",
            transform=legend_ax.transAxes,
        )
        current_y -= row_spacing * 1.2

    for item in legend_items:
        legend_item = normalize_legend_item(
            item.get("label", ""),
            markerfmt=item.get("markerfmt"),
            color=item.get("color"),
        )

        legend_ax.text(
            label_x,
            current_y,
            legend_item["label"],
            fontsize=fontsize,
            va="center",
            ha="left",
            transform=legend_ax.transAxes,
        )

        legend_ax.plot(
            marker_x,
            current_y,
            marker=legend_item["markerfmt"],
            color=legend_item["color"],
            markerfacecolor=legend_item["color"],
            markeredgecolor=legend_item["color"],
            markersize=markersize,
            linestyle="None",
            transform=legend_ax.transAxes,
        )

        current_y -= row_spacing

# -----------------------------
# Command-line wrapper
# -----------------------------
def row_to_options(row):
    """
    Convert supported CSV option columns into a per-row options dictionary.

    Blank CSV cells are ignored so timeline defaults still apply.
    """
    option_fields = [
        "text_wrap",
        "x_offset",
        "y_offset",
        "arrowprops",
        "annotation_anchor",
        "horizontalalignment",
        "color",
        "textcolor",
        "alpha",
        "linewidth",
        "vline",
        "vlinewidth",
        "marker",
        "markerfmt",
        "markersize",
        "placement",
        "title_fontsize",
        "description_fontsize",
    ]

    bool_fields = {"vline", "marker"}
    numeric_fields = {
        "text_wrap",
        "x_offset",
        "y_offset",
        "alpha",
        "markersize",
        "linewidth",
        "vlinewidth",
        "title_fontsize",
        "description_fontsize",
    }

    opts = {}

    for field in option_fields:
        if field not in row or pd.isna(row[field]):
            continue

        value = row[field]

        if isinstance(value, str):
            stripped = value.strip()

            if stripped.lower() == "true":
                value = True
            elif stripped.lower() == "false":
                value = False
            elif stripped.lower() in {"none", "null", ""}:
                value = None
            elif field == "arrowprops":
                # Allows CSV values such as:
                # {"arrowstyle": "->", "color": "black"}
                # Matplotlib requires arrowprops to be a dict or None.
                value = _parse_arrowprops(stripped)
            elif field in numeric_fields:
                try:
                    value = float(stripped)
                    if value.is_integer():
                        value = int(value)
                except ValueError:
                    pass

        if field in bool_fields and isinstance(value, str):
            value = value.lower() == "true"

        opts[field] = value

    return opts

def load_events_csv(csv_file):
    """Load events from CSV and prepare the options column expected by get_timeline."""
    data = pd.read_csv(csv_file)
    data["options"] = data.apply(row_to_options, axis=1)
    return data.where(pd.notnull(data), None)

def load_legend_csv(csv_file):
    """
    Load legend entries from a CSV with three columns:

        label, markerfmt, color

    Blank markerfmt and color values are filled using set_defaults().

    A legend entry is created as long as label is present.
    """
    legend_data = pd.read_csv(csv_file)
    legend_data.columns = [str(column).strip().lower() for column in legend_data.columns]

    required_columns = {"label", "markerfmt", "color"}
    missing_columns = required_columns - set(legend_data.columns)

    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(
            f"Legend CSV must contain columns: label, markerfmt, color. Missing: {missing}"
        )

    legend_items = []

    for _, row in legend_data.iterrows():
        label = row["label"]

        # A blank label would create an unreadable legend row, so skip it.
        if _is_missing(label) or str(label).strip() == "":
            continue

        legend_items.append(
            normalize_legend_item(
                label,
                markerfmt=row["markerfmt"],
                color=row["color"],
            )
        )

    return legend_items

def parse_args(argv=None):
    script_dir = Path(__file__).resolve().parent

    parser = argparse.ArgumentParser(
        description="Generate a timeline PNG from an events CSV."
    )
    parser.add_argument(
        "-f",
        "--file",
        dest="csv_file",
        default=script_dir / "events.csv",
        type=Path,
        help="Path to the input CSV file. Defaults to events.csv beside timeline_generator.py.",
    )
    parser.add_argument(
        "-o",
        "--output",
        dest="output_file",
        default=script_dir / "timeline.png",
        type=Path,
        help="Output image path and filename. Defaults to timeline.png beside timeline_generator.py.",
    )
    parser.add_argument(
        "-l",
        "--legend",
        dest="legend_file",
        default=None,
        type=Path,
        help="Optional legend CSV file with columns: label, markerfmt, color.",
    )
    parser.add_argument(
        "-t",
        "--title",
        dest="timeline_title",
        default=None,
        help="Optional title to show above the timeline.",
    )
    parser.add_argument(
        "--title-fontsize",
        dest="timeline_title_fontsize",
        default=12,
        type=float,
        help="Timeline title font size. Defaults to 12.",
    )

    return parser.parse_args(argv)

def main(argv=None):
    args = parse_args(argv)

    csv_file = args.csv_file.expanduser()
    output_file = args.output_file.expanduser()

    if not csv_file.exists():
        raise FileNotFoundError(f"Input CSV not found: {csv_file}")

    output_file.parent.mkdir(parents=True, exist_ok=True)

    data = load_events_csv(csv_file)

    legend_items = None

    if args.legend_file:
        legend_file = args.legend_file.expanduser()

        if not legend_file.exists():
            raise FileNotFoundError(f"Legend CSV not found: {legend_file}")

        legend_items = load_legend_csv(legend_file)

    get_timeline(
        data,
        filename=str(output_file),
        legend_items=legend_items,
        timeline_title=args.timeline_title,
        timeline_title_fontsize=args.timeline_title_fontsize,
    )

    plt.show()

if __name__ == "__main__":
    main()
