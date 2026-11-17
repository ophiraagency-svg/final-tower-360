"""Photoreal equirect panorama: wrap-pad 2:1 -> 21:9, Nano Banana restyle, crop back, blend the wrap seam.
python3 -I pano_photo.py living[,kitchen,...]"""
import os, sys
import numpy as np
from PIL import Image
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sj
os.chdir(os.path.dirname(os.path.abspath(__file__)))
os.makedirs("pano_photo", exist_ok=True)

W, H = 3072, 1536
PADW = round(H * 21 / 9) - W  # total horizontal padding
P = PADW // 2

PROMPT = """This is a 360-degree equirectangular panorama of an apartment interior (with wrap-around margins on both sides). Image-to-image: make it a real photograph while keeping the EXACT equirectangular projection: every curved line, the curved ceiling cove, the window wall, the room layout and the position of every object must stay exactly where they are. Do not straighten lines, do not recompose, do not crop or zoom.
Materials: contemporary luxury Dubai residence on the 30th floor; large-format warm white marble floor; warm oak joinery; soft limestone-coloured plaster walls; ivory boucle upholstery; cream wool rugs; sheer linen curtains; opal glass and brass pendant lights; warm hidden cove light; late-afternoon sunlight with soft shadows. Through the glass: the real Arabian Gulf and the Downtown Dubai skyline with the Burj Khalifa, as in the input.
Real 360 camera photograph, natural colour, true-to-life textures, no CGI look, no text, no watermark."""


NIGHT = """This is a 360-degree equirectangular panorama of an apartment interior (with wrap-around margins on both sides). Image-to-image: the SAME panorama photographed at blue hour, twenty minutes after sunset. Keep the EXACT equirectangular projection, the room, every object and every line exactly where they are; only change the light.
Outside the glass: deep blue dusk sky with a warm afterglow on the horizon and the Downtown Dubai skyline lit up, the Burj Khalifa glowing, lights reflecting on the sea. Inside: warm cove lights and pendant lights on, soft lamplight pools on the marble floor, cosy evening atmosphere, gentle reflections of the room in the glass.
Real 360 camera photograph, natural colour, no CGI look, no text, no watermark."""
MODE = os.environ.get("MODE", "day")


def one(name):
    out = f"pano_photo/pano_{name}" + ("_night" if MODE == "night" else "") + ".jpg"
    if os.path.exists(out):
        return out
    srcp = f"pano_photo/pano_{name}.jpg" if MODE == "night" else f"renders/interior/pano_{name}.jpg"
    src = Image.open(srcp).convert("RGB").resize((W, H), Image.LANCZOS)
    a = np.asarray(src)
    padded = np.concatenate([a[:, W - P:], a, a[:, :PADW - P]], axis=1)
    inp = f"pano_photo/in_{name}_{MODE}.jpg"
    Image.fromarray(padded).save(inp, quality=92)
    raw = f"pano_photo/raw_{name}" + ("_night" if MODE == "night" else "") + ".jpg"
    if not os.path.exists(raw):
        sj.image(NIGHT if MODE == "night" else PROMPT, [inp], raw, ar="21:9")
    o = np.asarray(Image.open(raw).convert("RGB").resize(padded.shape[1::-1], Image.LANCZOS)).astype(np.float32)
    keep = o[:, P:P + W].copy()
    left_pad = o[:, :P]                      # = content just before the left edge = the right end of the panorama
    band = P
    t = np.linspace(0, 1, band)[None, :, None]
    keep[:, W - band:] = keep[:, W - band:] * (1 - t) + left_pad * t   # right end eases into what sits left of the left edge
    Image.fromarray(keep.clip(0, 255).astype(np.uint8)).resize((4096, 2048), Image.LANCZOS).save(out, quality=90)
    return out


def _safe(n):
    try:
        return one(n)
    except Exception as e:
        return f"ERR {e}"[:300]


if __name__ == "__main__":
    names = sys.argv[1].split(",")
    with ThreadPoolExecutor(4) as ex:
        for n, r in zip(names, ex.map(lambda n: _safe(n), names)):
            print(n, r, flush=True)

