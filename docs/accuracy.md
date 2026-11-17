# Accuracy, provenance, and modeling decisions

## Scope

The requested state is **present-day architecture with a flowing river**. This reconstruction captures the bridge's recognizable architectural organization, repeating pointed masonry arches, galleries, brick character, stone foundations, cutwaters, and water setting. It is not a reconstruction of the vanished Safavid painted interiors.

The model is expressed in metres in a local coordinate system: X follows the bridge, Y crosses it in the river-flow direction, and Z is vertical. A metadata datum records a published approximate location for context. The geometry is **not georeferenced**, nor is the lighting an astronomical reconstruction for a known date and orientation.

## References

1. [Encyclopaedia Iranica, “Isfahan x. Monuments (5) Bridges,” Sussan Babaie](https://www.iranicaonline.org/articles/isfahan-x5-bridges/). Architectural organization, approximate 300 m length, 33 spans, central circulation and raised pedestrian promenades. This is the principal architectural-history reference.
2. [Cardiff University thesis, opening chapter on masonry arch bridges](https://orca.cardiff.ac.uk/id/eprint/55998/3/U584743-%20DEC%20PAGE%20REMOVED.pdf). Reports 295 m length, 13.8 m width, 33 spans, and stone-and-brick construction.
3. [Si-o-se-pol overview and linked references](https://en.wikipedia.org/wiki/Si-o-se-pol). Reports 297.76 m length, 14.75 m width and 5.60 m longest clear span. These values are not presented as our own measurements. Different published dimensions are retained as a documented discrepancy, rather than silently treated as equivalent.
4. [Takeo Kamiya, Bridge of 33 Arches](https://www.ne.jp/asahi/arc/ind/2_meisaku/58_bridge/x33a_1eng.htm). Broad photographic reference for the relationship of the river arches, denser upper arcade, and central pavilion.
5. [Wikimedia Commons, “33pol-innerview.JPG”](https://commons.wikimedia.org/wiki/File:33pol-innerview.JPG). Visual reference for the lower longitudinal passage, pointed ribs, stone bases and weathered masonry.
6. [RNZ, AFP/Atta Kenare photograph of the bridge](https://www.rnz.co.nz/news/world/514719/israel-attacks-iran-sources-say-drones-reported-over-isfahan). Close external photographic reference for upper niches, central projection, radial brick arches, and cutwater shoulders. Photograph described as taken 15 May 2022.
7. [Tripadvisor, Si O Se Pol Bridge visitor photographs](https://www.tripadvisor.com/Attraction_Review-g295423-d324079-Reviews-Si_O_Se_Pol_Bridge-Isfahan_Isfahan_Province.html). Upper deck reference showing broad central walkway, recessed pointed niches, smaller access portals, and seating ledges.

Reference photographs were inspected locally. They are not textures, not included in the `.blend`, and are ignored by Git. No license to redistribute third-party photographs is implied.

## Dimensional decisions

| Feature | Model | Evidence / confidence |
| --- | --- | --- |
| River span count | 33 | Consistent across references; high confidence |
| Overall length | 297.76 m | Published value; other sources use about 295–300 m |
| Nominal body width | 13.8 m | Cardiff source; other sources differ, possibly in extent conventions |
| River opening width | 5.6 m, repeated | Published maximum applied uniformly; individual spans are not surveyed |
| Bay spacing | Equal, derived from total length and end margins | Procedural simplification |
| Upper arcade | Three narrow openings per river bay, with central pavilion replacement | Photographic interpretation; exact opening inventory not surveyed |
| Deck level | 6.65 m above local datum | Estimated from photographic proportions |
| Main roof | 12.05 m, plus coping | Estimated, not a measured height |
| Pointed arch shape | Two circular arcs | Geometric approximation of Persian pointed profiles |
| Brick and stone dimensions | Regular nominal courses | Material-scale estimates; not a masonry survey |
| Water level | 0.70 m above local datum | Chosen visual state, not a current observation |

Pavilion size, niche depths, foundations, passage clearances, ramps, cutwater slopes, tree planting, and bank grade are inferred. Generic riverside context is provided for the visual setting; it does not reproduce the adjacent city parcel by parcel. The model does not claim to capture repairs, every crack, deformation, uneven courses, inscriptions, or present-day utility details.

## Geometry and materials

River openings and upper arcades are modeled holes, not black textures. River-vault spandrels use closed meshes above the intersection of transverse and longitudinal pointed profiles, preserving continuous headroom in the lower passage without Boolean modifiers. Pier passages are open. Radial arch bricks are separate solid components batched into mesh objects. Cornices and ledges have small bevels for grazing highlights.

Brick walls use procedural courses on metre-based projected UV coordinates. Radial voussoirs use geometric joints and roughness rather than incorrectly applying horizontal courses around an arch. Noise, varying tones and a height-based damp zone create plausible surface variation. These are synthetic materials, not photogrammetric PBR captures. Some adjoining components overlap intentionally; this is a visual assembly, not a watertight fabrication mesh.

The water uses an animated shader and subtle geometric ripples. It is not CFD, a flood model, or a validated water-level scenario. Foundations and lighting are artistic approximations; no structural or conservation conclusion should be drawn from them.

## Validation

`python3 manage.py test` checks pointed-arch endpoints, crown height, symmetry and monotonicity; overall bay placement and clearances; finite vertices and two-face edge incidence on generated closed components; longitudinal headroom through intersecting vaults; and rejection of invalid geometry dimensions.

The Blender build additionally checks 33 uniquely numbered river spans, metric scale, finite scene mesh coordinates, UV layers, and camera presence. It writes scene counts and Blender version to `output/validation.json`. Render inspection is a separate visual check; passing geometry tests does not establish historical or metrological accuracy.

`python3 manage.py verify` reopens the saved artifact and checks external image dependencies, water animation, full-bridge camera framing, and a 260 m unobstructed ray along the lower-gallery centerline.

## Path to a measured digital twin

Higher precision requires a registered terrestrial LiDAR or photogrammetry survey, calibrated facade and intrados photographs, measured plans and sections, and control points tied to a defined coordinate reference system. Those would allow replacing repeated idealized bays with actual span geometry and baking captured surface detail onto the meshes. Live water, deformation, or environmental readings would require separately specified data connections. The current collection structure and parameter file provide a starting point for that work.
