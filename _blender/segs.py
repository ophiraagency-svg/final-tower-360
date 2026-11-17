"""Photoreal orbit by interpolating between neighbouring key photos with Veo 3.1 Fast (first + last frame).
python3 -I segs.py day|dusk"""
import os, sys
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sj
os.chdir(os.path.dirname(os.path.abspath(__file__)))
from PIL import Image

P = ("Real aerial drone footage. One smooth continuous orbit: the drone circles around the residential towers at a constant height and "
     "constant distance, always aimed at the centre of the complex, moving steadily from the first frame to the last frame with no zoom, "
     "no cut and no change of altitude. The towers, pools, waterfall, palms and promenade stay exactly the same buildings throughout; "
     "nothing appears or disappears. {light} No text.")
LIGHT = {"day": "Gentle sun glints on the sea, palms moving slightly, people walking.",
         "dusk": "Blue hour: apartment lights glowing, pools lit turquoise, lights reflecting on the calm sea, city lights twinkling."}
mode = sys.argv[1]
pre = "" if mode == "day" else "d"


def ref(k):
    src, dst = f"keys/k{k}_{mode}.jpg", f"keys/k{k}_{mode}_ref2.jpg"
    if mode == "day":
        dst = f"keys/k{k}_ref2.jpg"
    if not os.path.exists(dst):
        im = Image.open(src).convert("RGB"); im.resize((2048, round(im.height * 2048 / im.width))).save(dst, quality=88)
    return dst


def one(k):
    out = f"seg/{pre}s{k}.mp4"
    if os.path.exists(out):
        return out
    a, b = sj.upload(ref(k)), sj.upload(ref((k + 1) % 8))
    return sj.run("video", {"model": os.environ.get("VM", "veo-3.1-fast"), "duration": 4, **({"resolution": "1080p"} if os.environ.get("VM", "veo-3.1-fast").startswith("veo") else {}), "prompt": P.format(light=LIGHT[mode]),
                            "start_image": a, "end_image": b, "generate_audio": False, "aspect_ratio": "16:9"}, out)


def safe(k):
    try:
        return one(k)
    except Exception as e:
        return f"ERR {e}"[:300]


with ThreadPoolExecutor(8) as ex:
    for k, r in zip(range(8), ex.map(safe, range(8))):
        print(k, r, flush=True)
