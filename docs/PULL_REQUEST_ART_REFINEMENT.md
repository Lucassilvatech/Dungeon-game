# Refine Web art directly from the user reference and enforce safe decorative placement

Draft against `feature/pixel-art-visual-overhaul-0.9`.

The previous visual layer had narrow generic actors, noisy terrain and legacy prop/wall placement bypasses. This change reconstructs the square-headed characters directly from the supplied reference, preserves their blue/green/purple/brown clothing, and composes clean village/ruins/boss surfaces with grouped detail.9:16 applies only to the requested reference image; gameplay viewport stays responsive.

Explicit zones validate complete visual footprints, remove unvalidated legacy rendering paths and contextualize interior furniture. Paths still meet real building doors, with actual sprite-body click/touch mapped to existing server operations. Terrain/actors use the established batched renderer, bounded lighting and software-GPU Canvas fallback.

Migration65a7c9e21b04 clears only identified legacy decorative city collision tiles, preserving structures, all actors/progress and finance. New audit records exactly which tiles changed. Representative private-copy hashes preserved55 nonspatial tables/940 rows;31 decorative tiles repaired; Lunar audit gap0. No operational database access, no reset/cutover repeat.

Validation evidence and final complete-suite results: docs/ART_REFINEMENT_DELIVERY_0.9.md. Frontend26passed/build PASS;250 real layouts/2027 props audited with0 violations; four Chromium scripts PASS, including body click/touch, trading/NPC production/combat/reconnect.16 screenshots and performance in artifacts/art-refinement. CI updated but remote run not observed.

Windows commands/backup/migration in docs/ART_REFINEMENT_LOCAL_WINDOWS.md. Discord remains read-only; Godot frozen. Pending user visual acceptance, physical-device validation and deployment. No merge requested.
