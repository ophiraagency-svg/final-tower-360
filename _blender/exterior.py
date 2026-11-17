# Builds the Chelsea Residences-style waterfront complex procedurally and renders the 360 orbit.
# Run: Blender -b -P exterior.py -- MODE [start end]   MODE = preview | day | dusk | id
import bpy, bmesh, math, os, sys, random
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
MODE = argv[0] if argv else "preview"
F0 = int(argv[1]) if len(argv) > 1 else 0
F1 = int(argv[2]) if len(argv) > 2 else 0
NFRAMES = int(os.environ.get("NF", 72))
FLOOR_H = 3.4
random.seed(7)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

# ---------------------------------------------------------------- materials
def node_mat(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    return m, nt, out

def principled(name, color, rough=0.5, metal=0.0, emit=None, estr=0.0, alpha=1.0, coat=0.0):
    m, nt, out = node_mat(name)
    p = nt.nodes.new("ShaderNodeBsdfPrincipled")
    p.inputs["Base Color"].default_value = (*color, 1)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    p.inputs["Coat Weight"].default_value = coat
    if emit:
        p.inputs["Emission Color"].default_value = (*emit, 1)
        p.inputs["Emission Strength"].default_value = estr
    if alpha < 1:
        p.inputs["Alpha"].default_value = alpha
    nt.links.new(p.outputs[0], out.inputs[0])
    return m

NIGHT = MODE == "dusk"

def facade_glass():
    """Dark reflective glass with mullions and, at dusk, randomly lit warm rooms."""
    m, nt, out = node_mat("facade_glass")
    L = nt.links.new
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ"); L(tc.outputs["Object"], sep.inputs[0])

    def mull(axis, spacing, width):
        d = nt.nodes.new("ShaderNodeMath"); d.operation = "DIVIDE"; d.inputs[1].default_value = spacing
        L(sep.outputs[axis], d.inputs[0])
        f = nt.nodes.new("ShaderNodeMath"); f.operation = "FRACT"; L(d.outputs[0], f.inputs[0])
        c = nt.nodes.new("ShaderNodeMath"); c.operation = "LESS_THAN"; c.inputs[1].default_value = width
        L(f.outputs[0], c.inputs[0])
        return c
    mx, my = mull("X", 1.6, 0.05), mull("Y", 1.6, 0.05)
    mm = nt.nodes.new("ShaderNodeMath"); mm.operation = "MAXIMUM"
    L(mx.outputs[0], mm.inputs[0]); L(my.outputs[0], mm.inputs[1])

    glass = nt.nodes.new("ShaderNodeBsdfPrincipled")
    glass.inputs["Base Color"].default_value = (0.018, 0.028, 0.035, 1)
    glass.inputs["Roughness"].default_value = 0.04
    glass.inputs["Metallic"].default_value = 0.0
    glass.inputs["Coat Weight"].default_value = 0.0
    glass.inputs["Specular IOR Level"].default_value = 0.9
    if NIGHT:
        # room cell id -> noise -> warm light in ~55% of rooms
        sc = nt.nodes.new("ShaderNodeVectorMath"); sc.operation = "MULTIPLY"
        sc.inputs[1].default_value = (1 / 3.2, 1 / 3.2, 1 / FLOOR_H)
        L(tc.outputs["Object"], sc.inputs[0])
        fl = nt.nodes.new("ShaderNodeVectorMath"); fl.operation = "FLOOR"; L(sc.outputs[0], fl.inputs[0])
        wn = nt.nodes.new("ShaderNodeTexWhiteNoise"); wn.noise_dimensions = "3D"; L(fl.outputs[0], wn.inputs["Vector"])
        cr = nt.nodes.new("ShaderNodeValToRGB")
        cr.color_ramp.elements[0].position = 0.60; cr.color_ramp.elements[0].color = (0, 0, 0, 1)
        cr.color_ramp.elements[1].position = 0.64; cr.color_ramp.elements[1].color = (1, 1, 1, 1)
        L(wn.outputs["Value"], cr.inputs[0])
        hue = nt.nodes.new("ShaderNodeValToRGB")
        hue.color_ramp.elements[0].color = (1.0, 0.62, 0.32, 1)
        hue.color_ramp.elements[1].color = (1.0, 0.86, 0.68, 1)
        L(wn.outputs["Color"], hue.inputs[0]) if "Color" in wn.outputs else None
        mul = nt.nodes.new("ShaderNodeMixRGB"); mul.blend_type = "MULTIPLY"; mul.inputs[0].default_value = 1
        L(hue.outputs[0], mul.inputs[1]); L(cr.outputs[0], mul.inputs[2])
        L(mul.outputs[0], glass.inputs["Emission Color"])
        glass.inputs["Emission Strength"].default_value = 0.9
    frame = nt.nodes.new("ShaderNodeBsdfPrincipled")
    frame.inputs["Base Color"].default_value = (0.55, 0.52, 0.48, 1)
    frame.inputs["Roughness"].default_value = 0.35
    frame.inputs["Metallic"].default_value = 0.8
    mix = nt.nodes.new("ShaderNodeMixShader")
    L(mm.outputs[0], mix.inputs[0]); L(glass.outputs[0], mix.inputs[1]); L(frame.outputs[0], mix.inputs[2])
    L(mix.outputs[0], out.inputs[0])
    return m

def stripes_mat(name, base, dark, spacing, width, axis="X", rough=0.6):
    m, nt, out = node_mat(name)
    L = nt.links.new
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ"); L(tc.outputs["Object"], sep.inputs[0])
    add = nt.nodes.new("ShaderNodeMath"); add.operation = "ADD"
    L(sep.outputs["X"], add.inputs[0]); L(sep.outputs["Y"], add.inputs[1])
    d = nt.nodes.new("ShaderNodeMath"); d.operation = "DIVIDE"; d.inputs[1].default_value = spacing
    L(add.outputs[0], d.inputs[0])
    f = nt.nodes.new("ShaderNodeMath"); f.operation = "FRACT"; L(d.outputs[0], f.inputs[0])
    c = nt.nodes.new("ShaderNodeMath"); c.operation = "LESS_THAN"; c.inputs[1].default_value = width
    L(f.outputs[0], c.inputs[0])
    mx = nt.nodes.new("ShaderNodeMixRGB"); L(c.outputs[0], mx.inputs[0])
    mx.inputs[1].default_value = (*base, 1); mx.inputs[2].default_value = (*dark, 1)
    p = nt.nodes.new("ShaderNodeBsdfPrincipled"); p.inputs["Roughness"].default_value = rough
    L(mx.outputs[0], p.inputs["Base Color"])
    if NIGHT:
        p.inputs["Emission Color"].default_value = (1.0, 0.6, 0.3, 1)
        L(c.outputs[0], p.inputs["Emission Strength"])  # warm light between fins
    L(p.outputs[0], out.inputs[0])
    return m

def water_mat(name, color, rough=0.02, scale=0.06, strength=0.12):
    m, nt, out = node_mat(name)
    L = nt.links.new
    p = nt.nodes.new("ShaderNodeBsdfPrincipled")
    p.inputs["Base Color"].default_value = (*color, 1)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Specular IOR Level"].default_value = 0.6
    tc = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise"); noise.inputs["Scale"].default_value = scale
    noise.inputs["Detail"].default_value = 8
    L(tc.outputs["Object"], noise.inputs["Vector"])
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = strength
    L(noise.outputs["Fac"], bump.inputs["Height"]); L(bump.outputs[0], p.inputs["Normal"])
    L(p.outputs[0], out.inputs[0])
    return m

M = {
    "glass": facade_glass(),
    "slab": principled("slab", (0.74, 0.68, 0.6) if not NIGHT else (0.32, 0.29, 0.26), 0.5),
    "context": stripes_mat("context", (0.5, 0.48, 0.45), (0.08, 0.09, 0.1), 3.6, 0.45),
    "road": principled("road", (0.08, 0.08, 0.085), 0.85),
    "frame": principled("frame", (0.86, 0.84, 0.8) if not NIGHT else (0.5, 0.48, 0.45), 0.35),
    "led": principled("led", (0.3, 0.9, 0.85), 0.3, emit=(0.25, 1.0, 0.9), estr=10.0 if NIGHT else 0.0),
    "core": principled("core", (0.16, 0.17, 0.18), 0.6),
    "rail": principled("rail", (0.6, 0.7, 0.72), 0.05, alpha=0.25),
    "podium": stripes_mat("podium", (0.70, 0.55, 0.38), (0.25, 0.18, 0.12), 2.2, 0.35),
    "paving": principled("paving", (0.5, 0.47, 0.42), 0.8),
    "promenade": principled("promenade", (0.62, 0.36, 0.33), 0.8),
    "sand": principled("sand", (0.86, 0.78, 0.62), 0.95),
    "grass": principled("grass", (0.12, 0.28, 0.06), 0.9),
    "sea": water_mat("sea", (0.01, 0.07, 0.09), 0.09, 0.9, 0.35),
    "pool": water_mat("pool", (0.0, 0.25, 0.55), 0.03),
    "falls": principled("falls", (0.85, 0.95, 1.0), 0.2, emit=(0.6, 0.9, 1.0), estr=4.0 if NIGHT else 0.4),
    "city": principled("city", (0.55, 0.62, 0.72) if not NIGHT else (0.03, 0.04, 0.06), 0.6,
                       emit=(0.9, 0.7, 0.45), estr=0.0 if not NIGHT else 0.6),
    "trunk": principled("trunk", (0.32, 0.25, 0.18), 0.9),
    "frond": principled("frond", (0.09, 0.22, 0.05), 0.6),
    "hull": principled("hull", (0.95, 0.95, 0.95), 0.2),
    "black": principled("black", (0, 0, 0), 1.0),
}

# ---------------------------------------------------------------- mesh helpers
class Builder:
    """Accumulates boxes per material into one mesh; stores a per-face floor id (0 = none)."""
    def __init__(self, name):
        self.name, self.bm, self.mats = name, bmesh.new(), []
        self.flayer = self.bm.faces.layers.int.new("floor")

    def mat_index(self, mat):
        if mat not in self.mats:
            self.mats.append(mat)
        return self.mats.index(mat)

    def box(self, c, s, mat, floor=0):
        geom = bmesh.ops.create_cube(self.bm, size=1.0)
        vs = geom["verts"]
        for v in vs:
            v.co = Vector((c[0] + v.co.x * s[0], c[1] + v.co.y * s[1], c[2] + v.co.z * s[2]))
        idx = self.mat_index(mat)
        for f in {f for v in vs for f in v.link_faces}:
            f.material_index = idx
            f[self.flayer] = floor

    def finish(self, loc=(0, 0, 0), rot=0.0):
        me = bpy.data.meshes.new(self.name)
        self.bm.to_mesh(me); self.bm.free()
        for mt in self.mats:
            me.materials.append(M[mt])
        ob = bpy.data.objects.new(self.name, me)
        ob.location = loc; ob.rotation_euler.z = rot
        scene.collection.objects.link(ob)
        return ob

# ---------------------------------------------------------------- towers
def tower(name, loc, rot, w, d, floors, blocks, shifts, slim=False, hero=False):
    """Stacked offset blocks, each wrapped in a white frame with an LED line, balconies per floor."""
    b = Builder(name)
    base = 16.0  # podium height
    core_w = w * 0.35 if not slim else w * 0.5
    b.box((0, 0, base + floors * FLOOR_H / 2), (core_w, d * 0.8, floors * FLOOR_H + 6), "core")
    fl = 0
    for bi, n in enumerate(blocks):
        sx = shifts[bi % len(shifts)]
        z0 = base + fl * FLOOR_H
        for k in range(n):
            fl += 1
            z = base + (fl - 1) * FLOOR_H
            hid = fl if hero else 0
            # interior glass volume (inset for balconies)
            b.box((sx, 0, z + FLOOR_H / 2), (w - 2.4, d - 3.2, FLOOR_H - 0.3), "glass", hid)
            # floor slab / balcony
            b.box((sx, 0, z + 0.15), (w, d, 0.3), "slab", hid)
            # balustrades on long facades
            for sy in (-1, 1):
                b.box((sx, sy * (d / 2 - 0.05), z + 0.85), (w - 0.4, 0.04, 1.1), "rail", hid)
        zt = base + fl * FLOOR_H
        hgt = zt - z0
        # frame: top / bottom bars + side posts, front and back
        fw = 0.9
        for sy in (-1, 1):
            yy = sy * (d / 2 + fw / 2)
            b.box((sx, yy, zt + 0.4), (w + 2 * fw, fw, 1.1), "frame")
            b.box((sx, yy, z0 + 0.4), (w + 2 * fw, fw, 0.8), "frame")
            b.box((sx, yy, z0 + 0.0), (w + 2 * fw, fw * 1.02, 0.12), "led")
            for sxp in (-1, 1):
                b.box((sx + sxp * (w / 2 + fw / 2), yy, z0 + hgt / 2 + 0.4), (fw, fw, hgt + 0.8), "frame")
        for sxp in (-1, 1):  # side faces of the frame (short facades)
            b.box((sx + sxp * (w / 2 + fw / 2), 0, zt + 0.4), (fw, d + 2 * fw, 1.1), "frame")
    # rooftop pergola + crown frame
    zt = base + fl * FLOOR_H
    sx = shifts[(len(blocks) - 1) % len(shifts)]
    b.box((sx, 0, zt + 0.3), (w, d, 0.6), "slab")
    for sxp in (-1, 1):
        for sy in (-1, 1):
            b.box((sx + sxp * (w / 2 - 0.6), sy * (d / 2 - 0.6), zt + 4.5), (1.2, 1.2, 8.4), "frame")
    for sy in (-1, 1):
        b.box((sx, sy * (d / 2 - 0.6), zt + 8.5), (w, 1.2, 1.0), "frame")
    ob = b.finish(loc, rot)
    roof = [(Vector((sx + random.uniform(-w / 2 + 3, w / 2 - 3), random.uniform(-d / 2 + 2, d / 2 - 2), zt + 0.6)))
            for _ in range(int(w / 6))]
    mw = Matrix.Translation(Vector(loc)) @ Matrix.Rotation(rot, 4, "Z")
    world_roof = [mw @ p for p in roof]
    return ob, world_roof, zt

TOWERS = [
    # name, loc, rot, w, d, floors, blocks, shifts, slim
    ("T1", (-150, 95, 0), math.radians(90), 26, 22, 33, [6, 5, 6, 5, 6, 5], [0, -2.5, 1.5, -1, 2, 0], True),
    ("T2", (-95, 140, 0), math.radians(8), 62, 20, 29, [5, 6, 6, 6, 6], [0, 4, -3, 5, -2], False),
    ("T3", (-25, 150, 0), math.radians(-6), 30, 22, 31, [5, 5, 6, 5, 5, 5], [0, -3, 2, -2, 3, 0], True),
    ("T4", (20, 75, 0), math.radians(-38), 64, 20, 27, [5, 6, 5, 6, 5], [0, -4, 3, -5, 2], False),
    ("T5", (-70, 40, 0), math.radians(12), 28, 22, 25, [5, 5, 5, 5, 5], [0, 2, -2, 3, -1], True),
    ("T6", (85, 5, 0), math.radians(-62), 70, 21, 33, [6, 5, 6, 5, 6, 5], [0, 5, -4, 6, -3, 4], False),
]
HERO = "T6"
roof_spots, hero_top = [], 0
for t in TOWERS:
    t = list(t); t[7] = [v * 0.5 for v in t[7]]
    ob, rs, zt = tower(*t, hero=(t[0] == HERO))
    roof_spots += rs
    if t[0] == HERO:
        hero_top = zt

# ---------------------------------------------------------------- site
def poly_slab(name, pts, z0, z1, mat):
    bm = bmesh.new()
    bot = [bm.verts.new((x, y, z0)) for x, y in pts]
    top = [bm.verts.new((x, y, z1)) for x, y in pts]
    bm.faces.new(top)
    bm.faces.new(list(reversed(bot)))
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((bot[i], bot[j], top[j], top[i]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    me.materials.append(M[mat])
    ob = bpy.data.objects.new(name, me); scene.collection.objects.link(ob)
    return ob

def rounded_rect(x0, y0, x1, y1, r, seg=10):
    pts = []
    corners = [(x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)]
    for cx, cy, a0 in corners:
        for i in range(seg + 1):
            a = math.radians(a0 + 90 * i / seg)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts

land = rounded_rect(-420, -70, 170, 900, 90)
poly_slab("land", land, -2, 1.2, "paving")
poly_slab("sand", rounded_rect(-420, -88, 188, 520, 100), -2, 0.4, "sand")
promen = rounded_rect(-410, -62, 162, 520, 84)
poly_slab("promenade", promen, 1.2, 1.25, "promenade")
poly_slab("lawn", rounded_rect(-405, -48, 148, 520, 74), 1.25, 1.35, "grass")
poly_slab("plaza", rounded_rect(-400, -38, 138, 520, 66), 1.35, 1.45, "paving")
# podium with lit fins, waterfall wall facing the sea, pool deck on top
pod = rounded_rect(-185, -25, 125, 185, 30)
poly_slab("podium", pod, 1.4, 16.0, "podium")
poly_slab("deck", rounded_rect(-180, -20, 120, 180, 26), 16.0, 16.3, "paving")
poly_slab("pool", rounded_rect(-120, -10, 70, 30, 14), 16.3, 16.35, "pool")
poly_slab("pool2", rounded_rect(-60, 60, -10, 110, 10), 16.3, 16.35, "pool")
falls = Builder("falls")
falls.box((-25, -26.2, 9), (150, 0.6, 13), "falls")
falls.finish()

ctxb = Builder("context")
for gx in range(-400, 150, 70):
    for gy in range(230, 880, 70):
        if random.random() < 0.85 and (Vector((gx, gy)) - Vector((-10, 60))).length > 420:
            h = random.choice([random.uniform(12, 30), random.uniform(30, 75)])
            ctxb.box((gx + random.uniform(-6, 6), gy + random.uniform(-6, 6), 1.2 + h / 2),
                     (random.uniform(30, 50), random.uniform(30, 50), h), "context")
for gx in range(-420, 150, 70):
    ctxb.box((gx + 35, 560, 1.25), (12, 680, 0.1), "road")
for gy in range(230, 880, 70):
    ctxb.box((-135, gy - 35, 1.25), (570, 12, 0.1), "road")
ctxb.box((-135, 205, 1.25), (570, 16, 0.1), "road")
ctxb.finish()

# sea
bpy.ops.mesh.primitive_plane_add(size=30000, location=(0, 0, 0))
sea = bpy.context.object; sea.name = "sea"; sea.data.materials.append(M["sea"])

# ---------------------------------------------------------------- palms (one source, many instances)
def make_palm():
    b = bmesh.new()
    seg, h = 10, 11.0
    rings = []
    for i in range(seg + 1):
        t = i / seg
        r = 0.32 - 0.1 * t
        off = Vector((0.9 * t * t, 0, h * t))
        rings.append([b.verts.new(off + Vector((r * math.cos(a), r * math.sin(a), 0)))
                      for a in [2 * math.pi * k / 8 for k in range(8)]])
    for i in range(seg):
        for k in range(8):
            b.faces.new((rings[i][k], rings[i][(k + 1) % 8], rings[i + 1][(k + 1) % 8], rings[i + 1][k]))
    for f in b.faces:
        f.material_index = 0
    top = Vector((0.9, 0, h))
    for fi in range(14):
        ang = 2 * math.pi * fi / 14 + random.uniform(-0.2, 0.2)
        droop = random.uniform(0.35, 0.8)
        L = random.uniform(3.6, 4.6)
        dirv = Vector((math.cos(ang), math.sin(ang), 0))
        side = Vector((-math.sin(ang), math.cos(ang), 0))
        prev = None
        for s in range(10):
            t = s / 9
            p = top + dirv * (L * t) + Vector((0, 0, 1.0 * t - droop * L * t * t))
            wdt = 0.9 * math.sin(math.pi * min(t * 1.1, 1)) + 0.05
            a = b.verts.new(p + side * wdt + Vector((0, 0, -0.15 * wdt)))
            c = b.verts.new(p - side * wdt + Vector((0, 0, -0.15 * wdt)))
            m = b.verts.new(p)
            if prev:
                fa = b.faces.new((prev[0], prev[2], m, a)); fa.material_index = 1
                fc = b.faces.new((prev[2], prev[1], c, m)); fc.material_index = 1
            prev = (a, c, m)
    me = bpy.data.meshes.new("palm"); b.to_mesh(me); b.free()
    me.materials.append(M["trunk"]); me.materials.append(M["frond"])
    ob = bpy.data.objects.new("palm_src", me)
    return ob

palm_src = make_palm()
palm_col = bpy.data.collections.new("palm_col"); palm_col.objects.link(palm_src)

def palm_at(p, s=1.0):
    e = bpy.data.objects.new("palm", None)
    e.instance_type = "COLLECTION"; e.instance_collection = palm_col
    e.location = p; e.rotation_euler.z = random.uniform(0, 6.28); e.scale = (s, s, s)
    scene.collection.objects.link(e)

# along promenade (follow the rounded edge) + podium deck + rooftops
for i in range(0, len(promen), 1):
    x, y = promen[i]
    if y < 400 and x > -380:
        palm_at((x * 0.97, y * 0.97 + 6 if y < 0 else y, 1.4), random.uniform(1.2, 1.6))
for _ in range(70):
    x, y = random.uniform(-175, 115), random.uniform(-15, 175)
    palm_at((x, y, 16.3), random.uniform(1.0, 1.4))
for p in roof_spots:
    palm_at(p, random.uniform(0.6, 0.8))

# ---------------------------------------------------------------- yachts
yb = Builder("yachts")
for (x, y, r) in [(260, -260, 0.4), (420, -120, -0.3), (-200, -320, 1.2), (600, -420, 0.1)]:
    yb.box((x, y, 1.0), (22, 5.5, 2.4), "hull")
    yb.box((x - 2, y, 3.2), (11, 4.2, 2.0), "hull")
yb.finish()

# ---------------------------------------------------------------- distant skyline (Downtown across the water)
city = Builder("skyline")
center = Vector((3200, -6400, 0))
for i in range(260):
    a = random.uniform(-0.55, 0.55)
    dist = random.uniform(-900, 1200)
    p = center + Vector((math.cos(a) * 2600 + dist * 0.3, math.sin(a) * 900 + dist, 0))
    h = random.choice([random.uniform(60, 180), random.uniform(150, 320), random.uniform(250, 420)])
    wd = random.uniform(30, 70)
    city.box((p.x, p.y, h / 2), (wd, wd, h), "city")
# a tapering supertall
z, wdt = 0, 70.0
for k in range(16):
    hh = 52
    city.box((center.x, center.y, z + hh / 2), (wdt, wdt, hh), "city")
    z += hh; wdt *= 0.83
city.box((center.x, center.y, z + 45), (3, 3, 90), "city")
city.finish()

# ---------------------------------------------------------------- world / lights
world = bpy.data.worlds.new("w"); scene.world = world; world.use_nodes = True
wn = world.node_tree; L = wn.links.new
bg = wn.nodes["Background"]
env = wn.nodes.new("ShaderNodeTexEnvironment")
hdri = "qwantani_dusk_2_puresky.exr" if NIGHT else "kloofendal_48d_partly_cloudy_puresky.exr"
env.image = bpy.data.images.load(os.path.join(HERE, "hdri", hdri))
mp = wn.nodes.new("ShaderNodeMapping"); tc = wn.nodes.new("ShaderNodeTexCoord")
mp.inputs["Rotation"].default_value = (0, 0, math.radians(200 if not NIGHT else 120))
L(tc.outputs["Generated"], mp.inputs[0]); L(mp.outputs[0], env.inputs[0]); L(env.outputs[0], bg.inputs[0])
bg.inputs[1].default_value = 1.0 if not NIGHT else 0.22

sun = bpy.data.lights.new("sun", "SUN")
sun.energy = 3.0 if not NIGHT else 0.6
sun.angle = math.radians(1.2)
sun.color = (1.0, 0.95, 0.88) if not NIGHT else (1.0, 0.55, 0.35)
so = bpy.data.objects.new("sun", sun); scene.collection.objects.link(so)
so.rotation_euler = (math.radians(50 if not NIGHT else 84), 0, math.radians(35 if not NIGHT else 300))

# ---------------------------------------------------------------- camera orbit
TARGET = Vector((-10, 60, 55))
cam_d = bpy.data.cameras.new("cam"); cam_d.lens = 26; cam_d.clip_end = 20000
cam = bpy.data.objects.new("cam", cam_d); scene.collection.objects.link(cam); scene.camera = cam
tgt = bpy.data.objects.new("tgt", None); tgt.location = TARGET; scene.collection.objects.link(tgt)
con = cam.constraints.new("TRACK_TO"); con.target = tgt
con.track_axis = "TRACK_NEGATIVE_Z"; con.up_axis = "UP_Y"
R, H = 340.0, 105.0
def cam_at(i):
    a = math.radians(-70 + 360 * i / NFRAMES)  # frame 0 looks from the sea at the hero tower
    cam.location = (TARGET.x + R * math.cos(a), TARGET.y + R * math.sin(a), H)

# ---------------------------------------------------------------- render settings
r = scene.render
r.resolution_x, r.resolution_y = (1920, 1080) if MODE != "preview" else (960, 540)
if NFRAMES != 72 and MODE == "day":
    r.resolution_x, r.resolution_y = 1280, 720
r.resolution_percentage = 100
r.image_settings.file_format = "JPEG"; r.image_settings.quality = 88
for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    try:
        r.engine = eng; break
    except TypeError:
        pass
ee = scene.eevee
ee.taa_render_samples = 64 if MODE != "preview" else 16
ee.use_raytracing = True
try:
    ee.ray_tracing_options.resolution_scale = "2"
    ee.use_shadows = True
except Exception:
    pass
vs = scene.view_settings
try:
    vs.view_transform = "AgX"; vs.look = "AgX - Medium High Contrast"
except TypeError:
    vs.view_transform = "Filmic"
vs.exposure = -0.45 if not NIGHT else -0.2

if MODE == "id":
    # floor id pass: hero tower faces coloured by floor (value floor*7 in red), everything else black
    r.engine = "BLENDER_WORKBENCH"
    sh = scene.display.shading
    sh.light = "FLAT"; sh.color_type = "VERTEX"
    scene.display.render_aa = "OFF"
    vs.view_transform = "Standard"; vs.look = "None"; vs.exposure = 0; vs.gamma = 1
    r.image_settings.file_format = "PNG"; r.image_settings.color_mode = "RGB"
    r.resolution_x, r.resolution_y = 960, 540
    world.color = (0, 0, 0)
    for ob in list(scene.objects):
        if ob.type != "MESH" and ob.instance_type != "COLLECTION":
            continue
        if ob.type == "MESH":
            me = ob.data
            ca = me.color_attributes.new("Col", "BYTE_COLOR", "CORNER")
            fa = me.attributes.get("floor") if ob.name == HERO else None
            for poly in me.polygons:
                fv = fa.data[poly.index].value if fa else 0
                v = (fv * 7) / 255.0
                for li in poly.loop_indices:
                    ca.data[li].color_srgb = (v, 0, 0, 1) if hasattr(ca.data[li], "color_srgb") else (v, 0, 0, 1)
    pc = palm_src.data.color_attributes.new("Col", "BYTE_COLOR", "CORNER")
    for d in pc.data:
        d.color = (0, 0, 0, 1)

outdir = os.path.join(HERE, "renders", MODE + ("" if NFRAMES == 72 else str(NFRAMES)))
os.makedirs(outdir, exist_ok=True)
frames = [F0] if MODE == "preview" and F1 == 0 else range(F0, (F1 or NFRAMES - 1) + 1, int(os.environ.get("STEP", 1)))
for i in frames:
    cam_at(i)
    r.filepath = os.path.join(outdir, f"{i:03d}")
    bpy.ops.render.render(write_still=True)
    print("FRAME", i, flush=True)
if NFRAMES == 72:
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, f"exterior_{MODE}.blend"))
