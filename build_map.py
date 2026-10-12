# %% [markdown]
# # Interactive Web Map of Waste-Bin Observations (QField → Folium)
#
# **Student:** Priyanshu Verma (CS25M113)
#
# This notebook turns the waste-bin point notes collected with **QField** into an
# interactive **Folium** web map (`index.html`) that can be hosted on GitHub Pages.
#
# Pipeline
# 1. Read the QField `notes.gpkg` (point notes + attachment table that links each note to its photo).
# 2. Resize the original 1.5 MB phone photos into small web-friendly JPEGs in `images/`.
# 3. Build the Folium map: markers, tooltips, popups with photos, GPS track, legend, layer control.
# 4. Save `index.html`. Photos are referenced with **relative paths** (`images/...`), so they
#    keep working once the folder is published (e.g. GitHub Pages).

# %%
from pathlib import Path
import html
import warnings

import geopandas as gpd
import pandas as pd
import folium
from folium import plugins
from branca.element import MacroElement, Template
from PIL import Image, ImageOps

warnings.filterwarnings("ignore")

ROOT = Path(".")               # project folder (contains data/, images/, DCIM/ ...)
OUT_HTML = ROOT / "index.html"

# %% [markdown]
# ## 1. Configuration
#
# Each entry in `CONTRIBUTORS` is one student's QField dataset.
# To add a classmate's observations, add another entry with `own=False` – their name is then
# shown in every popup as the original collector and the layer is labelled as shared data.

# %%
CONTRIBUTORS = [
    dict(
        name="Priyanshu Verma",
        student_id="CS25M113",
        gpkg=ROOT / "data" / "notes.gpkg",
        image_dir=ROOT / "images",          # resized web photos live here
        original_dir=ROOT / "DCIM",         # original QField photos (optional, not committed)
        own=True,
    ),
    # Example of a classmate's data (uncomment and edit):
    # dict(
    #     name="Classmate Name",
    #     student_id="csXXmYYY",
    #     gpkg=ROOT / "data" / "classmate_name" / "notes.gpkg",
    #     image_dir=ROOT / "images" / "classmate_name",
    #     original_dir=ROOT / "data" / "classmate_name" / "DCIM",
    #     own=False,
    # ),
]

TRACKS_FILE = ROOT / "data" / "tracks.geojson"
NOTE_LABEL = "Field note (bin fill level, %)"   # how the QField 'note' text is interpreted
MAX_PHOTO_PX = 900                               # longest side of web photos
LOCAL_TZ = "Asia/Kolkata"

# %% [markdown]
# ## 2. Load QField notes and attach photos

# %%
def prepare_photo(media_path: str, c: dict) -> str | None:
    """Return a relative web path to a resized photo for this observation.

    If the original photo is available it is (re)sized into `image_dir`; otherwise an
    already-resized copy with the same file name is used.
    """
    name = Path(media_path).name
    dst = c["image_dir"] / name
    src = c["original_dir"] / name
    if src.exists() and not dst.exists():
        c["image_dir"].mkdir(parents=True, exist_ok=True)
        with Image.open(src) as im:
            im = ImageOps.exif_transpose(im).convert("RGB")
            im.thumbnail((MAX_PHOTO_PX, MAX_PHOTO_PX))
            im.save(dst, "JPEG", quality=80, optimize=True)
    return dst.as_posix() if dst.exists() else None


def load_observations(c: dict) -> gpd.GeoDataFrame:
    pts = gpd.read_file(c["gpkg"], layer="notes_point", fid_as_index=True)
    pts.index.name = "fid"
    pts = pts.reset_index()
    att = gpd.read_file(c["gpkg"], layer="notes_attachments")
    att = att[["note_uuid", "media"]].drop_duplicates("note_uuid")

    df = pts.merge(att, left_on="uuid", right_on="note_uuid", how="left")
    df["lon"] = df.geometry.x
    df["lat"] = df.geometry.y
    df["time_local"] = (
        pd.to_datetime(df["timestamp"], utc=True).dt.tz_convert(LOCAL_TZ)
        .dt.strftime("%d %b %Y, %I:%M %p IST")
    )
    df["photo"] = df["media"].apply(lambda m: prepare_photo(m, c) if isinstance(m, str) else None)
    df["fill"] = pd.to_numeric(df["note"], errors="coerce")
    df["collector"] = c["name"]
    df["student_id"] = c["student_id"]
    df["own"] = c["own"]
    return df


frames = [load_observations(c) for c in CONTRIBUTORS]
obs = pd.concat(frames, ignore_index=True)
print(f"{len(obs)} observations, {obs['photo'].notna().sum()} with photos")
obs[["fid", "title", "note", "time_local", "photo"]].head()

# %% [markdown]
# ## 3. Styling helpers (fill level → colour, popup HTML)

# %%
def fill_style(fill) -> tuple[str, str]:
    """(folium icon colour, label) from fill level percentage."""
    if pd.isna(fill):
        return "gray", "Unknown"
    if fill < 34:
        return "green", "Low (0–33 %)"
    if fill < 67:
        return "orange", "Medium (34–66 %)"
    return "red", "High (67–100 %)"


def popup_html(r) -> str:
    e = html.escape
    own = bool(r["own"])
    header_bg = "#1f6feb" if own else "#8250df"
    colour, label = fill_style(r["fill"])
    note = "" if pd.isna(r["note"]) else str(r["note"])
    fill_txt = f"{note} %" if note != "" else "—"

    if own:
        credit = f"{e(r['collector'])} ({e(r['student_id'])})"
        src_row = ""
    else:
        credit = f"{e(r['collector'])} ({e(r['student_id'])})"
        src_row = (
            "<tr><td><b>Data source</b></td><td>Shared by classmate &ndash; "
            f"originally collected by <b>{e(r['collector'])}</b></td></tr>"
        )

    photo = ""
    if isinstance(r["photo"], str):
        p = e(r["photo"])
        photo = (
            f'<a href="{p}" target="_blank" rel="noopener" title="Open full photo">'
            f'<img src="{p}" alt="Photo of {e(str(r["title"]))}" loading="lazy" '
            'style="width:100%;height:230px;object-fit:contain;background:#eee;'
            'border-radius:6px;margin-top:6px;display:block"></a>'
            '<div style="font-size:10px;color:#666;text-align:center">Click photo to open full size</div>'
        )
    else:
        photo = '<div style="margin-top:6px;color:#999">No photo attached</div>'

    return f"""
    <div style="font-family:Arial,Helvetica,sans-serif;font-size:12px;width:250px">
      <div style="background:{header_bg};color:#fff;padding:6px 8px;border-radius:6px 6px 0 0;
                  font-size:14px;font-weight:bold">
        &#128465; Waste bin: {e(str(r['title']))}
      </div>
      <table style="width:100%;border-collapse:collapse;margin-top:4px">
        <tr><td style="width:38%"><b>Collected by</b></td><td>{credit}</td></tr>
        {src_row}
        <tr><td><b>{e(NOTE_LABEL.split(' (')[0])}</b></td><td>{e(note) if note else '—'}</td></tr>
        <tr><td><b>Fill level</b></td><td><span style="color:{'#2da44e' if colour=='green' else '#d98100' if colour=='orange' else '#cf222e' if colour=='red' else '#666'}">&#9679;</span> {fill_txt} &ndash; {label}</td></tr>
        <tr><td><b>Recorded</b></td><td>{e(r['time_local'])}</td></tr>
        <tr><td><b>Location</b></td><td>{r['lat']:.6f}, {r['lon']:.6f}</td></tr>
        <tr><td><b>QField ID</b></td><td>#{int(r['fid'])}</td></tr>
      </table>
      {photo}
    </div>
    """

# %% [markdown]
# ## 4. Build the map

# %%
centre = [obs["lat"].mean(), obs["lon"].mean()]
m = folium.Map(location=centre, zoom_start=17, max_zoom=21, tiles=None, control_scale=True)

# Base maps
folium.TileLayer("OpenStreetMap", name="OpenStreetMap", max_zoom=21, max_native_zoom=19, show=True).add_to(m)
folium.TileLayer(
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attr="Tiles &copy; Esri &mdash; Source: Esri, Maxar, Earthstar Geographics",
    name="Satellite (Esri World Imagery)", max_zoom=21, max_native_zoom=19, show=False,
).add_to(m)
folium.TileLayer("CartoDB positron", name="Light (CartoDB Positron)", max_zoom=21, show=False).add_to(m)

# GPS survey track (drawn first so markers sit on top)
if TRACKS_FILE.exists():
    tracks = folium.FeatureGroup(name="GPS survey track (QField)", show=True)
    folium.GeoJson(
        str(TRACKS_FILE),
        style_function=lambda f: {"color": "#1f6feb", "weight": 3, "opacity": 0.7, "dashArray": "6,6"},
        tooltip=folium.GeoJsonTooltip(fields=["timestamp"], aliases=["Track recorded (UTC):"]),
    ).add_to(tracks)
    tracks.add_to(m)

# One feature group per contributor -> toggled in the Layer Control
for c in CONTRIBUTORS:
    sub = obs[obs["student_id"] == c["student_id"]]
    label = (
        f"Waste bins – {c['name']} ({c['student_id']})"
        if c["own"]
        else f"Waste bins – data by {c['name']} ({c['student_id']}) [shared]"
    )
    fg = folium.FeatureGroup(name=label, show=True)
    for _, r in sub.iterrows():
        colour, lvl = fill_style(r["fill"])
        fill_txt = "n/a" if pd.isna(r["fill"]) else f"{r['fill']:.0f} %"
        tooltip = (
            f"<b>{html.escape(str(r['title']))}</b> &middot; fill {fill_txt}<br>"
            f"<span style='font-size:11px'>by {html.escape(r['collector'])}</span>"
        )
        folium.Marker(
            location=[r["lat"], r["lon"]],
            tooltip=folium.Tooltip(tooltip, sticky=True),
            popup=folium.Popup(popup_html(r), max_width=290, auto_pan_padding_top_left=(60, 130),
                               auto_pan_padding_bottom_right=(20, 20)),
            icon=folium.Icon(color=colour, icon="trash", prefix="fa"),
        ).add_to(fg)
    fg.add_to(m)

# Map controls
folium.LayerControl(collapsed=False, position="topright").add_to(m)
plugins.Fullscreen(position="topleft").add_to(m)
plugins.LocateControl(position="topleft", strings={"title": "Show my location"}).add_to(m)
plugins.MeasureControl(position="bottomleft", primary_length_unit="meters").add_to(m)
plugins.MiniMap(toggle_display=True, position="bottomright").add_to(m)
plugins.MousePosition(position="bottomleft", num_digits=5).add_to(m)

# Fit to data
m.fit_bounds(obs[["lat", "lon"]].values.tolist(), padding=(30, 30))

# %% [markdown]
# ### Title box and legend

# %%
n_total = len(obs)
collectors = ", ".join(sorted({f"{c['name']} ({c['student_id']})" for c in CONTRIBUTORS}))
n_low = int((obs["fill"] < 34).sum())
n_mid = int(((obs["fill"] >= 34) & (obs["fill"] < 67)).sum())
n_high = int((obs["fill"] >= 67).sum())

panel = Template(f"""
{{% macro html(this, kwargs) %}}
<div style="position:fixed;top:10px;left:50px;z-index:9999;background:rgba(255,255,255,.95);
  padding:8px 12px;border-radius:8px;box-shadow:0 1px 6px rgba(0,0,0,.35);
  font-family:Arial,Helvetica,sans-serif;font-size:12px;max-width:290px">
  <div style="font-size:15px;font-weight:bold">Waste-Bin Observations</div>
  <div style="color:#555">Collected with QField &middot; Folium web map</div>
  <div style="margin-top:4px"><b>Collector:</b> {html.escape(collectors)}</div>
  <div><b>Total bins mapped:</b> {n_total}</div>
</div>
<div style="position:fixed;bottom:30px;right:10px;z-index:9999;background:rgba(255,255,255,.95);
  padding:8px 12px;border-radius:8px;box-shadow:0 1px 6px rgba(0,0,0,.35);
  font-family:Arial,Helvetica,sans-serif;font-size:12px;margin-bottom:165px">
  <div style="font-weight:bold;margin-bottom:3px">Bin fill level</div>
  <div><span style="color:#2da44e">&#9679;</span> Low (0&ndash;33 %): {n_low}</div>
  <div><span style="color:#d98100">&#9679;</span> Medium (34&ndash;66 %): {n_mid}</div>
  <div><span style="color:#cf222e">&#9679;</span> High (67&ndash;100 %): {n_high}</div>
  <div style="margin-top:3px;font-size:10px;color:#666">Click a marker for photo &amp; details</div>
</div>
{{% endmacro %}}
""")
legend = MacroElement()
legend._template = panel
m.get_root().add_child(legend)

m.get_root().html.add_child(folium.Element("<title>Waste-Bin Observations – CS25M113</title>"))

# %% [markdown]
# ## 5. Save the HTML map

# %%
m.save(str(OUT_HTML))
print("Saved", OUT_HTML.resolve())
m
