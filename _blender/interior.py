# Sea-facing 2-bed apartment, floor 30 of the hero tower. Renders Cycles 360 panoramas + 16:9 stills.
# Run: Blender -b -P interior.py -- MODE [names]   MODE = pano | still | test
import bpy, bmesh, math, os, sys, random
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
MODE = argv[0] if argv else "test"
ONLY = argv[1].split(",") if len(argv) > 1 else None
A = os.path.join(HERE, "assets")
random.seed(3)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
W, D, CH = 11.0, 9.0, 3.0      # unit width (x), depth (y), ceiling height; glass at y=0, sea at -y
BAL = 2.3                       # balcony depth

# ---------------------------------------------------------------- materials
def mat(name, color=(0.8, 0.8, 0.8), rough=0.5, metal=0.0, tex=None, scale=1.0, emit=None, estr=0.0,
        transmission=0.0, alpha=1.0, normal=0.6, sheen=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; p = nt.nodes["Principled BSDF"]; L = nt.links.new
    p.inputs["Base Color"].default_value = (*color, 1)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    p.inputs["Transmission Weight"].default_value = transmission
    p.inputs["Sheen Weight"].default_value = sheen
    if alpha < 1:
        p.inputs["Alpha"].default_value = alpha
    if emit:
        p.inputs["Emission Color"].default_value = (*emit, 1)
        p.inputs["Emission Strength"].default_value = estr
    if tex:
        d = os.path.join(A, "tex", tex)
        tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping")
        mp.inputs["Scale"].default_value = (scale, scale, scale)
        L(tc.outputs["Object"], mp.inputs[0])
        def img(fn, data):
            fp = os.path.join(d, fn)
            if not os.path.exists(fp):
                return None
            n = nt.nodes.new("ShaderNodeTexImage"); n.image = bpy.data.images.load(fp)
            n.projection = "BOX"; n.projection_blend = 0.2
            if data:
                n.image.colorspace_settings.name = "Non-Color"
            L(mp.outputs[0], n.inputs[0]); return n
        dif = img("diff.jpg", False)
        if dif:
            if color != (0.8, 0.8, 0.8):
                mx = nt.nodes.new("ShaderNodeMixRGB"); mx.blend_type = "MULTIPLY"; mx.inputs[0].default_value = 1
                L(dif.outputs[0], mx.inputs[1]); mx.inputs[2].default_value = (*color, 1)
                L(mx.outputs[0], p.inputs["Base Color"])
            else:
                L(dif.outputs[0], p.inputs["Base Color"])
        rg = img("rough.jpg", True)
        if rg:
            mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs[3].default_value = rough * 0.5
            mr.inputs[4].default_value = min(1, rough * 1.5)
            L(rg.outputs[0], mr.inputs[0]); L(mr.outputs[0], p.inputs["Roughness"])
        nm = img("nor_gl.jpg", True)
        if nm:
            nn = nt.nodes.new("ShaderNodeNormalMap"); nn.inputs[0].default_value = normal
            L(nm.outputs[0], nn.inputs[1]); L(nn.outputs[0], p.inputs["Normal"])
    return m

MT = {
    "floor": mat("floor", (0.95, 0.93, 0.9), 0.18, tex="marble_01", scale=0.35, normal=0.15),
    "wall": mat("wall", (0.93, 0.91, 0.87), 0.85, tex="plastered_wall", scale=0.6, normal=0.25),
    "ceiling": mat("ceiling", (0.95, 0.94, 0.92), 0.9),
    "oak": mat("oak", (0.95, 0.85, 0.72), 0.45, tex="oak_veneer_01", scale=0.8, normal=0.3),
    "oakdark": mat("oakdark", (0.55, 0.45, 0.38), 0.45, tex="grey_oak_veneer_01", scale=0.8, normal=0.3),
    "stone": mat("stone", (1.0, 0.98, 0.95), 0.12, tex="marble_01", scale=0.5, normal=0.1),
    "linen": mat("linen", (0.93, 0.91, 0.87), 0.9, tex="rough_linen", scale=2.5, normal=0.5, sheen=0.4),
    "boucle": mat("boucle", (0.78, 0.72, 0.64), 0.95, tex="rough_linen", scale=4.0, normal=0.8, sheen=0.6),
    "rug": mat("rug", (1.0, 0.97, 0.9), 0.95, tex="rough_linen", scale=1.5, normal=1.0, sheen=0.5),
    "brass": mat("brass", (0.85, 0.66, 0.4), 0.25, metal=1.0),
    "black": mat("blackmetal", (0.03, 0.03, 0.03), 0.35, metal=0.9),
    "glass": mat("glass", (1, 1, 1), 0.0, transmission=1.0),
    "sheer": mat("sheer", (0.97, 0.96, 0.93), 0.8, alpha=0.55, sheen=0.3),
    "led": mat("led", (1, 1, 1), 0.5, emit=(1.0, 0.82, 0.62), estr=6.0),
    "slab": mat("slab", (0.86, 0.84, 0.8), 0.4),
    "deck": mat("deck", (0.55, 0.42, 0.32), 0.6, tex="oak_veneer_01", scale=0.7, normal=0.5),
}

def view_mat():
    m = bpy.data.materials.new("view"); m.use_nodes = True
    nt = m.node_tree; L = nt.links.new
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission"); em.inputs[1].default_value = 1.6
    t = nt.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(os.path.join(HERE, "keys", "view_day.jpg"))
    t.extension = "MIRROR"
    uv = nt.nodes.new("ShaderNodeUVMap")
    L(uv.outputs[0], t.inputs[0]); L(t.outputs[0], em.inputs[0]); L(em.outputs[0], out.inputs[0])
    return m

# ---------------------------------------------------------------- geometry helpers
def box(name, c, s, m, bevel=0.0, seg=3):
    bpy.ops.mesh.primitive_cube_add(size=1, location=c)
    o = bpy.context.object; o.name = name; o.scale = s
    bpy.ops.object.transform_apply(scale=True)
    o.data.materials.append(MT[m] if isinstance(m, str) else m)
    if bevel:
        b = o.modifiers.new("bev", "BEVEL"); b.width = bevel; b.segments = seg
        bpy.ops.object.shade_smooth()
    return o

def gltf(name, loc, rot=0.0, scale=1.0, fit=None):
    """Import a Poly Haven glTF, sit it on z=loc.z, centred on loc. fit=(axis, metres) rescales."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(A, name, f"{name}.gltf"))
    new = [o for o in bpy.data.objects if o not in before]
    roots = [o for o in new if o.parent is None]
    piv = bpy.data.objects.new(name + "_piv", None); scene.collection.objects.link(piv)
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in new if o.type == "MESH" for c in o.bound_box]
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    base = Vector(((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, mn.z))
    for r in roots:
        r.location -= base
        r.parent = piv
    if fit:
        ax, metres = fit
        size = {"x": mx.x - mn.x, "y": mx.y - mn.y, "z": mx.z - mn.z}[ax]
        scale = metres / size
    piv.location = loc; piv.rotation_euler.z = rot; piv.scale = (scale,) * 3
    return piv

def recolor(piv, m):
    """Swap the upholstery: the biggest material slot of each mesh becomes m."""
    for o in piv.children_recursive:
        if o.type == "MESH" and o.material_slots:
            areas = {}
            for p in o.data.polygons:
                areas[p.material_index] = areas.get(p.material_index, 0) + p.area
            o.material_slots[max(areas, key=areas.get)].material = MT[m]
    return piv

# ---------------------------------------------------------------- shell
box("floor", (W / 2, D / 2, -0.05), (W, D, 0.1), "floor")
box("ceiling", (W / 2, D / 2, CH + 0.05), (W, D, 0.1), "ceiling")
box("wall_back", (W / 2, D + 0.1, CH / 2), (W, 0.2, CH), "wall")
box("wall_left", (-0.1, D / 2, CH / 2), (0.2, D, CH), "wall")
box("wall_right", (W + 0.1, D / 2, CH / 2), (0.2, D, CH), "wall")
# partition living | bedroom with door opening (y 6.2..7.2)
box("part_a", (7.05, 3.1, CH / 2), (0.14, 6.2, CH), "wall")
box("part_b", (7.05, 8.1, CH / 2), (0.14, 1.8, CH), "wall")
box("part_head", (7.05, 6.7, CH - 0.4), (0.14, 1.0, 0.8), "wall")
box("bed_back", (9.05, 5.6, CH / 2), (3.9, 0.14, CH), "wall")
# ceiling cove + LED line + downlights
for (c, s) in [((W / 2, 0.45, CH - 0.15), (W, 0.9, 0.3)), ((W / 2, D - 0.3, CH - 0.15), (W, 0.6, 0.3))]:
    box("cove", c, s, "ceiling")
box("led1", (W / 2, 0.92, CH - 0.29), (W, 0.03, 0.01), "led")
box("led2", (W / 2, D - 0.62, CH - 0.29), (W, 0.03, 0.01), "led")
# glazing: frame + glass panels + mullions
box("sill", (W / 2, 0.0, 0.02), (W, 0.12, 0.04), "black")
box("head", (W / 2, 0.0, CH - 0.02), (W, 0.12, 0.04), "black")
n_pan = 6
for i in range(n_pan + 1):
    box(f"mull{i}", (W * i / n_pan, 0.0, CH / 2), (0.06, 0.12, CH), "black")
g = box("glazing", (W / 2, 0.0, CH / 2), (W, 0.02, CH), "glass"); g.visible_shadow = False
# balcony
box("bal_slab", (W / 2, -BAL / 2, -0.15), (W + 0.6, BAL, 0.3), "slab")
box("bal_deck", (W / 2, -BAL / 2 + 0.1, 0.01), (W, BAL - 0.2, 0.02), "deck")
g = box("bal_rail", (W / 2, -BAL + 0.04, 0.55), (W + 0.6, 0.02, 1.1), "glass"); g.visible_shadow = False
box("bal_cap", (W / 2, -BAL + 0.04, 1.11), (W + 0.6, 0.06, 0.03), "black")
box("bal_frame_t", (W / 2, -BAL / 2, CH + 0.4), (W + 1.2, BAL + 0.2, 0.8), "slab")
for sx in (-0.4, W + 0.4):
    box("bal_side", (sx, -BAL / 2, CH / 2 + 0.2), (0.8, BAL + 0.2, CH + 0.4), "slab")

# ---------------------------------------------------------------- view backdrop (cylindrical photo of the Gulf + Downtown)
def backdrop():
    R, arc, eye = 420.0, math.radians(190), 1.6
    img_arc = math.radians(110)          # the photo's horizontal field of view
    vfov = img_arc * 2688 / 6336
    top, bot = eye + R * math.tan(vfov * 0.47), eye - R * math.tan(vfov * 0.53)
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new()
    n = 96; cx = W / 2
    cols = []
    for i in range(n + 1):
        a = -math.pi / 2 - arc / 2 + arc * i / n
        x, y = cx + R * math.cos(a), R * math.sin(a)
        u = 0.5 + (a + math.pi / 2) / img_arc
        cols.append((bm.verts.new((x, y, bot)), bm.verts.new((x, y, top)), u))
    for i in range(n):
        v0, v1, u0 = cols[i]; v2, v3, u1 = cols[i + 1]
        f = bm.faces.new((v0, v2, v3, v1))
        for lp, uv in zip(f.loops, [(u0, 0), (u1, 0), (u1, 1), (u0, 1)]):
            lp[uvl].uv = (1 - uv[0], uv[1])
    me = bpy.data.meshes.new("view"); bm.to_mesh(me); bm.free()
    me.materials.append(view_mat())
    o = bpy.data.objects.new("view", me); scene.collection.objects.link(o)
    o.visible_shadow = False
backdrop()

# ---------------------------------------------------------------- curtains (sheer, gathered at both ends of the glass)
def curtain(x0, width, folds=9):
    bm = bmesh.new(); n = folds * 8
    rows = []
    for z in (0.02, CH - 0.08):
        rows.append([bm.verts.new((x0 + width * i / n, 0.28 + 0.07 * math.sin(i / 8 * 2 * math.pi), z)) for i in range(n + 1)])
    for i in range(n):
        bm.faces.new((rows[0][i], rows[0][i + 1], rows[1][i + 1], rows[1][i]))
    me = bpy.data.meshes.new("curtain"); bm.to_mesh(me); bm.free()
    me.materials.append(MT["sheer"])
    o = bpy.data.objects.new("curtain", me); scene.collection.objects.link(o)
    for p in me.polygons:
        p.use_smooth = True
curtain(0.15, 1.1); curtain(5.6, 1.1); curtain(7.2, 1.0); curtain(W - 1.15, 1.0)
box("track", (W / 2, 0.28, CH - 0.06), (W, 0.04, 0.03), "black")

# ---------------------------------------------------------------- living
box("rug", (3.6, 2.7, 0.006), (3.6, 2.8, 0.012), "rug")
recolor(gltf("sofa_02", (3.6, 4.15, 0), rot=math.pi, fit=("x", 2.6)), "boucle")
gltf("modern_coffee_table_01", (3.6, 2.75, 0), fit=("x", 1.2))
recolor(gltf("modern_arm_chair_01", (1.75, 2.4, 0), rot=-math.pi / 2 - 0.35, fit=("z", 0.82)), "boucle")
recolor(gltf("modern_arm_chair_01", (5.45, 2.4, 0), rot=math.pi / 2 + 0.35, fit=("z", 0.82)), "boucle")
gltf("side_table_01", (2.05, 4.35, 0), fit=("z", 0.55))
gltf("ceramic_vase_01", (3.5, 2.75, 0.36), fit=("z", 0.28))
gltf("throw_pillows_01", (3.25, 4.05, 0.42), rot=math.pi, fit=("x", 0.9))
gltf("pachira_aquatica_01", (0.55, 0.85, 0), fit=("z", 1.9))
gltf("potted_plant_02", (6.55, 0.75, 0), fit=("z", 1.2))
# dining
gltf("dining_table", (4.4, 6.6, 0), rot=math.pi / 2, fit=("x", 1.0))
for dx in (-0.6, 0.0, 0.6):
    gltf("dining_chair_02", (4.4 + dx * 1.2 - 0.0, 6.0, 0), rot=0, fit=("z", 0.85))
    gltf("dining_chair_02", (4.4 + dx * 1.2, 7.2, 0), rot=math.pi, fit=("z", 0.85))
for dx in (-0.55, 0.0, 0.55):
    box("pendant", (4.4 + dx * 1.2, 6.6, CH - 0.9), (0.02, 0.02, 1.6), "black")
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.14, location=(4.4 + dx * 1.2, 6.6, CH - 1.7))
    s = bpy.context.object; s.data.materials.append(MT["led"]); bpy.ops.object.shade_smooth()
# art above dining (soft abstract canvas)
art = box("art", (4.4, D - 0.02, 1.65), (2.2, 0.04, 1.3), mat("art", (0.82, 0.74, 0.62), 0.9, tex="fabric_pattern_07", scale=0.3, normal=1.0))
# kitchen: tall oak run on the left wall, marble island
for i in range(6):
    y = 3.9 + i * 0.85
    box(f"tall{i}", (0.33, y + 0.42, 1.35), (0.62, 0.83, 2.7), "oak", bevel=0.004, seg=2)
box("kick", (0.33, 6.45, 0.05), (0.6, 5.1, 0.1), "black")
box("island", (2.15, 6.4, 0.45), (1.0, 3.0, 0.9), "oakdark", bevel=0.004, seg=2)
box("island_top", (2.15, 6.4, 0.93), (1.1, 3.2, 0.06), "stone", bevel=0.003, seg=2)
box("island_fall", (2.15, 4.82, 0.47), (1.1, 0.06, 0.94), "stone")
for k in range(3):
    gltf("bar_chair_round_01", (2.85, 5.6 + k * 0.7, 0), rot=math.pi / 2, fit=("z", 0.95))
for k in range(2):
    bpy.ops.mesh.primitive_cylinder_add(radius=0.16, depth=0.3, location=(2.15, 5.8 + k * 1.2, CH - 0.85))
    c = bpy.context.object; c.data.materials.append(MT["brass"])
    box("cord", (2.15, 5.8 + k * 1.2, CH - 0.35), (0.01, 0.01, 0.7), "black")
gltf("ceramic_vase_03", (2.15, 7.4, 0.96), fit=("z", 0.3))
# bedroom
box("bed_base", (9.05, 4.3, 0.18), (2.1, 2.3, 0.36), "oakdark", bevel=0.01)
box("mattress", (9.05, 4.25, 0.48), (2.0, 2.15, 0.26), "linen", bevel=0.06, seg=4)
box("duvet", (9.05, 3.95, 0.63), (2.12, 1.6, 0.08), "linen", bevel=0.035, seg=4)
box("throw", (9.05, 3.45, 0.68), (2.14, 0.5, 0.03), "boucle", bevel=0.012, seg=3)
for px in (8.55, 9.55):
    box("pillow", (px, 5.15, 0.72), (0.75, 0.3, 0.22), "linen", bevel=0.09, seg=5)
box("headboard", (9.05, 5.48, 0.9), (2.6, 0.12, 1.25), "boucle", bevel=0.03, seg=3)
for nx in (7.5, 10.6):
    gltf("side_table_tall_01", (nx, 5.15, 0), fit=("z", 0.55))
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.11, location=(nx, 5.2, 0.86))
    s = bpy.context.object; s.data.materials.append(MT["led"]); bpy.ops.object.shade_smooth()
gltf("mid_century_lounge_chair", (10.2, 1.1, 0), rot=math.pi + 0.6, fit=("z", 0.85))
gltf("potted_plant_04", (7.55, 0.7, 0), fit=("z", 1.0))
box("bed_rug", (9.05, 3.6, 0.006), (3.0, 2.0, 0.012), "rug")
# balcony furniture
gltf("outdoor_table_chair_set_01", (0.9, -1.1, 0.02), rot=math.pi / 2, fit=("z", 0.9))

# ---------------------------------------------------------------- lights / world
world = bpy.data.worlds.new("w"); scene.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.55, 0.7, 0.95, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 2.0
sun = bpy.data.lights.new("sun", "SUN"); sun.energy = 5.0; sun.angle = math.radians(0.8)
sun.color = (1.0, 0.9, 0.78)
so = bpy.data.objects.new("sun", sun); scene.collection.objects.link(so)
so.rotation_euler = (math.radians(60), 0, math.radians(-25))   # afternoon sun slanting in through the glass
por = bpy.data.lights.new("portal", "AREA"); por.shape = "RECTANGLE"; por.size = W; por.size_y = CH
por.cycles.is_portal = True
po = bpy.data.objects.new("portal", por); scene.collection.objects.link(po)
po.location = (W / 2, -0.05, CH / 2); po.rotation_euler = (math.radians(-90), 0, 0)

# ---------------------------------------------------------------- render
r = scene.render; r.engine = "CYCLES"
cy = scene.cycles
prefs = bpy.context.preferences.addons["cycles"].preferences
try:
    prefs.compute_device_type = "METAL"; prefs.get_devices()
    for d in prefs.devices:
        d.use = True
    cy.device = "GPU"
except Exception as e:
    print("GPU fallback", e)
cy.use_denoising = True; cy.denoiser = "OPENIMAGEDENOISE"
cy.max_bounces = 8; cy.diffuse_bounces = 4; cy.glossy_bounces = 4; cy.transmission_bounces = 8
cy.caustics_reflective = False; cy.caustics_refractive = False
vs = scene.view_settings
vs.view_transform = "AgX"
try:
    vs.look = "AgX - Base Contrast"
except TypeError:
    pass
vs.exposure = 0.7
r.image_settings.file_format = "JPEG"; r.image_settings.quality = 90

cam_d = bpy.data.cameras.new("cam"); cam_d.clip_end = 2000
cam = bpy.data.objects.new("cam", cam_d); scene.collection.objects.link(cam); scene.camera = cam

# 360 nodes: (x, y, yaw of panorama centre)
NODES = {
    "living": (3.6, 3.35, 1.55),
    "kitchen": (3.3, 5.55, 1.55),
    "bedroom": (9.0, 2.2, 1.55),
    "balcony": (6.6, -1.1, 1.55),
}
# stills: (cam pos, look-at, lens)
STILLS = {
    "s_living": ((5.9, 7.6, 1.45), (2.6, 0.0, 1.15), 20),
    "s_kitchen": ((5.6, 8.3, 1.5), (1.4, 5.0, 0.9), 22),
    "s_bedroom": ((10.4, 0.6, 1.4), (8.5, 5.4, 0.8), 18),
    "s_balcony": ((1.0, -0.4, 1.5), (7.5, -2.6, 1.0), 20),
    "s_view": ((3.6, 5.2, 1.4), (3.6, 0.0, 1.2), 24),
}
out = os.path.join(HERE, "renders", "interior"); os.makedirs(out, exist_ok=True)

def look(o, target):
    d = Vector(target) - o.location
    o.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()

if MODE in ("pano", "test"):
    cam_d.type = "PANO"
    try:
        cam_d.panorama_type = "EQUIRECTANGULAR"
    except AttributeError:
        cam_d.cycles.panorama_type = "EQUIRECTANGULAR"
    r.resolution_x, r.resolution_y = (4096, 2048) if MODE == "pano" else (1600, 800)
    cy.samples = 128 if MODE == "pano" else 32
    for k, (x, y, yaw) in NODES.items():
        if ONLY and k not in ONLY:
            continue
        cam.location = (x, y, 1.55)
        cam.rotation_euler = (math.radians(90), 0, math.radians(180))  # equirect centre looks at -y (the sea)
        r.filepath = os.path.join(out, f"pano_{k}" + ("_test" if MODE == "test" else ""))
        bpy.ops.render.render(write_still=True); print("DONE", k, flush=True)
        if MODE == "test":
            break
if MODE == "still":
    cam_d.type = "PERSP"
    r.resolution_x, r.resolution_y = 1920, 1080
    cy.samples = 128
    for k, (p, t, lens) in STILLS.items():
        if ONLY and k not in ONLY:
            continue
        cam.location = p; cam_d.lens = lens; look(cam, t)
        r.filepath = os.path.join(out, k)
        bpy.ops.render.render(write_still=True); print("DONE", k, flush=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "interior.blend"))
