# The Final Tower · 360° sales concept

Interactive off-plan sales demo by Ophira: photoreal orbit around the tower, clickable floors, unit cards with payment plans, shortlist/compare, WhatsApp handoff, a rules-based "Find my residence" guide and a 360° interior walk. Fictional project, not affiliated with any developer. All prices and availability are sample data.

Live: https://final-tower-360.vercel.app

## Run the site
```bash
cd web
npm install
npm run dev      # http://localhost:3360
npm test         # matching / payment tests
npm run build    # static export to web/out
```

## Where things are
- `web/app/data.ts`: sample inventory, payment plan, broker directory (`BROKERS`). The one source of truth for units and money.
- `web/app/match.ts`: guide logic (brief parsing, matching, no-match relaxations). Tested in `web/tests/`.
- `web/app/Experience.tsx`: page layout, panels, shortlist, compare, handoff.
- `web/app/Orbit.tsx`: 144-frame orbit, key photos, floor picking from `public/orbit/id` masks (red channel = floor × 7).
- `web/app/Tour.tsx`: three.js 360° panoramas.
- `web/app/Guide.tsx`: guide panel UI.
- `web/public/`: all published images (orbit frames, key photos, panoramas, stills, intro film).
- `_blender/*.py`: the Blender 4.5 scripts that built the scene (`exterior.py`, `interior.py`), the AI photoreal passes (`keys.py`, `segs.py`, `stills.py`, `pano_photo.py`; these need a Sunra account) and `publish.py`, which copies renders into `web/public`. The heavy renders and .blend files are not in the repo.

See `GUIDE-REPORT.md` for the latest changes, checks and a 90-second demo script.
