"""Photoreal interiors from the Blender stills. python3 -I stills.py s_living,s_kitchen"""
import os, sys
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sj

os.chdir(os.path.dirname(os.path.abspath(__file__)))
os.makedirs("stills", exist_ok=True)

BASE = """Image-to-image: turn this 3D interior render into a real architectural interior photograph that aligns with the input. Keep the same camera position, lens, framing, room shape, window wall, ceiling cove, floor tiles and the position of every piece of furniture; do not recompose or zoom.
Upgrade the finishes to a contemporary luxury Dubai residence on the 30th floor: large-format warm white marble floor, warm oak joinery with fine grain, soft limestone-coloured plaster walls, sheer linen curtains moving slightly, warm hidden cove light, late-afternoon sun casting long soft shadows across the floor.
Through the floor-to-ceiling glass: the real view across the Arabian Gulf to the Downtown Dubai skyline with the Burj Khalifa, exactly as in the input.
Shot by an architectural photographer on a Canon EOS R5 with a 16-35mm lens at f/8, natural colour, true-to-life materials, subtle imperfections, no CGI look, no text, no logos, no watermark."""

ROOM = {
    "s_living": " The sofa is a contemporary curved sofa in ivory boucle with cushions; the armchair is walnut and black leather; a large cream wool rug; dining chairs in dark walnut and leather in the foreground; the glowing spheres are opal glass pendant lights.",
    "s_kitchen": " The tall cabinets are handleless oak; the island is book-matched white marble with a waterfall edge; brass pendant lights; walnut bar stools; a ceramic vase on the island.",
    "s_bedroom": " The bed has crisp white linen, an ivory boucle upholstered headboard and a textured throw; walnut bedside tables with opal glass lamps; a cream rug.",
    "s_balcony": " The terrace has a teak deck, a frameless glass balustrade, outdoor lounge chairs and potted olive trees.",
    "s_view": " Seen from the sofa towards the glass: the living room and the terrace with the sea view.",
}


def one(k):
    out = f"stills/{k}.jpg"
    if os.path.exists(out):
        return out
    return sj.image(BASE + ROOM[k], [f"renders/interior/{k}.jpg"], out)


def _safe(k):
    try:
        return one(k)
    except Exception as e:
        return f"ERR {e}"[:300]


if __name__ == "__main__":
    ks = sys.argv[1].split(",")
    with ThreadPoolExecutor(6) as ex:
        for k, r in zip(ks, ex.map(lambda k: _safe(k), ks)):
            print(k, r, flush=True)

