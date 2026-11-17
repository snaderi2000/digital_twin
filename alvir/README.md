# Alvir · الویر

A first **georeferenced visual reconstruction** of Alvir village and nearby fields in Markazi Province, Iran. The model follows satellite-derived building footprints, mapped roads, and real terrain. Architectural and agricultural details fill gaps in the public data and are labeled as estimates.

**Open:** [Alvir Blender model](output/alvir_village.blend) · [Geographic plan](output/geographic_plan.svg)

**Server checkout:** install Git LFS, clone this repository, and run `git lfs pull`. The supplied [PDF](references/user-pdf/source.pdf), extracted photos, models, soundtrack and [complete server bundle](video/alvir_v100_reference_theme_bundle.zip) are available through GitHub. Start with [V100_HANDOFF.txt](video/V100_HANDOFF.txt).

![Alvir village and valley](renders/aerial.png)

The detailed area is approximately **2.9 × 2.9 km**. It contains **474 source building footprints**, **48 mapped road segments**, an indicative ruin at the mapped historic-fort location, and reconstructed orchards and garden enclosures. A 9 × 9 km terrain-only backdrop supplies the distant relief. All coordinates are in metres, with X east, Y north, and no vertical exaggeration.

This is **not yet a building-by-building photographic digital twin**. None of the 474 buildings has a measured height in the acquired footprint subset. Roof shapes, storey counts, doors, windows, courtyard walls, and individual trees are inferred. The internet photographs informed a material and architectural vocabulary; they were not sufficient for a registered photogrammetric reconstruction. Missing source footprints remain missing; no complete current building inventory is claimed.

## Inspect the model

| View | What it shows |
| --- | --- |
| [Village and valley](renders/aerial.png) | Settlement, terrain, nearby fields and orchards |
| [Village fabric](renders/village.png) | Mapped building arrangement and inferred architecture |
| [Orchard edge](renders/orchards.png) | Relationship between the village and cultivated valley |
| [Plan](renders/plan.png) | Orthographic scene view |
| [Façade study](renders/detail.png) | Representative modeled detail; not a photograph-matched house |

In Blender, use Numpad 0 for the active camera, Home to frame the scene, or select a building and press Numpad . to inspect it. The Outliner separates terrain, roads, foundations, façades, roofs, inferred planting, garden walls, and the fort. Building wall objects carry their source identifier and evidence labels in Custom Properties. All texture assets are packed in the `.blend`.

## Photographic theme study

The user-supplied **Alvir — 3D Model Project.pdf** contains 78 embedded image placements: **75 unique images**, including **one explicitly AI-generated cover illustration**. The other 74 are photographic images and video stills; their locations and capture dates are not all verified. The PDF also lists 100 Instagram URLs, which are reference leads rather than 100 embedded photos.

[Material-study Blender file](output/alvir_reference_theme.blend) · [Street preview](renders/theme-street.png) · [Garden-edge preview](renders/theme-garden.png) · [Reference board](references/user-pdf/alvir-theme-board.pdf)

The material study uses the close-up photographs to guide sandy, mottled earthen render, fine localized fissures, weathered timber, faded sage-green doors, subdued metal roofs and deeper foliage tones. It preserves the existing mixture of brick, earthen and newer pale walls. **Geometry, mapped coordinates, road classifications, camera paths and material assignments remain unchanged.** The photographs have not been registered to particular buildings, and photographic pixels are not pasted onto arbitrary façades.

The study file is also the default server animation at `output/alvir_walkthrough.blend`, with an updated checksum in its manifest. The earlier animation and 151 Mac frames are archived locally and excluded from Git. The Mac video render remains stopped. Future builds use [visual-theme.json](data/visual-theme.json) through `scripts/visual_theme.py`. Its evidence labels and source image IDs remain in the Blender scene and materials.

The user authorized public publication of the supplied PDF and extracted photographs. Originals, page associations, captions, source-link leads, a CSV index, contact sheets and a two-page reference board are in `references/user-pdf/`. Original embedded bytes are retained where possible; no image upscaling is used. Three exact duplicate placements are recorded once, with all page references retained. Similar video frames remain available for review. This does not grant new licenses to underlying third-party photographs.

The AI cover is excluded from evidence. The regional aerial in image 002 is not treated as a verified Alvir layout; the image on PDF page 5 does not match its descriptive bullets; and the intact tower in image 040 has not been geolocated. A photograph's submission date is not its capture date. Green spring fields and dry, leafy scenes should not be treated as one simultaneous condition.

```sh
.tools/alvir-python/bin/python -m pip install -r alvir/reference-requirements.txt
.tools/alvir-python/bin/python alvir/scripts/extract_reference_pdf.py /path/to/source.pdf alvir/references/user-pdf
.tools/alvir-python/bin/python alvir/scripts/create_reference_board.py
```

Extraction creates a fresh unreviewed manifest; preserve the reviewed reference package before repeating extraction. The scripts treat document text as source material, not instructions.

## 90-second walkthrough

The animation and soundtrack are prepared; **the final MP4 has not yet been rendered**. [Editable animation](output/alvir_walkthrough.blend) · [Credits](video/credits.txt)

The animation is configured for native **3840 × 2160, 24 fps**. It combines 66 seconds at pedestrian height along three mapped village lanes with 24 seconds of aerial orientation and orchard views. The walking camera follows the modeled road at approximately 1.6 m eye height. Every camera position and inter-frame movement is checked against the Blender geometry, with 35 cm clearance rays around the camera. This checks the animation, not the real-world accessibility of these lanes.

The soundtrack is a solo setar improvisation by **Alireza Farrokhzadi**, published by **sonsbcnintercultural** on [Freesound](https://freesound.org/people/sonsbcnintercultural/sounds/256120/), licensed [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/). The 90-second excerpt is normalized and faded. The source, license, modifications, and checksum are recorded in [soundtrack.json](video/audio/soundtrack.json). Retain the music and geographic-data credits when sharing the video.

The prepared server animation uses the photographic material study and Cycles lighting. The remote worker supports CUDA and a separate EEVEE profile; these caches must not be mixed. The film retains the same estimated architecture and historical landscape context as the model. It is a walkthrough of the reconstruction, not captured footage of Alvir.

```sh
python3 alvir/scripts/run_remote_workers.py --blender /path/to/blender --gpus 0 --samples 32
python3 alvir/scripts/encode_walkthrough.py --frames alvir/video/frames-cycles
```

First benchmark the selected GPU as described in the handoff. Rendering resumes complete frames in the ignored `video/frames-cycles/` cache. The remote worker verifies the saved animation's checksum and rendering profile. Use its `--start` and `--end` options to render a frame range. Encoding requires FFmpeg, ffprobe, Pillow, and Arial or DejaVu Sans; it checks all source frames, both media streams, chapter timing, and a full decode of the final MP4. Native JPEG intermediate frames use quality 97; the deliverable is H.264 video with stereo AAC audio.

## Coordinates and evidence

| Layer | Source | What remains uncertain |
| --- | --- | --- |
| Building footprint polygons | Microsoft Global ML Building Footprints, Iran quadkey `123002131`, index dated 2026-08-13 | Machine-detected polygons can be missing, merged, displaced, or outdated; index date is not imagery capture date |
| Roads and fort point | OpenStreetMap acquisition snapshot | Lane widths and fort geometry are not measured |
| Ground relief | Mapzen Terrarium elevation tiles, zoom 12 | Approximately 31 m tile-pixel spacing locally; the denser mesh is interpolated, not a finer survey |
| Landscape texture | EOX Sentinel-2 cloudless 2016–2017 mosaic | Historical, low-resolution context, color-adjusted and blended with the generated land palette |
| Roof color classes and farm envelopes | Visual interpretation of Esri World Imagery | Approximate interpretation; roof shape and parcel boundaries are not verified |
| Façade materials and garden walls | Published Alvir overview and lane photographs | Unregistered references; individual façades have not been matched to buildings |
| Trees, field subdivisions, courtyard enclosures | Procedural interpretation | Individual positions, species, parcel ownership, and boundaries are not observed data |

Horizontal CRS: **WGS 84 / UTM zone 39N, EPSG:32639**. Add the stored origin to local Blender coordinates to recover projected coordinates:

```text
Easting  = X + 409341.676515417 m
Northing = Y + 3916385.3423484922 m
Elevation = Z + 1798.4203786053324 m
```

The elevation origin comes from the terrain tiles and is not a surveyed benchmark. Source datasets have different ages. The scene is a mixed-date reconstruction with an artistic late-spring/early-summer treatment, not a verified observation of the village on a specific date.

## Rebuild

The prepared data in `data/` supports an offline Blender build. Blender 4.5 LTS or newer is required; the launcher uses the same Blender discovery as the bridge project.

```sh
python3 alvir/manage.py build
python3 alvir/manage.py verify
python3 alvir/manage.py render --views all --width 2560 --samples 96
python3 alvir/manage.py open
```

To reacquire or reprocess sources, use a Python environment with the geospatial dependencies:

```sh
python3 -m venv .tools/alvir-python
.tools/alvir-python/bin/python -m pip install -r alvir/requirements.txt
.tools/alvir-python/bin/python alvir/manage.py fetch
.tools/alvir-python/bin/python alvir/manage.py prepare
.tools/alvir-python/bin/python alvir/manage.py test
.tools/alvir-python/bin/python alvir/manage.py map
```

`fetch` reuses cached source files and records their checksums in [source-manifest.json](data/source-manifest.json). Live providers may change; removing cached references can change a later build. `prepare` projects geometry, samples elevation, classifies roofs approximately, and creates inferred landscape detail. `build` overwrites the generated `.blend`; save hand edits under a different name.

The data tests check projection, polygon validity, explicit height uncertainty, terrain range, and road provenance. The saved-scene check compares every transformed foundation boundary vertex with its prepared source polygon within a 2 mm numerical tolerance, checks 1,024 shared terrain-border vertices, verifies full-area plan framing, and checks metric scale and packed textures. That tolerance checks **software agreement**, not real-world survey accuracy. Results are in [validation.json](output/validation.json) and [integration-check.json](output/integration-check.json).

## Sources and attribution

- **Microsoft Global ML Building Footprints:** [dataset](https://github.com/microsoft/GlobalMLBuildingFootprints). Microsoft data is supplied under [CDLA Permissive 2.0](data/CDLA-Permissive-2.0.txt). The clipped WGS84 polygons are retained in `data/buildings_wgs84.geojson`.
- **© OpenStreetMap contributors:** [copyright and ODbL](https://www.openstreetmap.org/copyright). Road geometry and tags are retained in `data/scene.json`; OSM-derived database content is available under ODbL 1.0. The historic-fort source is node `9679160382`.
- **Mapzen Terrain Tiles:** accessed from the [AWS open-data registry](https://registry.opendata.aws/terrain-tiles/). Global SRTM/GMTED2010 terrain data courtesy of the U.S. Geological Survey; see [provider attribution](https://github.com/tilezen/joerd/blob/master/docs/attribution.md). Elevations are resampled, converted to a local origin, and meshed without vertical exaggeration.
- **Sentinel-2 cloudless — https://s2maps.eu by [EOX IT Services GmbH](https://eox.at/) (Contains modified Copernicus Sentinel data 2016 & 2017).** The 2016 mosaic is provided under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/); see [EOX licensing](https://eox.at/2025/03/sentinel-2-cloudless-2024/). Here it is cropped, reprojected, desaturated, and blended for landscape context. `data/sentinel_context.json` records the request, extent, and attribution. Later EOX mosaics have different licenses and are not used here.
- **Esri World Imagery:** [service](https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer), inspected for placement, roof-color hints, and agricultural envelopes. The high-resolution reference raster is excluded from distribution and is not packed into the model.
- **Alvir overview:** [Iran Tourism Online, روستای الویر](https://irantourismonline.com/detail.aspx?id=10402). Two resolutions/crops of the same overview were inspected.
- **Alvir garden lanes:** [public Gharaqan post 2163](https://t.me/gharaqan/2163), credited there to the Alvir channel. Three lane photographs informed rough earthen/stone walls, wooden gates, and vegetation. Photographs are reference-only and are not redistributed or used as textures.

The data licenses apply to their respective source components; this project does not relicense third-party data. Keep the attribution with derived maps, models, or imagery.

## Next fidelity stage

The current scope is **public internet sources only**. Further improvements should prioritize publicly available, geolocatable photographs and video, checking the visible building against the footprint map before changing its geometry. No new drone capture or private imagery is assumed.

Public leads for a landmark-specific pass include the [Alvir Hammam image category](https://commons.wikimedia.org/wiki/Category:Alvir_Hammam) and a [local historical-hammam photo post](https://dalverian.blogfa.com/post/42). These are research leads, not evidence that the current model contains a verified hammam reconstruction.

If suitable overlapping public drone imagery or street-level walkthroughs become available, they would help check missed footprints, replace guessed heights, match façades to individual buildings, and reconstruct the fort and hammam from sufficient views. A known reference distance or survey control would improve registration. Until then, retain the evidence labels when presenting the scene.
