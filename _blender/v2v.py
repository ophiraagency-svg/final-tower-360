"""Photoreal 360 orbit: Blender orbit (even frames of day480) -> two 10 s halves -> Kling O3 video edit
-> 144 drag frames (2.5° apart) in renders/photo144.
python3 -I v2v.py encode | run | extract"""
import glob, json, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sj

HERE = os.path.dirname(os.path.abspath(__file__)); os.chdir(HERE)
FF = "/private/tmp/claude-501/-Users-makram--claude-spares-spare-IMF4dx/e9ec10ee-ed50-4c0d-8ac4-bdf3a5923e95/scratchpad/ff/node_modules/ffmpeg-static/ffmpeg"
FPS = 12          # 120 source frames per half -> 10 s
os.makedirs("v2v", exist_ok=True)

PROMPT = """Restyle this video into real, photorealistic aerial drone footage, matching the look of the reference photographs exactly: luxury residential towers with warm white aluminium frames, beige balcony slabs, glass balustrades, bronze-tinted glass with curtains and balcony furniture, rooftop gardens with palms, a podium of warm bronze vertical fins, a long water-curtain waterfall, turquoise pools with loungers and umbrellas, lush tropical planting and date palms, a terracotta running track and lawn along the promenade with people walking, the deep blue Arabian Gulf with sun glints, real Dubai Maritime City buildings and streets with cars, the Downtown Dubai skyline in the haze.
Keep the camera motion, the timing, the framing and every building's position, height, stepped blocks and frames EXACTLY as in the source video. Late-morning sun, slight haze. No text, no logos, no CGI look."""


def encode():
    fr = [f"renders/day480/{i:03d}.jpg" for i in range(0, 480, 2)]
    assert all(os.path.exists(f) for f in fr), "orbit not finished"
    for h, part in (("a", fr[:120]), ("b", fr[120:])):
        lst = f"v2v/{h}.txt"
        with open(lst, "w") as f:
            for p in part:
                f.write(f"file '{os.path.join(HERE, p)}'\nduration {1 / FPS}\n")
        subprocess.run([FF, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-r", str(FPS),
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16", "-vf", "scale=1280:720", f"v2v/src_{h}.mp4"], check=True)
        print("encoded", h)


def run():
    refs = [sj.upload(p) for p in ("keys/k0_ref.jpg", "keys/v1/k1_day.jpg", "keys/k4_day.jpg")]
    from concurrent.futures import ThreadPoolExecutor

    def one(h):
        out = f"v2v/photo_{h}.mp4"
        if os.path.exists(out):
            return out
        src = sj.upload(f"v2v/src_{h}.mp4")
        return sj.run("video", {"model": "gemini-omni-1.2-flash", "prompt": PROMPT, "source_video": src,
                                "reference_images": refs, "generate_audio": False}, out)
    halves = sys.argv[2] if len(sys.argv) > 2 else "ab"
    with ThreadPoolExecutor(2) as ex:
        print(list(ex.map(one, halves)))


def extract():
    os.makedirs("renders/photo144", exist_ok=True)
    for h, base in (("a", 0), ("b", 72)):
        src = f"v2v/photo_{h}.mp4"
        info = subprocess.run([FF, "-i", src], capture_output=True, text=True).stderr
        dur = [l for l in info.splitlines() if "Duration" in l][0].split("Duration: ")[1].split(",")[0]
        hh, mm, ss = dur.split(":"); D = int(hh) * 3600 + int(mm) * 60 + float(ss)
        for j in range(72):
            t = j * 2.5 / 180 * D        # angle j*2.5° inside this half
            subprocess.run([FF, "-y", "-loglevel", "error", "-ss", f"{t:.3f}", "-i", src, "-frames:v", "1", "-q:v", "2",
                            f"renders/photo144/{base + j:03d}.jpg"], check=True)
        print("extracted", h, D)


if __name__ == "__main__":
    {"encode": encode, "run": run, "extract": extract}[sys.argv[1]]()
