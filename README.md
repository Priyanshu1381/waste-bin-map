# Interactive Web Map of Waste-Bin Observations

**Student:** Priyanshu Verma (CS25M113) · Urban Data / QField field survey

Interactive Folium map of 29 waste bins recorded with QField on campus, each with a
photo, field note, timestamp and the name of the student who collected it.

**Live map:** `https://<your-github-username>.github.io/<repo-name>/`

## Contents
| Path | What it is |
|---|---|
| `index.html` | The hosted interactive map (generated) |
| `images/` | Web-sized photos (≈ 75 KB each), referenced by relative path in the popups |
| `data/notes.gpkg` | QField point notes + attachment table (source data) |
| `data/tracks.geojson` | QField GPS tracks (exported from `tracks.gpkg`) |
| `build_map.py` / `waste_bin_map.ipynb` | Code that builds the map (same code, script and notebook) |

## Rebuild
```bash
pip install folium geopandas pillow
python build_map.py          # or run waste_bin_map.ipynb
```
Original QField photos (`DCIM/`) are optional: if present they are resized into `images/`,
otherwise the committed `images/` are used.

## Adding another student's data
Add an entry to `CONTRIBUTORS` in the code with `own=False`, their `notes.gpkg` and photo
folder. Their name is then shown in every popup as the original collector and the layer is
labelled as shared data. Acknowledge them here too:

| Collector | Student ID | Observations | Shared by |
|---|---|---|---|
| _none yet_ | | | |

## Notes
- The QField note text (0–100) is interpreted as bin **fill level in %**; change `NOTE_LABEL`
  and `fill_style()` in the code if it means something else.
- Times are converted from QField's UTC stamps to IST.
- Basemaps: OpenStreetMap, Esri World Imagery, CartoDB Positron.
