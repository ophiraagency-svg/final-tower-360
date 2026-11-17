"""Tiny Sunra CLI wrapper: upload local images, run image/video jobs, download results.
usage (as module): from sj import upload, image, video
"""
import json, os, subprocess, sys, time

S = os.path.expanduser("~/.local/bin/sunra")
HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "sunra_state.json")
LEDGER = os.path.join(HERE, "sunra_ledger.txt")


def call(tool, args, spend=False):
    cmd = [S, "call", tool, json.dumps(args)] + (["--yes"] if spend else [])
    out = subprocess.run(cmd, capture_output=True, text=True)
    txt = out.stdout.strip()
    try:
        return json.JSONDecoder(strict=False).raw_decode(txt)[0]
    except Exception:
        raise RuntimeError(f"{tool} failed: {txt[:800]} {out.stderr[:400]}")


def state():
    return json.load(open(STATE)) if os.path.exists(STATE) else {}


def save(st):
    json.dump(st, open(STATE, "w"), indent=1)


def project():
    st = state()
    if "project_id" not in st:
        r = call("create_project", {"name": "DAMAC 360 concept"})
        st["project_id"] = r.get("project_id") or r.get("id") or r["project"]["id"]
        save(st)
    return st["project_id"]


def upload(path):
    st = state(); up = st.setdefault("uploads", {})
    key = f"{path}:{os.path.getmtime(path)}"
    if key in up:
        return up[key]
    ct = {"png": "image/png", "mp4": "video/mp4"}.get(path.rsplit(".", 1)[-1], "image/jpeg")
    r = call("get_upload_url", {"content_type": ct, "filename": os.path.basename(path)})
    hdr = sum([["-H", f"{k}: {v}"] for k, v in (r.get("headers") or {}).items()], [])
    subprocess.run(["curl", "-sS", "-X", "PUT", "--data-binary", f"@{path}", *hdr, r["upload_url"]], check=True)
    up[key] = r["asset_url"]; save(st)
    return r["asset_url"]


def _wait(node_ids):
    while True:
        r = call("wait_for_nodes", {"project_id": project(), "node_ids": node_ids})
        if not r.get("still_running"):
            if r.get("failed"):
                raise RuntimeError(json.dumps(r)[:800])
            return r
        time.sleep(3)


def _urls(node):
    for k in ("output_urls", "urls", "outputs"):
        v = node.get(k)
        if v:
            return [x if isinstance(x, str) else x.get("url") for x in v]
    if node.get("output_url"):
        return [node["output_url"]]
    raise RuntimeError(f"no url in {json.dumps(node)[:600]}")


def _log(kind, out, credits):
    with open(LEDGER, "a") as f:
        f.write(f"{time.strftime('%H:%M')}\t{kind}\t{credits}\t{os.path.basename(out)}\n")


def run(kind, args, out):
    tool = "create_image" if kind == "image" else "create_video"
    r = call(tool, {"project_id": project(), "auto_confirm": True, **args}, spend=True)
    with open(os.path.join(HERE, "sunra_responses.log"), "a") as f:
        f.write(json.dumps({"out": out, "r": r}) + "\n")
    credits = r.get("estimated_credits") or r.get("credits") or r.get("maximum_credits")
    _log(kind, out, credits)
    ids = r.get("node_ids") or [n.get("node_id") or n.get("id") for n in r.get("nodes", [])]
    if ids and all(ids):
        return fetch(ids, out)
    tids = r.get("task_ids") or ([r["task_id"]] if r.get("task_id") else []) or [t.get("task_id") for t in r.get("tasks", [])]
    if not tids:
        raise RuntimeError("create returned no ids: " + json.dumps(r)[:900])
    return fetch_job(tids[0], out)


def fetch_job(tid, out):
    import re
    while True:
        try:
            r = call("get_job", {"task_id": tid})
        except RuntimeError as e:
            if "Rate-limited" in str(e) or "Couldn't reach" in str(e):
                time.sleep(35); continue
            raise
        st = str(r.get("status", "")).upper()
        if st in ("COMPLETED", "SUCCEEDED", "SUCCESS"):
            urls = re.findall(r'https://[^"\s]+\.(?:png|jpe?g|webp|mp4)', json.dumps(r))
            subprocess.run(["curl", "-sSL", "-o", out, urls[0]], check=True)
            return out
        if st in ("FAILED", "ERROR", "CANCELLED"):
            raise RuntimeError(json.dumps(r)[:800])
        time.sleep(5)


def fetch(ids, out):
    import re
    r = _wait(ids)
    urls = re.findall(r'https://cdn\.sunra\.ai/generations/[^"\s]+', json.dumps(r))
    if not urls:
        raise RuntimeError("no url: " + json.dumps(r)[:800])
    url = urls[0]
    subprocess.run(["curl", "-sSL", "-o", out, url], check=True)
    return out


def image(prompt, refs, out, model="nano-banana-2.1", res="4K", ar="16:9"):
    return run("image", {"prompt": prompt, "model": model, "resolution": res, "aspect_ratio": ar,
                         "image_urls": [upload(p) for p in refs], "output_format": "jpeg"}, out)


if __name__ == "__main__":
    print(project())
