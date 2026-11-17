"""Photoreal key angles of the orbit: day from the Blender frames, dusk from the day photos.
python3 -I keys.py day|dusk [k,k,...]"""
import os, sys
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sj

os.chdir(os.path.dirname(os.path.abspath(__file__)))
KEYS = list(range(8))  # key k = orbit frame 9k

DAY = """Image-to-image restyle: turn this architectural massing render into a real aerial drone photograph that aligns pixel-for-pixel with the input. Same camera position, same lens, same framing and crop, same horizon line: do not zoom out, do not raise or tilt the camera, do not recompose. Keep every tower outline, height, stepped offset block and white frame EXACTLY where it is in the input; do not add, remove or move any building, pool or palm.
Indistinguishable from a real photograph taken with a DJI Mavic 3 Pro Hasselblad camera, late-morning Dubai sun, slight atmospheric haze.
Towers: luxury residential towers with warm white aluminium frames, light beige balcony slabs with glass balustrades, floor-to-ceiling bronze-tinted glass with curtains, furniture and plants on some balconies, rooftop gardens with palms. Podium: warm bronze vertical fins; the long white panel on the podium is a water-curtain waterfall. Pools: turquoise with sun loungers, umbrellas, a few swimmers. Deck: travertine with lush tropical planting and date palms. Promenade: terracotta running track, lawn, people walking. Sea: deep blue Arabian Gulf with ripples and sun glints. Grey blocks are real Dubai Maritime City mid-rise buildings with windows and streets with cars. Distant pale blocks on the horizon are the real Downtown Dubai skyline.
No text, no logos, no watermark, no CGI look, no plastic sheen."""

DUSK = """The same photograph at blue hour, twenty minutes after sunset. Keep the camera, framing, every building, palm, pool and the whole composition EXACTLY identical; only change the light.
Deep blue-violet sky with a warm amber afterglow low on the horizon; warm interior lights glowing in roughly half of the apartments, some curtains drawn; a thin cyan LED line glowing along the bottom of each white frame; podium fins washed in warm light; the waterfall lit from below; pools glowing turquoise; promenade lamps and palm uplights on; reflections of lights on the calm sea; city lights twinkling in the distance.
Indistinguishable from a real long-exposure drone photograph. No text, no logos, no watermark, no CGI look."""


def day(k):
    out = f"keys/k{k}_day.jpg"
    if os.path.exists(out):
        return out
    return sj.image(DAY, [f"renders/day/{9 * k:03d}.jpg"], out)


def dusk(k):
    out = f"keys/k{k}_dusk.jpg"
    if os.path.exists(out):
        return out
    return sj.image(DUSK, [f"keys/k{k}_day.jpg"], out)



def _safe(fn, k):
    try:
        return fn(k)
    except Exception as e:
        return f"ERR {e}"[:300]


if __name__ == "__main__":
    fn = {"day": day, "dusk": dusk}[sys.argv[1]]
    ks = [int(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else KEYS
    with ThreadPoolExecutor(8) as ex:
        for r in ex.map(lambda k: (k, _safe(fn, k)), ks):
            print(r, flush=True)

