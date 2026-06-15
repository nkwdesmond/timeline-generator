# Timeline Generator

Create visual timelines from structured CSV data for incident investigations, activity reviews, case notes, and other time-based analysis.

This project was forked from [IBM/timeline-generator](https://github.com/IBM/timeline-generator) and extended with a standalone command-line workflow, richer CSV-based styling, x-axis compression, x-axis break markers, and additional annotation controls.

## Purpose

Timeline Generator helps you keep timeline data in a repeatable, structured format while producing clean visual outputs with Matplotlib.

It is designed for cases where a timeline needs more detail and formatting control than a hand-built spreadsheet, Mermaid diagram, or PlantUML diagram. Typical uses include:

- incident response timelines
- VPN, authentication, endpoint, or network activity timelines
- investigation summaries
- event sequence reconstruction
- reporting graphics for cases or post-incident reviews

## Features

- Milestones: events that occur at a single point in time.
- Spans: events with both a start and end time.
- CSV-driven formatting for each event.
- Standalone CLI usage with `-f` input and `-o` output flags.
- Default input/output behavior using `events.csv` and `timeline.png`.
- X-axis compression for long inactive periods.
- Visual `//` break markers for compressed gaps.
- Compression based on CSV timestamp anchors, meaning both `start` and `end` values can define compression points.
- Support for compression inside long spans.
- Configurable marker style, marker size, vertical line visibility, vertical line width, horizontal span width, transparency, colors, font sizes, wrapping, offsets, and annotation anchors.
- Optional arrow annotations using Matplotlib-compatible `arrowprops`.
- Date parsing through `pandas.to_datetime`.
- Output format controlled by the output filename extension, such as `.png`, `.svg`, or `.pdf`.

## Requirements

- Python 3
- pandas
- matplotlib

Install dependencies with:

```bash
pip install pandas matplotlib
```

## Quick Start

Place `timeline_generator.py` and `events.csv` in the same folder, then run:

```bash
python timeline_generator.py
```

By default, the script reads:

```text
events.csv
```

and writes:

```text
timeline.png
```

in the same folder as `timeline_generator.py`.

## Command-Line Usage

Use `-f` or `--file` to specify the input CSV.

Use `-o` or `--output` to specify the output image path and filename.

```bash
python timeline_generator.py -f events.csv -o timeline.png
```

Example with explicit paths:
```bash
python timeline_generator.py -f demo_events.csv -o demo_timeline.png
```
```bash
python timeline_generator.py -f C:\cases\case001\events.csv -o C:\cases\case001\timeline.png
```

The output file extension controls the saved file type. For example:

```bash
python timeline_generator.py -f events.csv -o timeline.svg
python timeline_generator.py -f events.csv -o timeline.pdf
```

## CSV Format

The CSV must include at least the following columns:

```csv
start,end,title,description,height
```

A milestone has a `start` value and a blank `end` value.

A span has both `start` and `end` values.

Example:

```csv
start,end,title,description,height,color
24/2/2026 10:54:22,,VPN Login,Successful VPN login,1,blue
24/2/2026 11:15:00,24/2/2026 12:30:00,Active Session,VPN session duration,2,green
```

The script uses `dayfirst=True` when parsing dates, so values such as `24/2/2026` are interpreted as `24 February 2026`.

## Supported CSV Columns

| Column | Required | Description |
|---|---:|---|
| `start` | Yes | Start date/time of the event. For milestones, this is the event time. |
| `end` | No | End date/time of the event. Leave blank for milestones. |
| `title` | No | Title text displayed in bold. |
| `description` | No | Description text displayed below the title. |
| `height` | Yes | Vertical position of the event on the chart. Use different values to separate overlapping labels or bars. |
| `color` | No | Color of the marker, vertical line, or horizontal span line. Accepts Matplotlib color values. |
| `textcolor` | No | Color of the title and description text. |
| `text_wrap` | No | Number of characters before wrapping description text. |
| `title_fontsize` | No | Font size of the title text. |
| `description_fontsize` | No | Font size of the description text. |
| `linewidth` | No | Width of horizontal span lines. Larger values create thicker bars. |
| `alpha` | No | Transparency from `0` to `1`, where `0` is fully transparent and `1` is fully opaque. |
| `marker` | No | Use `False` to hide a milestone marker. |
| `markerfmt` | No | Marker shape/style, such as `o`, `s`, `^`, `D`, or `x`. |
| `markersize` | No | Size of the milestone marker. |
| `vline` | No | Use `False` to hide the vertical line below a milestone marker. |
| `vlinewidth` | No | Width of the vertical line below a milestone marker. |
| `horizontalalignment` | No | Text alignment relative to the annotation anchor: `left`, `center`, or `right`. |
| `x_offset` | No | Horizontal label offset in Matplotlib points. |
| `y_offset` | No | Vertical label offset in Matplotlib points. |
| `annotation_anchor` | No | Label anchor mode: `left`, `right`, `start`, or `end`. |
| `placement` | No | Label placement helper. Use `left` to place the label left of the marker. |
| `arrowprops` | No | Optional Matplotlib arrow properties as a dictionary-like CSV string. |

## Default Style Values

If a CSV cell is blank, the script uses the default value.

| Option | Default | Meaning |
|---|---:|---|
| `color` | `darkblue` | Default marker, vertical line, or span line color. |
| `textcolor` | `black` | Default label text color. |
| `text_wrap` | `30` | Wrap description text after roughly this many characters. |
| `title_fontsize` | `6` | Default title font size. |
| `description_fontsize` | `5` | Default description font size. |
| `linewidth` | `5` | Default horizontal span line width. |
| `horizontalalignment` | `center` | Default label alignment. |
| `x_offset` | `0` | Default horizontal label offset in points. |
| `y_offset` | `33` | Default vertical label offset in points. |
| `marker` | `True` | Show milestone markers by default. |
| `markerfmt` | `o` | Use circle milestone markers by default. |
| `markersize` | `5` | Default marker size. |
| `vline` | `True` | Show milestone vertical lines by default. |
| `vlinewidth` | `0.5` | Default milestone vertical line width. |
| `annotation_anchor` | `left` | Anchor labels to the event start by default. |
| `alpha` | `1` | Fully opaque by default. |
| `arrowprops` | `None` | No annotation arrow by default. |
| `placement` | `center` | Use configured alignment and offsets by default. |

## Annotation Anchors

The `annotation_anchor` column controls where the label is anchored.

| Value | Behavior |
|---|---|
| `left` | Anchor label to the event start time. |
| `right` | Anchor label to the event end time. Useful for spans. |
| `start` | Anchor label to the visible left edge of the chart. |
| `end` | Anchor label to the visible right edge of the chart. |

## X-Axis Compression

The script can compress long inactive periods so that dense areas of activity remain readable.

By default:

```python
compress_xaxis=True
gap_threshold="48h"
compressed_gap="6h"
show_axis_breaks=True
```

This means inactive gaps longer than 48 hours are visually shortened. A `//` marker is drawn on the x-axis to show that time has been compressed.

Compression is based on CSV timestamp anchors. Both `start` and non-empty `end` values are treated as important points. This allows the script to compress inactive time even when that inactive period is in the middle of a long span.

For example, if a span starts on 1 March and ends on 16 March, the script can still compress long inactive periods between timestamp anchors while keeping the span visually connected.

## Arrow Annotations

The `arrowprops` column may contain a Matplotlib-compatible dictionary.

Because this value is inside CSV, double quotes must be escaped.

Example CSV cell:

```csv
"{""arrowstyle"": ""->"", ""color"": ""purple"", ""linewidth"": 0.8}"
```

This becomes the following Python dictionary:

```python
{"arrowstyle": "->", "color": "purple", "linewidth": 0.8}
```

Invalid or blank `arrowprops` values are treated as `None`.

## Example CSV

```csv
start,end,title,description,height,color,title_fontsize,description_fontsize,markerfmt,markersize,placement,alpha,vline,marker,text_wrap,x_offset,y_offset,arrowprops,horizontalalignment,annotation_anchor,textcolor,linewidth,vlinewidth
24/2/2026 10:54:22,,Initial VPN Login,Successful VPN connection from external IP,1,blue,7,5,o,6,center,1,True,True,30,0,33,,center,left,black,5,0.5
24/2/2026 11:00:00,24/2/2026 13:30:00,VPN Session,Session remained active for two and a half hours,2,green,7,5,,5,center,0.8,True,True,35,0,33,,center,left,black,8,0.5
25/2/2026 09:15:00,,Alert Generated,Detection rule triggered and created an alert,3,red,7,5,D,7,left,1,True,True,30,-10,35,"{""arrowstyle"": ""->"", ""color"": ""red"", ""linewidth"": 0.8}",right,left,black,5,0.5
16/3/2026 10:18:28,16/3/2026 11:53:16,Post-Break Activity,Activity after a long inactive period demonstrates x-axis compression,1.5,purple,7,5,s,6,center,1,True,True,35,0,33,,center,left,black,6,0.5
```

## Programmatic Usage

You can also import `get_timeline()` from another Python script.

```python
import pandas as pd
from timeline_generator import get_timeline, load_events_csv

data = load_events_csv("events.csv")

get_timeline(
    data,
    filename="timeline.png",
    compress_xaxis=True,
    gap_threshold="48h",
    compressed_gap="6h",
)
```

## Notes and Tips

- Use different `height` values to prevent labels from overlapping.
- Use `text_wrap`, `x_offset`, and `y_offset` to improve label readability.
- Use `marker=False` for milestones where only the annotation text is needed.
- Use `vline=False` to hide milestone guide lines.
- Use `alpha` to make long spans less visually dominant.
- Use `linewidth` to emphasize important spans.
- Use `vlinewidth` to adjust milestone guide-line thickness.
- Use `annotation_anchor=start` or `annotation_anchor=end` for chart-level notes.
- Use output extensions such as `.png`, `.svg`, or `.pdf` depending on where the timeline will be used.

## License and Attribution

This project was forked from [IBM/timeline-generator](https://github.com/IBM/timeline-generator).

Review the original repository for upstream licensing and attribution requirements before redistributing modified versions.
