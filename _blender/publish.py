"""Copy renders and photos into web/public at web sizes. python3 publish.py [orbit_dir]"""
import os, sys, glob
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
PUB = os.path.join(HERE, "..", "web", "public")
orbit = sys.argv[1] if len(sys.argv) > 1 else "renders/day"
mask = sys.argv[2] if len(sys.argv) > 2 else "renders/id"


def save(src, dst, w, q=82):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.exists(dst) and os.path.getmtime(dst) > os.path.getmtime(src):
        return
    im = Image.open(src).convert("RGB")
    if im.width > w:
        im = im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
    im.save(dst, quality=q, optimize=True, progressive=True)


for f in sorted(glob.glob(os.path.join(HERE, orbit, "*.jpg"))):
    save(f, os.path.join(PUB, "orbit", "day", os.path.basename(f)), 1600, 74)
    save(f, os.path.join(PUB, "orbit", "day-s", os.path.basename(f)), 960, 72)
for f in sorted(glob.glob(os.path.join(HERE, "renders", "dusk144", "*.jpg"))):
    save(f, os.path.join(PUB, "orbit", "dusk", os.path.basename(f)), 1600, 74)
    save(f, os.path.join(PUB, "orbit", "dusk-s", os.path.basename(f)), 960, 72)
for f in sorted(glob.glob(os.path.join(HERE, mask, "*.png"))):
    dst = os.path.join(PUB, "orbit", "id", os.path.basename(f))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    Image.open(f).convert("RGB").getchannel("R").save(dst, optimize=True)
for f in [f for f in glob.glob(os.path.join(HERE, "keys", "k[0-7]_d*.jpg")) if "ref" not in f]:
    save(f, os.path.join(PUB, "keys", os.path.basename(f)), 2560, 82)
for f in glob.glob(os.path.join(HERE, "pano_photo", "pano_*.jpg")):
    save(f, os.path.join(PUB, "pano", os.path.basename(f)), 4096, 84)
for f in glob.glob(os.path.join(HERE, "stills", "*.jpg")):
    save(f, os.path.join(PUB, "stills", os.path.basename(f)), 2400, 84)
for d in ("orbit/day", "orbit/day-s", "orbit/dusk", "orbit/dusk-s", "orbit/id", "keys", "pano", "stills"):
    p = os.path.join(PUB, d)
    if os.path.isdir(p):
        n = sum(os.path.getsize(os.path.join(p, x)) for x in os.listdir(p))
        print(f"{d}: {len(os.listdir(p))} files, {n / 1e6:.1f} MB")

# horizontal focus per orbit frame: centre of the hero tower in the floor mask (0..1), used to crop on phones
import json
fs = sorted(glob.glob(os.path.join(PUB, "orbit", "id", "*.png")))
focus = []
for f in fs:
    m = Image.open(f).convert("L"); w, h = m.size; px = m.load()
    xs = [x for y in range(0, h, 4) for x in range(0, w, 4) if px[x, y] > 3]
    focus.append(round(sum(xs) / len(xs) / w, 3) if xs else 0.5)
json.dump(focus, open(os.path.join(PUB, "orbit", "focus.json"), "w"))
print("focus", focus[:8])
