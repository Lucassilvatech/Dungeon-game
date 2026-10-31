# Web0.9: original pixel worlds, directional actors and connected building entrances

Draft against `feature/autonomous-npc-economy-0.9`.

The existing Web world used simple generated shapes and a fixed-resolution camera. This change ships original PNG atlases, consistent village/ruins/crypt/ritual themes, directional actors and four independent boss appearances. Existing gameplay/economy/coordinates remain server-authoritative. Building paths now meet actual doors and clicking the painted facade resolves to the existing authorized exit.

Static terrain batches once per room; tall objects and actors use foot depth, with protected paths/doors/spawns/services/resources and a clear arena. Bounded animated torches/glows/shadows/particles, crisp responsive viewport and Canvas fallback for software WebGL. Godot and Discord source remain unchanged.

Validation: one complete PostgreSQL17 backend run339passed,0failed,0skipped,2warnings,1003.34s; frontend22passed; TypeScript/Vite build PASS; four real Chromium suites PASS (visual, smoke, NPC chain, encounters). Five scenes captured at1280/1920/390px; real facade entry tested desktop/mobile; Canvas60FPS in sampled scenes.16 screenshots and metrics in artifacts/visual-review. Alembic upgrade/check on fresh private DBs; no new migration or operational bank write.

See docs/DELIVERY_PIXEL_ART_0.9.md and docs/PIXEL_ART_LOCAL_WINDOWS.md. Pending user art approval, physical GPU/mobile/Windows validation and deployment. GitHub Actions updated but not observed remotely. No merge requested.
