# Alvir reference cache

Downloaded working references are excluded from Git. Run `alvir/manage.py fetch` to obtain the source map/elevation cache; prepared, attributed data is included in `alvir/data/` for offline builds.

The user explicitly authorized publication of the supplied PDF and extracted photos in `user-pdf/`; that directory is included, with its image/PDF assets managed through Git LFS. See its `README.txt` and reviewed manifest for provenance, uncertain captions, and the AI illustration excluded from evidence.

`satellite-context.jpg` is an Esri World Imagery reference export, not a distributed terrain texture. `alignment-check.jpg` overlays the source footprints and roads for local inspection. Published village and lane photographs are reference-only; source links and the model's limits are recorded in [the Alvir README](../README.md).

The separately licensed EOX Sentinel landscape mosaic and its attribution are in `alvir/data/`. That historical, lower-resolution image supplies the packed landscape texture.
