"""seg/{pre}s0..7.mp4 -> renders/{photo|dusk}144/000..143.jpg (18 frames per 45° segment)."""
import os, subprocess, sys
FF = "/private/tmp/claude-501/-Users-makram--claude-spares-spare-IMF4dx/e9ec10ee-ed50-4c0d-8ac4-bdf3a5923e95/scratchpad/ff/node_modules/ffmpeg-static/ffmpeg"
os.chdir(os.path.dirname(os.path.abspath(__file__)))
mode = sys.argv[1] if len(sys.argv) > 1 else "day"
pre, dst = ("", "renders/photo144") if mode == "day" else ("d", "renders/dusk144")
os.makedirs(dst, exist_ok=True)
for k in range(8):
    src = f"seg/{pre}s{k}.mp4"
    # 96 frames at 24 fps; take 18 evenly spaced (the 19th would be the next key)
    pass
    for j in range(18):
        t = j / 18 * 4.0
        subprocess.run([FF, "-y", "-loglevel", "error", "-ss", f"{t:.4f}", "-i", src, "-frames:v", "1", "-vf", "scale=1920:1080",
                        "-q:v", "3", f"{dst}/{18 * k + j:03d}.jpg"], check=True)
    print("seg", k, flush=True)
