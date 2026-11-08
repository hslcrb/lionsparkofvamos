"""Lions Park of VAMOS — v4 district build pipeline (standalone).

Builds the whole Daegu Samsung Lions Park district procedurally and exports the
web assets used by the app:

  * public/models/lionspark.glb                (Draco compressed GLB)
  * public/models/lionspark-collision.json     (oriented solids, spawn, night anchors)
  * public/models/lionspark-scene.json         (scene description)
  * assets/blender/lionspark-v4.blend          (editable scene)
  * assets/blender/v4-manifest.json            (size + hash record)
  * assets/blender/references/*-v4.png         (preview renders)

Run from the repository root:

    blender --background --python assets/blender/lionspark_v4_build.py

Optional environment variables:
    LSV4_SKIP_RENDER=1   skip preview renders (faster CI runs)

The script is self-contained: it does not open any earlier .blend file and
needs no Blender MCP session. Every material is a Principled BSDF with packed
image textures so the GLB carries its own look on any host.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import struct
import sys
import time
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets" / "blender"
OUT = ROOT / "public" / "models"
TEX_DIR = ASSETS / "textures"
FONT_DIR = ASSETS / "fonts"
REF_DIR = ASSETS / "references"
REF_DIR.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)

SEED = 20261108
RNG = random.Random(SEED)
SKIP_RENDER = os.environ.get("LSV4_SKIP_RENDER") == "1"
START = time.time()


def log(message: str) -> None:
    print(f"[v4 {time.time() - START:6.1f}s] {message}", flush=True)


# ---------------------------------------------------------------------------
# Scene reset
# ---------------------------------------------------------------------------
bpy.ops.wm.read_factory_settings(use_empty=True)
SCENE = bpy.context.scene
SCENE.name = "Lionspark_District_V4"
SCENE.unit_settings.system = "METRIC"
SCENE.unit_settings.scale_length = 1.0
SCENE.render.engine = "BLENDER_EEVEE_NEXT"
SCENE.render.image_settings.file_format = "PNG"
SCENE.render.film_transparent = False
SCENE.view_settings.look = "AgX - Medium High Contrast" if "AgX - Medium High Contrast" in [
    item.identifier for item in SCENE.view_settings.bl_rna.properties["look"].enum_items
] else "None"

COL = bpy.data.collections.new("Lionspark_V4_World")
SCENE.collection.children.link(COL)

# ---------------------------------------------------------------------------
# Colour + texture helpers
# ---------------------------------------------------------------------------


def srgb(value: str):
    """sRGB hex string -> linear RGB tuple."""
    value = value.lstrip("#")
    parts = [int(value[i : i + 2], 16) / 255.0 for i in (0, 2, 4)]
    out = []
    for c in parts:
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return tuple(out)


def _upsample(grid: np.ndarray, height: int, width: int) -> np.ndarray:
    gy = np.clip((np.arange(height) * grid.shape[0] // height), 0, grid.shape[0] - 1)
    gx = np.clip((np.arange(width) * grid.shape[1] // width), 0, grid.shape[1] - 1)
    return grid[gy][:, gx]


def fbm(height: int, width: int, base: int, octaves: int = 4, rng=None) -> np.ndarray:
    rng = rng or np.random.default_rng(SEED)
    out = np.zeros((height, width), dtype=np.float32)
    amplitude = 1.0
    size = base
    for _ in range(octaves):
        grid = rng.random((max(2, size), max(2, size))).astype(np.float32)
        layer = _upsample(grid, height, width)
        if size > 2:
            layer = (
                layer * 0.4
                + np.roll(layer, 1, 0) * 0.15
                + np.roll(layer, -1, 0) * 0.15
                + np.roll(layer, 1, 1) * 0.15
                + np.roll(layer, -1, 1) * 0.15
            )
        out += amplitude * layer
        amplitude *= 0.55
        size *= 2
    out -= out.min()
    return out / max(1e-6, out.max())


def texture_array(kind: str, size: int = 512, tint=None) -> np.ndarray:
    rng = np.random.default_rng(SEED + abs(hash(kind)) % 10_000)
    height = width = size
    v = np.arange(height)[:, None] / height
    u = np.arange(width)[None, :] / width
    noise = fbm(height, width, 8, 5, rng)
    grain = rng.random((height, width)).astype(np.float32)
    rgb = np.zeros((height, width, 3), dtype=np.float32)

    if kind == "grass":
        base = np.array(srgb("#3f7c2f"))
        fine = fbm(height, width, 96, 3, rng)
        blotch = fbm(height, width, 8, 3, rng)
        stripes = 0.90 + 0.10 * (np.sin(u * math.pi * 4) > 0).astype(np.float32)
        shade = 0.93 + 0.10 * fine + 0.07 * blotch + 0.05 * (grain - 0.5)
        for i in range(3):
            rgb[..., i] = base[i] * stripes * shade
        rgb[..., 1] *= 1.0 + 0.05 * blotch
        rgb = np.clip(rgb, 0, 1)
    elif kind == "clay":
        base = np.array(srgb("#9a5a3c"))
        for i in range(3):
            rgb[..., i] = base[i] * (0.82 + 0.32 * noise) + (grain - 0.5) * 0.05
        rgb[..., 0] *= 1.03
        rgb[..., 2] *= 0.95
    elif kind == "asphalt":
        base = np.array(srgb("#3b3d40"))
        for i in range(3):
            rgb[..., i] = base[i] * (0.85 + 0.30 * noise) + (grain - 0.5) * 0.03
        rgb[..., 1] += 0.004
    elif kind == "concrete":
        base = np.array(srgb("#c9c6bf"))
        for i in range(3):
            rgb[..., i] = base[i] * (0.90 + 0.16 * noise) + (grain - 0.5) * 0.02
    elif kind == "paving":
        base = np.array(srgb("#cfccc4"))
        tile_u = np.abs(((u * 8) % 1.0) - 0.5)
        tile_v = np.abs(((v * 8) % 1.0) - 0.5)
        seam = np.clip((np.maximum(tile_u, tile_v) - 0.475) / 0.02, 0, 1)
        for i in range(3):
            rgb[..., i] = base[i] * (0.93 + 0.10 * noise)
        rgb *= (1.0 - 0.16 * seam[..., None])
        rgb += (grain[..., None] - 0.5) * 0.012
    elif kind == "roof":
        base = np.array(srgb("#f2f3f4"))
        for i in range(3):
            rgb[..., i] = base[i] * (0.93 + 0.09 * noise)
        rgb *= (1.0 - 0.05 * (noise < 0.2)[..., None])
    elif kind == "metal":
        base = np.array(srgb("#dfe3e6"))
        for i in range(3):
            rgb[..., i] = base[i] * (0.92 + 0.10 * noise)
    elif kind == "wood":
        grain_band = 0.86 + 0.14 * np.sin(v * math.pi * 60 + noise * 6)
        base = np.array(srgb("#8a6134"))
        for i in range(3):
            rgb[..., i] = base[i] * grain_band
    else:
        base = np.array(srgb("#808080"))
        for i in range(3):
            rgb[..., i] = base[i] * (0.9 + 0.2 * noise)

    alpha = np.ones((height, width, 1), dtype=np.float32)
    arr = np.concatenate([np.clip(rgb, 0, 1), alpha], axis=2).astype(np.float32)
    return arr


TEXTURE_CACHE: dict[str, bpy.types.Image] = {}


def get_texture(kind: str, size: int = 512) -> bpy.types.Image:
    key = f"{kind}_{size}"
    if key in TEXTURE_CACHE:
        return TEXTURE_CACHE[key]
    arr = texture_array(kind, size)
    image = bpy.data.images.new(f"LSV4_{key}", width=size, height=size, alpha=True)
    image.pixels.foreach_set(arr.ravel())
    image.pack()
    TEXTURE_CACHE[key] = image
    return image


MATS: dict[str, bpy.types.Material] = {}
MAT_UV: dict[str, float] = {}
MAT_TEXTURED: set[str] = set()
SMOOTH: set[str] = set()


def material(
    name: str,
    color: str,
    rough: float = 0.7,
    metal: float = 0.0,
    texture: str | None = None,
    uv: float = 4.0,
    emissive: str | None = None,
    emissive_strength: float = 1.0,
    alpha: float = 1.0,
):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nodes = m.node_tree.nodes
    bsdf = next(node for node in nodes if node.type == "BSDF_PRINCIPLED")
    rgb = srgb(color)
    bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if texture:
        image = get_texture(texture)
        tex = nodes.new("ShaderNodeTexImage")
        tex.image = image
        tex.interpolation = "Linear"
        tex.extension = "REPEAT"
        m.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        MAT_UV[name] = uv
        MAT_TEXTURED.add(name)
    if emissive:
        bsdf.inputs["Emission Color"].default_value = (*srgb(emissive), 1.0)
        bsdf.inputs["Emission Strength"].default_value = emissive_strength
    if alpha < 1.0:
        bsdf.inputs["Alpha"].default_value = alpha
        if hasattr(m, "surface_render_method"):
            try:
                m.surface_render_method = "BLENDED"
            except TypeError:
                m.surface_render_method = "DITHERED"
        if hasattr(m, "use_transparency_overlap"):
            m.use_transparency_overlap = False
        m.use_backface_culling = False
    m.diffuse_color = (*rgb, alpha)
    MATS[name] = m
    return m


# Surfaces ------------------------------------------------------------------
material("WalkSurface_Field_Grass", "#4d8c3a", 0.92, texture="grass", uv=13.0)
material("WalkSurface_Outfield_Grass", "#477f36", 0.94, texture="grass", uv=10.0)
material("WalkSurface_Paving", "#cfccc4", 0.86, texture="paving", uv=2.4)
material("WalkSurface_Asphalt", "#3b3d40", 0.92, texture="asphalt", uv=9.0)
material("Infield_Clay", "#9a5a3c", 0.9, texture="clay", uv=7.0)
material("Warning_Track", "#8a5136", 0.9, texture="clay", uv=5.0)
material("WalkSurface_Terrain", "#45633a", 0.95, texture="grass", uv=30.0)
material("Bowl_Concrete", "#b9b6ae", 0.85, texture="concrete", uv=5.0)
material("WalkSurface_Berm", "#4d8536", 0.94, texture="grass", uv=8.0)

# Structure -----------------------------------------------------------------
material("Facade_Panel", "#e8e9e6", 0.52, 0.12, texture="metal", uv=6.0)
material("Facade_Charcoal", "#41494b", 0.66, 0.25, texture="concrete", uv=5.0)
material("Facade_White_Band", "#f4f5f4", 0.42, 0.1)
material("Roof_Membrane", "#eef0f1", 0.55, texture="roof", uv=7.0)
material("Roof_Soffit", "#dfe6ea", 0.6)
material("Roof_Fascia", "#f6f7f7", 0.4, 0.15)
material("Steel_White", "#f0f2f2", 0.35, 0.55)
material("Steel_Galvanized", "#b9bfc3", 0.42, 0.75)
material("Steel_Dark", "#2c3236", 0.5, 0.6)
material("Glass_Blue", "#1c4d68", 0.08, 0.35, alpha=0.52)
material("Glass_Clear", "#cfe4ee", 0.05, 0.1, alpha=0.28)
material("Glass_Storefront", "#123b52", 0.06, 0.45, alpha=0.62)
material("Seat_Blue", "#0f4fa0", 0.62)
material("Seat_Navy", "#0b2f60", 0.62)
material("Seat_White", "#e9edf2", 0.65)
material("Seat_Red", "#a52228", 0.62)
material("Seat_Pans_Blue", "#0f4fa0", 0.62)
material("Dugout_Blue", "#123c74", 0.7)
material("Stone_Light", "#cfc9bd", 0.82, texture="concrete", uv=4.0)
material("Stone_Dark", "#6a6660", 0.8, texture="concrete", uv=3.0)
material("Planter_Soil", "#4a3a2a", 0.95)
material("Plaza_Shrubs", "#2f5a2a", 0.9)
material("Hedge", "#2c5a2b", 0.9, texture="grass", uv=3.0)
material("Mulch", "#4b3625", 0.95)

# Signage + light -----------------------------------------------------------
material("Sign_Navy", "#08214f", 0.5, 0.2)
material("Sign_White", "#f7f9fb", 0.35)
material("Sign_Blue", "#0d47a1", 0.4)
material("Sign_Red", "#b3161b", 0.45)
material("Night_Facade_Glow", "#0d4fd8", 0.4, 0.1, emissive="#1f6bff", emissive_strength=4.5)
material("Night_Sign_LED", "#d9e6ff", 0.3, emissive="#eaf2ff", emissive_strength=3.6)
material("Night_Floodlight_Fittings", "#f2f6ff", 0.2, emissive="#f4f8ff", emissive_strength=10.0)
material("Night_Road_Lamps", "#ffe7c2", 0.3, emissive="#ffdca8", emissive_strength=7.0)
material("Scoreboard_Screen", "#0a0d12", 0.35, 0.2, emissive="#0b1220", emissive_strength=0.6)
material("Banner_Vamos", "#0a2f6b", 0.7)
material("WhitePaint", "#f2f3ee", 0.86)
material("YellowPaint", "#e8b021", 0.86)
material("RedPath", "#8f3a33", 0.9, texture="asphalt", uv=5.0)

# Landscape -----------------------------------------------------------------
material("Tree_Bark", "#4a3b2f", 0.95, texture="wood", uv=1.6)
material("Tree_Leaves_A", "#2f5c2b", 0.9)
material("Tree_Leaves_B", "#3b6b2f", 0.9)
material("Tree_Leaves_C", "#54782f", 0.9)
material("Grass_Verge", "#5a7f3c", 0.94, texture="grass", uv=7.0)

# Sculpture -----------------------------------------------------------------
material("Sculpture_Gold", "#b07a1d", 0.28, 0.92)
material("Polished_Gold", "#d8a63a", 0.16, 1.0)

# Vehicles ------------------------------------------------------------------
for idx, color in enumerate(
    ["#e9eaec", "#1a1c1f", "#8d9095", "#1d3f6e", "#7c1f24", "#c8ccce"]
):
    material(f"Car_Paint_{idx}", color, 0.22, 0.7)
material("Car_Glass", "#16232c", 0.08, 0.4, alpha=0.7)
material("Car_Tire", "#16181a", 0.9)
material("Car_Trim", "#2a2d30", 0.45, 0.6)
material("Car_Lamp", "#f5f7ff", 0.2, emissive="#ffffff", emissive_strength=1.5)

# ---------------------------------------------------------------------------
# Geometry batching
# ---------------------------------------------------------------------------
BATCH: dict[tuple[str, str], tuple[list, list]] = {}
OBJS: list[bpy.types.Object] = []


def add(name: str, verts, faces, mat: str) -> None:
    key = (name, mat)
    bucket = BATCH.get(key)
    if bucket is None:
        bucket = ([], [])
        BATCH[key] = bucket
    offset = len(bucket[0])
    bucket[0].extend(verts)
    bucket[1].extend(tuple(offset + i for i in face) for face in faces)


BOX_FACES = [(0, 3, 2, 1), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7), (4, 5, 6, 7)]


def box(name: str, center, size, mat: str, rot: float = 0.0, tilt: float = 0.0) -> None:
    x, y, z = center
    a, b, c = (v / 2.0 for v in size)
    coords = [
        (-a, -b, -c),
        (a, -b, -c),
        (a, b, -c),
        (-a, b, -c),
        (-a, -b, c),
        (a, -b, c),
        (a, b, c),
        (-a, b, c),
    ]
    ca, sa = math.cos(rot), math.sin(rot)
    cb, sb = math.cos(tilt), math.sin(tilt)
    verts = []
    for vx, vy, vz in coords:
        px = vx * ca - vy * sa
        py = vx * sa + vy * ca
        # tilt rotates about the local Y axis (rise away from the field)
        verts.append((x + px * cb + vz * sb, y + py, z - px * sb + vz * cb))
    add(name, verts, BOX_FACES, mat)


def beam(name: str, a, b, radius: float, mat: str, sides: int = 6) -> None:
    start, end = Vector(a), Vector(b)
    direction = end - start
    if direction.length < 1e-5:
        return
    quat = direction.to_track_quat("Z", "Y")
    verts = []
    for point in (start, end):
        for j in range(sides):
            offset = Vector(
                (
                    radius * math.cos(j * math.tau / sides),
                    radius * math.sin(j * math.tau / sides),
                    0,
                )
            )
            verts.append(tuple(quat @ offset + point))
    faces = [tuple(reversed(range(sides))), tuple(range(sides, sides * 2))]
    faces += [(j, (j + 1) % sides, (j + 1) % sides + sides, j + sides) for j in range(sides)]
    add(name, verts, faces, mat)


def ellipse(name: str, center, scale, mat: str, segments: int = 12, rings: int = 6) -> None:
    verts = []
    faces = []
    x, y, z = center
    for j in range(rings + 1):
        t = math.pi * j / rings
        for i in range(segments):
            a = i * math.tau / segments
            verts.append(
                (
                    x + scale[0] * math.sin(t) * math.cos(a),
                    y + scale[1] * math.sin(t) * math.sin(a),
                    z + scale[2] * math.cos(t),
                )
            )
    for j in range(rings):
        for i in range(segments):
            k = j * segments + i
            kn = j * segments + (i + 1) % segments
            faces.append((k, kn, kn + segments, k + segments))
    add(name, verts, faces, mat)


def prism(name: str, points, z0: float, z1: float, mat: str) -> None:
    """Closed vertical prism from a horizontal polygon."""
    n = len(points)
    verts = [(x, y, z0) for x, y in points] + [(x, y, z1) for x, y in points]
    faces = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))]
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, j + n, i + n))
    add(name, verts, faces, mat)


def polygon_slab(name: str, points, z0: float, z1: float, mat: str) -> None:
    prism(name, points, z0, z1, mat)


def quad(name: str, corners, mat: str) -> None:
    add(name, list(corners), [(0, 1, 2, 3)], mat)


def face_at(name: str, corners, mat: str) -> None:
    add(name, list(corners), [(0, 1, 2, 3)], mat)


def strip(name: str, points, width: float, z: float, mat: str, close: bool = False) -> None:
    """Flat ribbon along a polyline, used for paint, tracks and paving seams."""
    verts = []
    faces = []
    count = len(points)
    for i, (x, y) in enumerate(points):
        if close:
            nx, ny = points[(i + 1) % count]
            px, py = points[(i - 1) % count]
        elif i == 0:
            nx, ny = points[1]
            px, py = points[0]
        elif i == count - 1:
            nx, ny = points[-1]
            px, py = points[-2]
        else:
            nx, ny = points[i + 1]
            px, py = points[i - 1]
        dx, dy = nx - px, ny - py
        length = math.hypot(dx, dy) or 1.0
        ox, oy = -dy / length * width / 2, dx / length * width / 2
        verts.extend([(x + ox, y + oy, z), (x - ox, y - oy, z)])
    for i in range(count if close else count - 1):
        j = (i + 1) % count
        faces.append((i * 2, i * 2 + 1, j * 2 + 1, j * 2))
    add(name, verts, faces, mat)


def flush(smooth: bool = False) -> None:
    created = []
    for (name, mat_name), (verts, faces) in list(BATCH.items()):
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(verts, [], faces)
        mesh.validate(verbose=False)
        mesh.update()
        obj = bpy.data.objects.new(name, mesh)
        COL.objects.link(obj)
        mesh.materials.append(MATS[mat_name])
        scale = MAT_UV.get(mat_name)
        if scale:
            uv_layer = mesh.uv_layers.new(name="UVMap")
            loops = len(mesh.loops)
            polys = len(mesh.polygons)
            if loops and polys:
                loop_vertex = np.empty(loops, dtype=np.int32)
                mesh.loops.foreach_get("vertex_index", loop_vertex)
                coords = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
                mesh.vertices.foreach_get("co", coords)
                coords = coords.reshape(-1, 3)
                normals = np.empty(polys * 3, dtype=np.float32)
                mesh.polygons.foreach_get("normal", normals)
                normals = normals.reshape(-1, 3)
                totals = np.empty(polys, dtype=np.int32)
                mesh.polygons.foreach_get("loop_total", totals)
                poly_index = np.repeat(np.arange(polys), totals)
                axis = np.abs(normals[poly_index]).argmax(axis=1)
                v = coords[loop_vertex]
                # dominant-axis planar projection: up faces use (x, y), walls use the
                # horizontal axis plus height so textures never smear into a line.
                u = np.where(axis == 0, v[:, 1], v[:, 0])
                w = np.where(axis == 2, v[:, 1], v[:, 2])
                w = np.where(axis == 1, v[:, 2], w)
                uv = np.stack([u / scale, w / scale], axis=1).astype(np.float32)
                uv_layer.data.foreach_set("uv", uv.ravel())
        smooth_flag = smooth or name.startswith(
            ("Tree_", "Golden_", "Polished_", "Car_", "Lamp_", "Station_Column")
        )
        mesh.polygons.foreach_set(
            "use_smooth", np.full(len(mesh.polygons), smooth_flag, dtype=bool)
        )
        created.append(obj)
        OBJS.append(obj)
    BATCH.clear()


# ---------------------------------------------------------------------------
# Text (Korean + Latin) converted to mesh
# ---------------------------------------------------------------------------


def load_font(filename: str):
    path = FONT_DIR / filename
    if not path.exists():
        return None
    try:
        return bpy.data.fonts.load(str(path), check_existing=True)
    except Exception as exc:  # pragma: no cover - font fallback
        log(f"font load failed {filename}: {exc}")
        return None


FONT_KR = load_font("NotoSansKR.ttf")
FONT_DISPLAY = load_font("BarlowCondensed-Bold.ttf") or FONT_KR


def text(
    name: str,
    body: str,
    location,
    size: float,
    mat: str,
    yaw: float = 0.0,
    font=None,
    extrude: float = 0.04,
    align_y: str = "CENTER",
    max_width: float | None = None,
    flat: bool = False,
) -> None:
    curve = bpy.data.curves.new(name, "FONT")
    curve.body = body
    curve.size = size
    curve.align_x = "CENTER"
    curve.align_y = align_y
    curve.extrude = extrude
    curve.resolution_u = 3
    if font is not None:
        curve.font = font
    obj = bpy.data.objects.new(name, curve)
    COL.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (0.0, 0.0, yaw) if flat else (math.pi / 2, 0.0, yaw)
    curve.materials.append(MATS[mat])
    # Convert to mesh so the GLB is geometry on every viewer.
    bpy.context.view_layer.objects.active = obj
    for other in bpy.context.selected_objects:
        other.select_set(False)
    obj.select_set(True)
    bpy.ops.object.convert(target="MESH")
    converted = bpy.context.view_layer.objects.active
    if max_width:
        width = max(bb[0] for bb in converted.bound_box) - min(bb[0] for bb in converted.bound_box)
        if width > max_width:
            factor = max_width / width
            converted.scale = (factor, factor, 1.0)
    converted.select_set(False)
    OBJS.append(converted)


# ---------------------------------------------------------------------------
# Site constants
# ---------------------------------------------------------------------------
# Octagonal park footprint, metres, +y is south (outfield hill), -y is north
# (Dalgubeol-daero and Daegongwon station).
P = [(-62, -128), (62, -128), (136, -54), (136, 62), (62, 136), (-62, 136), (-136, 62), (-136, -54)]
HOME = (0.0, -58.0)
CF = (0.0, 64.0)
LF = (-70.0, 12.0)
RF = (70.0, 12.0)


def side_point(side: int, t: float, scale: float = 1.0, z: float = 0.0):
    a = Vector(P[side % 8])
    b = Vector(P[(side + 1) % 8])
    p = a.lerp(b, t) * scale
    return (p.x, p.y, z)


def side_dir(side: int):
    a = Vector(P[side % 8])
    b = Vector(P[(side + 1) % 8])
    d = (b - a).normalized()
    return d


def face_rot(side: int) -> float:
    """Yaw that turns a plane facing -Y to face outward along this side."""
    d = side_dir(side)
    normal = Vector((d.y, -d.x, 0))
    return math.atan2(normal.y, normal.x) + math.pi / 2


# ---------------------------------------------------------------------------
# Terrain
# ---------------------------------------------------------------------------


def hill_height(x: float, y: float) -> float:
    """Outfield hill to the south and gentle ground beyond the district."""
    r = math.hypot(x, y * 0.85)
    base = 0.0
    if y > 168:
        t = min(1.0, (y - 168) / 210.0)
        base += 34.0 * (t * t * (3 - 2 * t))
        base *= 1.0 - 0.45 * min(1.0, abs(x) / 430.0)
        base += 2.6 * math.sin(x / 46.0) * min(1.0, t * 2)
    if r > 420:
        t = min(1.0, (r - 420) / 260.0)
        base += 9.0 * t * t
    return base


def build_terrain() -> None:
    extent = 720.0
    steps = 96
    verts = []
    faces = []
    for j in range(steps + 1):
        y = -extent + 2 * extent * j / steps
        for i in range(steps + 1):
            x = -extent + 2 * extent * i / steps
            z = hill_height(x, y)
            verts.append((x, y, z))
    for j in range(steps):
        for i in range(steps):
            a = j * (steps + 1) + i
            b = a + 1
            c = a + steps + 2
            d = a + steps + 1
            faces.append((a, b, c, d))
    add("WalkSurface_Terrain", verts, faces, "WalkSurface_Terrain")
    flush()


build_terrain()
log("terrain")

# ---------------------------------------------------------------------------
# Field
# ---------------------------------------------------------------------------


def field_outline():
    arc = []
    # wall points from right-field corner around center field to left-field corner
    pts = [
        (-70.0, 12.0),
        (-67.0, 24.0),
        (-61.0, 38.0),
        (-50.0, 50.0),
        (-36.0, 59.0),
        (-19.0, 64.5),
        (0.0, 66.0),
        (19.0, 64.5),
        (36.0, 59.0),
        (50.0, 50.0),
        (61.0, 38.0),
        (67.0, 24.0),
        (70.0, 12.0),
    ]
    arc.extend(pts)
    return [HOME] + arc


def build_field() -> None:
    outline = field_outline()
    # foul-territory grass inside the bowl
    inner = [side_point(side, t, 0.615, -0.02) for side in range(8) for t in (0.0, 0.5)]
    # cobble a filled octagon from triangles around the centre
    verts = inner + [(0.0, 0.0, -0.02)]
    faces = []
    n = len(inner)
    for i in range(n):
        faces.append((i, (i + 1) % n, n))
    add("WalkSurface_Outfield_Grass", verts, faces, "WalkSurface_Outfield_Grass")

    # playing surface fan
    polygon = [(x, y, 0.04) for x, y in outline]
    faces = [(0, i, i + 1) for i in range(1, len(polygon) - 1)]
    add("WalkSurface_Field_Grass", polygon, faces, "WalkSurface_Field_Grass")

    # warning track band outside the wall
    wall = outline[1:]
    inner_pts = [(x, y, 0.045) for x, y in wall]
    outer_pts = []
    for x, y in wall:
        direction = Vector((x, y))
        outward = direction.normalized() if y > 18 else Vector((1 if x > 0 else -1, 0))
        outer_pts.append((x + outward.x * 4.5, y + outward.y * 4.5, 0.045))
    verts = inner_pts + outer_pts
    faces = [
        (i, i + 1, len(wall) + i + 1, len(wall) + i) for i in range(len(wall) - 1)
    ]
    add("WalkSurface_Warning_Track", verts, faces, "Warning_Track")

    # infield dirt: rounded diamond (superellipse in the 45 degree frame)
    cx, cy = 0.0, -38.6
    half = 13.7 + 9.2
    pts = []
    for i in range(72):
        t = math.tau * i / 72
        ct, st = math.cos(t), math.sin(t)
        u = math.copysign(abs(ct) ** 0.22, ct) * half
        v = math.copysign(abs(st) ** 0.22, st) * half
        pts.append(((u + v) / math.sqrt(2), (u - v) / math.sqrt(2) + cy))
    verts = [(x, y, 0.10) for x, y in pts] + [(0.0, cy, 0.10)]
    faces = [(i, (i + 1) % len(pts), len(pts)) for i in range(len(pts))]
    add("Infield_Clay_Surface", verts, faces, "Infield_Clay")

    # mound
    ellipse("Infield_Clay_Mound", (0.0, -38.6, 0.02), (4.6, 4.6, 0.32), "Infield_Clay", 20, 4)
    box("Mound_Rubber", (0.0, -37.6, 0.36), (0.6, 0.15, 0.04), "WhitePaint")

    # bases + home plate
    for center, rot in [((19.4, -38.6, 0.14), 0.0), ((0.0, -19.2, 0.14), 0.0), ((-19.4, -38.6, 0.14), 0.0)]:
        box("Field_Base", center, (0.45, 0.45, 0.09), "WhitePaint", rot)
    plate = [(0.0, -58.5), (0.2, -58.3), (0.2, -58.0), (0.0, -57.8), (-0.2, -58.0), (-0.2, -58.3)]
    polygon_slab("Field_Home_Plate", plate, 0.12, 0.15, "WhitePaint")

    # foul lines
    for corner in (LF, RF):
        strip("Field_Foul_Line", [HOME, corner], 0.14, 0.13, "WhitePaint")
    # coach boxes
    for sign in (-1, 1):
        box("Field_Coach_Box", (sign * 13.0, -46.0, 0.12), (3.0, 1.6, 0.02), "WhitePaint", sign * 0.5)

    # outfield wall with padding and a yellow home-run line
    for i in range(len(wall) - 1):
        a = (wall[i][0], wall[i][1], 0.0)
        b = (wall[i + 1][0], wall[i + 1][1], 0.0)
        length = math.hypot(b[0] - a[0], b[1] - a[1])
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, 0.0)
        angle = math.atan2(b[1] - a[1], b[0] - a[0])
        box("Outfield_Wall", (mid[0], mid[1], 1.7), (length + 0.2, 0.55, 3.4), "Dugout_Blue", angle)
        box("Outfield_Wall_Cap", (mid[0], mid[1], 3.45), (length + 0.2, 0.7, 0.14), "WhitePaint", angle)
        box("Outfield_Home_Run_Line", (mid[0], mid[1], 3.2), (length + 0.2, 0.72, 0.1), "YellowPaint", angle)
    # foul poles
    for corner in (LF, RF):
        beam("Foul_Pole", (corner[0], corner[1], 0.0), (corner[0], corner[1], 26.0), 0.22, "YellowPaint", 8)
        beam("Foul_Pole_Cap", (corner[0], corner[1], 26.0), (corner[0], corner[1], 27.4), 0.45, "Sign_Red", 8)

    # painted outfield wordmark (flat text, readable from the stands)
    text(
        "Field_Painted_Sign",
        "DAEGU LIONS PARK",
        (0.0, 34.0, 0.11),
        9.0,
        "WhitePaint",
        font=FONT_DISPLAY,
        extrude=0.0,
        align_y="CENTER",
        flat=True,
    )
    # on-deck circles
    for sign in (-1, 1):
        ring = [
            (sign * 30.0 + 3.2 * math.cos(a * math.tau / 28), -50.0 + 3.2 * math.sin(a * math.tau / 28))
            for a in range(28)
        ]
        strip("Field_On_Deck_Circle", ring, 0.18, 0.11, "WhitePaint", close=True)
    # batter's boxes
    for sign in (-1, 1):
        box("Field_Batters_Box", (sign * 1.6, -58.0, 0.11), (1.2, 2.6, 0.02), "WhitePaint")
        box("Field_Catchers_Box", (sign * 1.6, -61.8, 0.11), (1.2, 1.2, 0.02), "WhitePaint")

    # backstop net behind home plate, with a central passage from the Gate 2 tunnel
    for span in [(-17.0, -5.0), (5.0, 17.0)]:
        x0, x1 = span
        count = max(2, int((x1 - x0) / 2))
        for k in range(count + 1):
            x = x0 + (x1 - x0) * k / count
            beam("Backstop_Pole", (x, -72.0, 0.0), (x, -72.0, 13.0), 0.055, "Steel_Galvanized", 5)
        for z in (4.5, 9.0, 13.0):
            beam("Backstop_Beam", (x0, -72.0, z), (x1, -72.0, z), 0.05, "Steel_Galvanized", 5)
        quad(
            "Backstop_Net",
            [(x0, -72.0, 0.2), (x1, -72.0, 0.2), (x1, -72.0, 13.0), (x0, -72.0, 13.0)],
            "Glass_Clear",
        )
    for x in (-5.6, 5.6):
        beam("Backstop_Edge_Post", (x, -72.0, 0.0), (x, -72.0, 13.2), 0.1, "Steel_Dark", 6)
    flush()
    log("field")


build_field()

# ---------------------------------------------------------------------------
# Seating bowl
# ---------------------------------------------------------------------------
SIDE_TIER_TWO = {7, 0, 1, 2, 6}
SIDE_ROOF = {7, 0, 1}
SIDE_ROOF_HALF = {2, 6}


def bowl_row_height(tier: str, row: int, rows: int) -> float:
    if tier == "lower":
        return 2.7 + row * (14.4 / max(1, rows - 1))
    return 20.6 + row * (12.6 / max(1, rows - 1))


SEAT_COUNT = 0


def build_bowl() -> None:
    global SEAT_COUNT
    seats = {"Seat_Blue": [], "Seat_Navy": [], "Seat_White": [], "Seat_Red": []}
    tiers = [
        ("lower", 0.618, 0.800, 25, {0, 1, 2, 3, 4, 5, 6, 7}, 0.0),
        ("upper", 0.820, 1.000, 20, SIDE_TIER_TWO, 0.0),
    ]
    for tier, s0, s1, rows, sides, _ in tiers:
        ds = (s1 - s0) / rows
        for side in range(8):
            if side not in sides:
                continue
            for row in range(rows):
                s_row = s0 + row * ds
                z_row = bowl_row_height(tier, row, rows)
                # skip the Gate 2 vomitory in the home plate bowl
                ranges = [(0.0, 1.0)]
                if side == 0 and tier == "lower":
                    ranges = [(0.0, 0.455), (0.545, 1.0)]
                if tier == "upper" and side in SIDE_ROOF_HALF:
                    ranges = [(0.0, 0.58)]
                for t0, t1 in ranges:
                    a = side_point(side, t0, s_row, z_row)
                    b = side_point(side, t1, s_row, z_row)
                    # tread
                    ta = side_point(side, t0, s_row + ds, z_row)
                    tb = side_point(side, t1, s_row + ds, z_row)
                    quad("Bowl_Step_Tread", [a, b, tb, ta], "Bowl_Concrete")
                    # riser facing the field
                    za = z_row - 0.62
                    quad("Bowl_Step_Riser", [(a[0], a[1], za), (b[0], b[1], za), b, a], "Bowl_Concrete")
                    # seats
                    length = (Vector(b) - Vector(a)).length
                    count = max(0, int(length / 0.63))
                    if count == 0:
                        continue
                    for k in range(count):
                        t = t0 + (t1 - t0) * (k + 0.5) / count
                        pos = side_point(side, t, s_row + ds * 0.55, z_row)
                        target = Vector((0.0, -18.0, 0.0))
                        back = Vector((target.x - pos[0], target.y - pos[1]))
                        yaw = math.atan2(-back.x, back.y) + math.pi
                        # aisles every ~56 seats
                        if count > 8 and (k % 56 in (0, 1)):
                            continue
                        color = "Seat_Blue"
                        if tier == "lower" and side == 2 and 0.52 < t < 0.92:
                            color = "Seat_Red"
                        if tier == "lower" and side in (1, 2) and 0.06 < t < 0.16:
                            color = "Seat_Navy"
                        if tier == "upper" and side == 0 and 0.36 < t < 0.64:
                            color = "Seat_White"
                        if tier == "upper" and side in (1, 6) and t < 0.12:
                            color = "Seat_Navy"
                        seats[color].append((pos, yaw))
        # tier walkways
        for walk_s0, walk_s1, z in [(s0 - 0.006, s0, 2.35), (s1, s1 + 0.012, bowl_row_height(tier, rows - 1, rows))]:
            for side in range(8):
                if side not in sides:
                    continue
                a = side_point(side, 0.0, walk_s0, z)
                b = side_point(side, 1.0, walk_s0, z)
                c = side_point(side, 1.0, walk_s1, z)
                d = side_point(side, 0.0, walk_s1, z)
                quad("WalkSurface_Bowl_Aisle", [a, b, c, d], "Bowl_Concrete")

    # seats geometry: pan + back, batched per colour
    seat_names = {
        "Seat_Blue": "Seat_Blue_Pans",
        "Seat_Navy": "Seat_Navy_Pans",
        "Seat_White": "Seat_White_Pans",
        "Seat_Red": "Seat_Red_Pans",
    }

    def seat_box(x, y, z, yaw, local_center, half, array):
            ca, sa = math.cos(yaw), math.sin(yaw)
            cx, cy, cz = local_center
            hx, hy, hz = half
            base = len(array)
            for vx, vy, vz in [
                (-hx, -hy, -hz),
                (hx, -hy, -hz),
                (hx, hy, -hz),
                (-hx, hy, -hz),
                (-hx, -hy, hz),
                (hx, -hy, hz),
                (hx, hy, hz),
                (-hx, hy, hz),
            ]:
                array.append(
                    (
                        x + (cx + vx) * ca - (cy + vy) * sa,
                        y + (cx + vx) * sa + (cy + vy) * ca,
                        z + cz + vz,
                    )
                )
            return [(base + i, base + j, base + k, base + l) for i, j, k, l in BOX_FACES]

    for color, items in seats.items():
        if not items:
            continue
        verts = []
        faces = []
        for (pos, yaw) in items:
            x, y, z = pos
            faces.extend(seat_box(x, y, z, yaw, (0.0, 0.0, 0.31), (0.235, 0.21, 0.035), verts))
            faces.extend(seat_box(x, y, z, yaw, (0.0, 0.22, 0.62), (0.235, 0.035, 0.29), verts))
        add(seat_names[color], verts, faces, color)

    # padded wall at the front of the lower bowl
    for side in range(8):
        spans = [(0.0, 1.0)]
        if side == 0:
            spans = [(0.0, 0.452), (0.548, 1.0)]
        for t0, t1 in spans:
            a = side_point(side, t0, 0.615, 0.0)
            b = side_point(side, t1, 0.615, 0.0)
            d = side_dir(side)
            angle = math.atan2(d.y, d.x)
            mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, 1.3)
            length = (Vector(b) - Vector(a)).length
            box("Bowl_Front_Wall", mid, (length, 0.6, 2.6), "Dugout_Blue", angle)
            box("Bowl_Front_Wall_Cap", (mid[0], mid[1], 2.68), (length, 0.8, 0.16), "Seat_Blue", angle)

    # dugouts along the baselines, outside the foul lines
    for sign in (-1, 1):
        rot = sign * math.pi / 4
        dx, dy = sign * 60.0, -24.0
        box("Dugout_Floor", (dx, dy, 0.12), (26.0, 6.4, 0.24), "Bowl_Concrete", rot)
        box("Dugout_Back_Wall", (dx + sign * 2.6, dy + 2.6, 1.3), (26.0, 0.5, 2.4), "Dugout_Blue", rot)
        for k in range(3):
            box("Dugout_Ad_Panel", (dx + sign * 2.85, dy + 1.0, 1.5), (6.0, 0.12, 1.1), "Sign_Blue", rot)
        box("Dugout_Roof", (dx, dy, 2.62), (26.6, 7.2, 0.28), "Dugout_Blue", rot)
        for k in range(10):
            box("Dugout_Bench", (dx - sign * 11.7 + k * 2.6 * sign, dy, 0.62), (0.75, 3.0, 0.14), "Dugout_Blue", rot)
        for post in (-12.6, 12.6):
            px = dx + post * math.cos(rot)
            py = dy + post * math.sin(rot)
            beam("Dugout_Post", (px, py, 0.1), (px, py, 2.6), 0.11, "Steel_White")

    SEAT_COUNT = sum(len(v) for v in seats.values())
    flush()
    log(f"bowl ({SEAT_COUNT} seats)")


build_bowl()

# ---------------------------------------------------------------------------
# Facade, gates, roof
# ---------------------------------------------------------------------------


def build_facade() -> None:
    for side in range(8):
        outfield = side in (3, 4, 5)
        a0 = side_point(side, 0.0, 1.0, 0.0)
        a1 = side_point(side, 1.0, 1.0, 0.0)
        d = side_dir(side)
        angle = math.atan2(d.y, d.x)
        length = (Vector(a1) - Vector(a0)).length
        mid = ((a0[0] + a1[0]) / 2, (a0[1] + a1[1]) / 2)
        if outfield:
            # low outfield concourse wall behind the seats, open above
            box("Outfield_Facade", (mid[0], mid[1], 3.4), (length, 3.6, 6.8), "Facade_Panel", angle)
            box("Outfield_Facade_Band", (mid[0], mid[1], 7.0), (length, 3.8, 0.4), "Sign_Blue", angle)
            for k in range(0, 13):
                t = 0.04 + k * 0.077
                p = side_point(side, t, 1.02, 3.4)
                box("Outfield_Facade_Pier", (p[0], p[1], 3.4), (0.6, 3.9, 6.8), "Facade_Charcoal", angle)
            for k in range(6):
                t = 0.09 + k * 0.165
                p = side_point(side, t, 1.006, 3.5)
                quad(
                    "Outfield_Concourse_Window",
                    [side_point(side, t - 0.05, 1.006, 1.4), side_point(side, t + 0.05, 1.006, 1.4),
                     side_point(side, t + 0.05, 1.006, 5.9), side_point(side, t - 0.05, 1.006, 5.9)],
                    "Glass_Blue",
                )
            continue

        # ---- base plinth and concourse glass (Gate 2 keeps an open passage) ----
        spans = [(0.0, 1.0)]
        if side == 0:
            spans = [(0.0, 0.34), (0.66, 1.0)]
        for t0, t1 in spans:
            pa = side_point(side, t0, 1.03, 0.0)
            pb = side_point(side, t1, 1.03, 0.0)
            seg_mid = ((pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2)
            seg_len = (Vector(pb) - Vector(pa)).length
            box("Facade_Base_Plinth", (seg_mid[0], seg_mid[1], 0.7), (seg_len, 1.6, 1.4), "Facade_Charcoal", angle)
            box("Facade_Base_Band", (seg_mid[0], seg_mid[1], 1.5), (seg_len, 1.9, 0.24), "Facade_White_Band", angle)
            box("Concourse_Glass", (seg_mid[0], seg_mid[1], 4.3), (seg_len - 0.6, 0.9, 5.6), "Glass_Blue", angle)
            for k in range(int(seg_len / 2.3)):
                px = pa[0] + d.x * (1.2 + k * 2.3)
                py = pa[1] + d.y * (1.2 + k * 2.3)
                box("Concourse_Mullion", (px, py, 4.3), (0.12, 1.0, 5.6), "Steel_White", angle)
        box("Facade_Spandrel", (mid[0], mid[1], 7.9), (length, 1.5, 1.4), "Facade_Panel", angle)

        # ---- upper facade: wide white piers, three deep trapezoid openings ----
        bottom, top = 11.2, 22.8
        for k in range(4):
            t = k / 3
            p = side_point(side, t, 1.018, 0.0)
            box("Facade_Pier", (p[0], p[1], (8.6 + 25.0) / 2), (3.2, 1.6, 16.4), "Facade_Panel", angle)
        for z0, z1 in [(8.6, bottom), (top, 25.0)]:
            box("Facade_Solid_Band", (mid[0], mid[1], (z0 + z1) / 2), (length, 1.5, z1 - z0), "Facade_Panel", angle)
        for k in range(3):
            t0 = k / 3 + 0.022
            t1 = (k + 1) / 3 - 0.022
            # recessed glazing inside the opening
            quad(
                "Facade_Portal_Glass",
                [side_point(side, t0, 1.0, bottom), side_point(side, t1, 1.0, bottom),
                 side_point(side, t1, 1.0, top), side_point(side, t0, 1.0, top)],
                "Glass_Storefront",
            )
            # mullion grid inside the opening
            for j in range(1, 6):
                tt = t0 + (t1 - t0) * j / 6
                pa = side_point(side, tt, 1.005, bottom)
                pb = side_point(side, tt, 1.005, top)
                beam("Facade_Portal_Mullion", pa, pb, 0.07, "Steel_White", 4)
            for z in (bottom + (top - bottom) / 3, bottom + 2 * (top - bottom) / 3):
                pa = side_point(side, t0, 1.005, z)
                pb = side_point(side, t1, 1.005, z)
                beam("Facade_Portal_Mullion", pa, pb, 0.07, "Steel_White", 4)
            # sloped reveal along the top edge of the opening
            pa = side_point(side, t0 - 0.012, 1.02, top)
            pb = side_point(side, t1 + 0.012, 1.02, top)
            beam("Facade_Portal_Header", pa, pb, 0.24, "Facade_Charcoal", 4)

        # ---- roofline fascia and night wash ----
        box("Facade_Roofline", (mid[0], mid[1], 26.3), (length, 1.9, 2.6), "Facade_White_Band", angle)
        box("Facade_Roofline_Shadow", (mid[0], mid[1], 25.05), (length, 2.0, 0.22), "Facade_Charcoal", angle)
        box("Night_Facade_Glow_Cornice", (mid[0], mid[1], 24.95), (length - 1.0, 1.4, 0.16), "Night_Facade_Glow", angle)
        for t in (0.25, 0.75):
            p = side_point(side, t, 1.02, 0.0)
            box("Facade_Column_Fin", (p[0], p[1], 16.8), (1.0, 2.4, 16.6), "Facade_Charcoal", angle)

        # ---- main Gate 2 portal on the home-plate facade ----
        if side == 0:
            g = side_point(side, 0.5, 1.03, 0.0)
            # portal frame: two jambs + header, with the recessed doors visible between
            for dx in (-13.0, 13.0):
                box("Gate_2_Jamb", (g[0] + dx, g[1], 7.2), (3.0, 2.6, 14.4), "Facade_Panel", angle)
            box("Gate_2_Header", (g[0], g[1], 13.4), (26.0, 2.6, 2.0), "Facade_Panel", angle)
            # side vestibules with glass doors; the middle 9 m stays open for visitors
            for bx in (-10.5, 10.5):
                box("Gate_2_Vestibule", (g[0] + bx, g[1] - 0.6, 4.6), (4.6, 1.2, 9.2), "Facade_Panel", angle)
                box("Gate_2_Door", (g[0] + bx, g[1] - 1.25, 2.3), (3.4, 0.2, 4.6), "Glass_Clear", angle)
                for side_k in (-1, 1):
                    box("Gate_2_Door_Frame", (g[0] + bx + side_k * 1.75, g[1] - 1.35, 2.3), (0.14, 0.2, 4.6), "Steel_White", angle)
            box("Gate_2_Canopy", (g[0], g[1] - 1.0, 6.4), (26.0, 4.0, 0.28), "Roof_Fascia", angle)
            for bx in (-8.0, 8.0):
                box("Gate_2_Turnstile", (g[0] + bx, g[1] - 2.5, 1.1), (0.9, 1.6, 2.2), "Steel_Galvanized")
            text("Sign_Gate_2_Plate", "GATE 2", (g[0], g[1] - 1.35, 13.4), 1.7, "Night_Sign_LED", font=FONT_DISPLAY, extrude=0.05)
        if side in (2, 6):
            g = side_point(side, 0.5, 1.04, 0.0)
            box("Gate_Side_Reveal", (g[0], g[1], 5.6), (14.0, 1.8, 11.2), "Facade_Charcoal", angle)
            box("Gate_Side_Glass", (g[0], g[1], 4.8), (11.0, 1.0, 9.0), "Glass_Storefront", angle)

    flush()
    log("facade")

build_facade()


def build_roof() -> None:
    """Cantilever roof: anchored on the facade line, sweeping inward over the stands."""
    covered = []
    for side in range(8):
        if side in SIDE_ROOF:
            covered.append((side, 0.0, 1.0))
        elif side in SIDE_ROOF_HALF:
            covered.append((side, 0.0, 0.58))
    for side, t0, t1 in covered:
        inner_a = side_point(side, t0, 0.70, 32.6)
        inner_b = side_point(side, t1, 0.70, 32.6)
        outer_b = side_point(side, t1, 1.035, 38.4)
        outer_a = side_point(side, t0, 1.035, 38.4)
        quad("Roof_Membrane_Deck", [inner_a, inner_b, outer_b, outer_a], "Roof_Membrane")
        quad(
            "Roof_Soffit_Panel",
            [
                (inner_a[0] * 0.997, inner_a[1] * 0.997, 32.15),
                (inner_b[0] * 0.997, inner_b[1] * 0.997, 32.15),
                (outer_b[0] * 0.997, outer_b[1] * 0.997, 37.95),
                (outer_a[0] * 0.997, outer_a[1] * 0.997, 37.95),
            ],
            "Roof_Soffit",
        )
        d = side_dir(side)
        angle = math.atan2(d.y, d.x)
        mid_in = ((inner_a[0] + inner_b[0]) / 2, (inner_a[1] + inner_b[1]) / 2, 32.4)
        length = (Vector(inner_b) - Vector(inner_a)).length
        box("Roof_Inner_Edge", mid_in, (length, 1.5, 1.8), "Roof_Fascia", angle)
        box("Night_Roof_Glow_Strip", (mid_in[0], mid_in[1], 31.62), (length, 1.1, 0.26), "Night_Facade_Glow", angle)
        mid_out = ((outer_a[0] + outer_b[0]) / 2, (outer_a[1] + outer_b[1]) / 2, 38.7)
        length_out = (Vector(outer_b) - Vector(outer_a)).length
        box("Roof_Outer_Fascia", mid_out, (length_out, 2.0, 1.8), "Roof_Fascia", angle)
        steps = max(3, int(length / 9.0))
        for k in range(steps + 1):
            t = t0 + (t1 - t0) * k / steps
            a = side_point(side, t, 0.71, 32.8)
            b = side_point(side, t, 1.03, 38.2)
            beam("Roof_Truss", (a[0], a[1], 32.9), (b[0], b[1], 38.1), 0.24, "Steel_White", 5)
            beam("Roof_Truss_Web", (a[0], a[1], 31.9), (b[0], b[1], 35.2), 0.13, "Steel_White", 4)
        for frac in (0.33, 0.68):
            s_mid = 0.70 + (1.035 - 0.70) * frac
            z_mid = 32.6 + (38.4 - 32.6) * frac
            pa = side_point(side, t0, s_mid, z_mid)
            pb = side_point(side, t1, s_mid, z_mid)
            beam("Roof_Purlin", pa, pb, 0.15, "Steel_White", 4)
        for k in range(3):
            tt0 = t0 + (t1 - t0) * (0.12 + k * 0.28)
            tt1 = tt0 + (t1 - t0) * 0.14
            quad(
                "Roof_Skylight",
                [side_point(side, tt0, 0.80, 34.0), side_point(side, tt1, 0.80, 34.0),
                 side_point(side, tt1, 0.92, 35.5), side_point(side, tt0, 0.92, 35.5)],
                "Glass_Clear",
            )
        for t in (0.08, 0.92):
            base = side_point(side, t, 1.075, 0.0)
            top = side_point(side, t, 1.06, 38.2)
            beam("Roof_Column", (base[0], base[1], 0.0), (top[0], top[1], 38.0), 0.5, "Steel_White", 8)
            box("Roof_Column_Foot", (base[0], base[1], 0.7), (2.8, 2.8, 1.4), "Facade_Charcoal")
            anchor = side_point(side, t, 0.72, 32.4)
            beam("Roof_Back_Stay", (base[0], base[1], 30.0), anchor, 0.26, "Steel_White", 6)
    flush()
    log("roof")

build_roof()

# ---------------------------------------------------------------------------
# Identity: scoreboard, floodlights, facade signage
# ---------------------------------------------------------------------------


def build_identity() -> None:
    # ---- giant outfield scoreboard (36.0 m x 20.4 m) ----
    sx, sy = 58.0, 112.0
    width, height = 36.0, 20.4
    bottom = 16.0
    for dx in (-14.0, 14.0):
        for dy in (-2.2, 2.2):
            beam("Scoreboard_Leg", (sx + dx, sy + dy, 0.0), (sx + dx * 0.72, sy + dy * 0.6, bottom + height + 1.6), 0.55, "Steel_White", 8)
    for z in (8.0, bottom + height + 1.0):
        beam("Scoreboard_Truss", (sx - 15.0, sy - 2.0, z), (sx + 15.0, sy - 2.0, z), 0.28, "Steel_White", 6)
        beam("Scoreboard_Truss", (sx - 15.0, sy + 2.0, z), (sx + 15.0, sy + 2.0, z), 0.28, "Steel_White", 6)
    for k in range(5):
        x = sx - 15.0 + k * 7.5
        beam("Scoreboard_Brace", (x, sy - 2.0, 8.0), (x, sy + 2.0, bottom + height + 1.0), 0.16, "Steel_White", 4)
    box("Scoreboard_Back", (sx, sy, bottom + height / 2), (width + 2.4, 2.6, height + 2.0), "Steel_Dark")
    box("Scoreboard_Screen_Frame", (sx, sy - 1.35, bottom + height / 2), (width + 0.9, 0.5, height + 0.7), "Steel_White")
    box("Scoreboard_Screen", (sx, sy - 1.65, bottom + height / 2), (width, 0.25, height), "Scoreboard_Screen")
    text("Scoreboard_Wordmark", "LIONS", (sx, sy - 1.82, bottom + height - 4.4), 5.6, "Night_Sign_LED", font=FONT_DISPLAY, extrude=0.02)
    text("Scoreboard_Score", "0   :   0", (sx, sy - 1.82, bottom + 6.2), 4.2, "Night_Sign_LED", font=FONT_DISPLAY, extrude=0.02)
    text("Scoreboard_Inning", "7회말  ·  LIONS PARK", (sx, sy - 1.82, bottom + 2.0), 1.5, "Night_Sign_LED", font=FONT_KR, extrude=0.01)
    box("Night_Sign_LED_Scoreboard", (sx, sy - 1.8, bottom + height + 0.15), (width, 0.2, 0.18), "Night_Sign_LED")
    # scoreboard capping roof and rear sponsor wall
    box("Scoreboard_Roof", (sx, sy, bottom + height + 3.0), (width + 5.0, 5.0, 0.4), "Roof_Fascia")
    text("Scoreboard_Rear_Brand", "SAMSUNG LIONS", (sx, sy + 1.5, bottom + height - 3.0), 3.4, "Sign_White", yaw=math.pi, font=FONT_DISPLAY, extrude=0.02)

    # ---- floodlight towers at the four corners ----
    for cx, cy in [(-168.0, -96.0), (168.0, -96.0), (-168.0, 96.0), (168.0, 96.0)]:
        top_z = 50.0
        spread = 2.4
        legs = [(-spread, -spread), (spread, -spread), (spread, spread), (-spread, spread)]
        for lx, ly in legs:
            beam("Floodlight_Tower_Leg", (cx + lx, cy + ly, 0.0), (cx + lx * 0.35, cy + ly * 0.35, top_z), 0.26, "Steel_White", 4)
        for z in range(6, 48, 6):
            t = z / top_z
            r = spread * (1 - 0.65 * t)
            ring = [(cx - r, cy - r, z), (cx + r, cy - r, z), (cx + r, cy + r, z), (cx - r, cy + r, z)]
            for i in range(4):
                beam("Floodlight_Tower_Brace", ring[i], ring[(i + 1) % 4], 0.09, "Steel_White", 3)
            beam("Floodlight_Tower_Brace", ring[0], ring[2], 0.08, "Steel_White", 3)
        bank_z = 46.0
        box("Floodlight_Bank", (cx * 0.94, cy * 0.94, bank_z), (7.6, 2.2, 5.2), "Steel_Dark", math.atan2(-cy, -cx))
        for row in range(4):
            for col in range(7):
                import math as _m
                yaw = math.atan2(-cy, -cx)
                ox = (col - 3) * 0.95
                oxz = (row - 1.5) * 1.1
                px = cx * 0.94 + ox * math.cos(yaw) - 1.4 * math.sin(yaw)
                py = cy * 0.94 + ox * math.sin(yaw) + 1.4 * math.cos(yaw)
                box("Night_Floodlight_Fittings", (px, py, bank_z + oxz), (0.8, 0.35, 0.9), "Night_Floodlight_Fittings", yaw)

    # ---- facade identity ----
    # navy roofline band with white letters, as on the night facade reference
    for side in (0, 1, 7):
        a = side_point(side, 0.0, 1.055, 26.4)
        b = side_point(side, 1.0, 1.055, 26.4)
        d = side_dir(side)
        angle = math.atan2(d.y, d.x)
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, 26.4)
        length = (Vector(b) - Vector(a)).length
        box("Sign_Roofline_Band", mid, (length - 2.0, 0.5, 2.4), "Sign_Navy", angle)
    text("Sign_Roofline_Wordmark", "DAEGU LIONS PARK", (0.0, -141.2, 26.4), 3.3, "Sign_White", font=FONT_DISPLAY, extrude=0.06, max_width=66.0)
    text("Sign_Roofline_East", "LIONS", (120.0, -66.0, 26.4), 3.0, "Sign_White", yaw=-math.pi / 2, font=FONT_DISPLAY, extrude=0.06, max_width=22.0)
    # crest panels on the corner facades
    for side in (2, 6):
        p = side_point(side, 0.5, 1.05, 18.0)
        d = side_dir(side)
        yaw = math.atan2(-d.y, d.x) + math.pi / 2
        yaw = math.atan2(d.y, d.x)
        box("Sign_Crest_Panel", (p[0], p[1], 17.5), (16.0, 0.4, 7.0), "Sign_Navy", yaw)
        text("Sign_Crest_Text", "LIONS", (p[0], p[1], 18.2), 3.4, "Sign_White", yaw=yaw, font=FONT_DISPLAY, extrude=0.05, max_width=14.0)
        text("Sign_Crest_Sub", "SAMSUNG  LIONS", (p[0], p[1], 15.4), 1.05, "Sign_White", yaw=yaw, font=FONT_DISPLAY, extrude=0.02, max_width=14.0)
    # VAMOS banner on the outfield concourse
    p = side_point(4, 0.5, 1.0, 5.2)
    d = side_dir(4)
    yaw = math.atan2(d.y, d.x)
    box("Banner_Vamos_Wall", (p[0], p[1], 5.0), (30.0, 0.5, 3.2), "Banner_Vamos", yaw)
    text("Banner_Vamos_Text", "VAMOS, WE WILL GO AGAIN", (p[0], p[1], 5.0), 1.5, "Sign_White", yaw=yaw + math.pi, font=FONT_DISPLAY, extrude=0.03, max_width=28.0)
    # Gate 2 sign over the entrance
    flush()
    log("identity")


build_identity()

# ===========================================================================
# STAGE B — plaza, transit, roads, parking, landscape
# ===========================================================================


def flat_poly(name: str, points, z: float, mat: str) -> None:
    verts = [(x, y, z) for x, y in points]
    faces = [(0, i, i + 1) for i in range(1, len(points) - 1)]
    add(name, verts, faces, mat)


def rect(name: str, x0: float, y0: float, x1: float, y1: float, z: float, mat: str) -> None:
    flat_poly(name, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z, mat)


def curb(name: str, points, width: float = 0.3, height: float = 0.22, mat: str = "Stone_Light") -> None:
    for i in range(len(points) - 1):
        a = (points[i][0], points[i][1], 0.0)
        b = (points[i + 1][0], points[i + 1][1], 0.0)
        length = math.hypot(b[0] - a[0], b[1] - a[1])
        if length < 0.05:
            continue
        box(
            name,
            ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, height / 2),
            (length + width * 0.5, width, height),
            mat,
            math.atan2(b[1] - a[1], b[0] - a[0]),
        )


def line(name: str, x0: float, y0: float, x1: float, y1: float, width: float, z: float, mat: str) -> None:
    length = math.hypot(x1 - x0, y1 - y0)
    box(
        name,
        ((x0 + x1) / 2, (y0 + y1) / 2, z),
        (length, width, 0.02),
        mat,
        math.atan2(y1 - y0, x1 - x0),
    )


# ---------------------------------------------------------------------------
# Plaza
# ---------------------------------------------------------------------------

PLAZA_Z = 0.16
PLAZA = [(-162, -132), (162, -132), (162, -221), (-162, -221)]


def build_plaza() -> None:
    # paved field
    flat_poly("WalkSurface_Plaza_Paving", PLAZA, PLAZA_Z, "WalkSurface_Paving")
    # darker inlay bands radiating from the main entrance
    for k in range(9):
        t = -1 + 2 * k / 8
        line(
            "Plaza_Paving_Inlay",
            t * 18,
            -134,
            t * 150,
            -218,
            1.4,
            PLAZA_Z + 0.012,
            "Stone_Dark",
        )
    # granite grid + central axis band
    for k in range(7):
        y = -140.0 - k * 12.0
        line("Plaza_Paving_Grid", -160.0, y, 160.0, y, 0.45, PLAZA_Z + 0.008, "Stone_Dark")
    for x in (-120.0, -90.0, -60.0, -30.0, 30.0, 60.0, 90.0, 120.0):
        line("Plaza_Paving_Grid", x, -136.0, x, -220.0, 0.35, PLAZA_Z + 0.008, "Stone_Dark")
    line("Plaza_Axis_Band", 0.0, -136.0, 0.0, -220.0, 7.0, PLAZA_Z + 0.01, "Stone_Light")
    for r, width in ((15.0, 0.9), (15.9, 0.35), (23.0, 0.5)):
        ring = [(r * math.cos(a * math.tau / 72), -178 + r * math.sin(a * math.tau / 72)) for a in range(72)]
        strip("Plaza_Paving_Ring", ring, width, PLAZA_Z + 0.014, "Stone_Dark", close=True)
    inner = [(-10, -178), (0, -188), (10, -178), (0, -168)]
    flat_poly("Plaza_Emblem_Inlay", inner, PLAZA_Z + 0.014, "Sign_Blue")
    for x in (-104.0, -66.0, 46.0, 84.0):
        for k in range(6):
            tree(x, -146.0 - k * 13.0, PLAZA_Z + 0.05, 9.2, "B", 0.9)
    for x in (-34.0, 34.0):
        for k in range(5):
            tree(x, -150.0 - k * 15.0, PLAZA_Z + 0.05, 8.0, "C", 0.8)
    for x, y in [(-30.0, -160.0), (30.0, -160.0), (-30.0, -196.0), (30.0, -196.0), (-140.0, -178.0), (140.0, -178.0)]:
        beam("Plaza_Light_Mast", (x, y, PLAZA_Z), (x, y, 9.0), 0.13, "Steel_Dark", 8)
        box("Night_Road_Lamps_Plaza", (x, y, 9.1), (1.6, 0.7, 0.22), "Night_Road_Lamps")

    # grand staircase up to Gate 2 (five broad steps)
    steps = 5
    for s in range(steps):
        y0 = -142.0 + s * 1.15
        y1 = y0 + 1.15
        z = PLAZA_Z + (s + 1) * 0.15
        rect("WalkSurface_Grand_Stair", -24.0, y0, 24.0, y1, z, "WalkSurface_Paving")
        # riser
        box("Grand_Stair_Riser", (0.0, y0, z - 0.075), (48.0, 0.1, 0.15), "Stone_Light")
    rect("WalkSurface_Gate_Terrace", -40.0, -136.0, 40.0, -128.0, PLAZA_Z + 0.75, "WalkSurface_Paving")
    # accessible ramps beside the stair
    for sign in (-1, 1):
        for k in range(10):
            t0 = k / 10
            t1 = (k + 1) / 10
            x0 = sign * (26.0 + t0 * 12.0)
            x1 = sign * (26.0 + t1 * 12.0)
            z = PLAZA_Z + 0.75 * (1 - t0)
            box("Plaza_Ramp", ((x0 + x1) / 2, -140.0, z - 0.05), (abs(x1 - x0) + 0.1, 8.0, 0.12), "WalkSurface_Paving")
        # balustrade
        for k in range(11):
            t = k / 10
            x = sign * (26.0 + t * 12.0)
            z = PLAZA_Z + 0.75 * (1 - t)
            beam("Plaza_Balustrade_Post", (x, -136.4, z), (x, -136.4, z + 1.05), 0.05, "Steel_Galvanized", 6)
        beam(
            "Plaza_Balustrade_Rail",
            (sign * 26.0, -136.4, PLAZA_Z + 1.05),
            (sign * 38.0, -136.4, PLAZA_Z + 0.08),
            0.06,
            "Steel_Galvanized",
        )

    # Gate 2 canopy and lantern masts
    for x in (-24.0, 24.0):
        beam("Gate_Canopy_Mast", (x, -137.0, PLAZA_Z), (x, -137.0, 12.5), 0.28, "Steel_White", 8)
    beam("Gate_Canopy_Beam", (-24.0, -137.0, 12.2), (24.0, -137.0, 12.2), 0.24, "Steel_White", 8)
    box("Gate_Canopy_Roof", (0.0, -137.0, 12.55), (52.0, 7.0, 0.35), "Roof_Membrane")

    # ticket box (north-west of the axis)
    tx, ty = -96.0, -158.0
    box("Ticket_Box_Body", (tx, ty, 2.4), (18.0, 9.0, 4.4), "Facade_Panel")
    box("Ticket_Box_Glass", (tx, ty + 4.55, 2.2), (15.0, 0.2, 3.0), "Glass_Storefront")
    for k in range(6):
        box("Ticket_Window", (tx - 6.0 + k * 2.4, ty + 4.7, 2.4), (1.3, 0.1, 1.2), "Glass_Clear")
    box("Ticket_Box_Canopy", (tx, ty + 2.0, 4.9), (20.0, 12.0, 0.4), "Roof_Fascia")
    box("Ticket_Box_Band", (tx, ty, 4.55), (18.2, 9.2, 0.5), "Sign_Blue")
    text("Sign_Ticket", "매표소  TICKET", (tx, ty + 4.75, 3.9), 1.15, "Sign_White", font=FONT_KR, extrude=0.02)

    # team store
    sx, sy = 112.0, -160.0
    box("Team_Store_Body", (sx, sy, 4.0), (40.0, 20.0, 8.0), "Facade_Panel")
    box("Team_Store_Glass", (sx, sy + 10.1, 3.4), (36.0, 0.3, 5.6), "Glass_Storefront")
    box("Team_Store_Fascia", (sx, sy + 10.2, 7.4), (40.5, 0.8, 1.6), "Sign_Blue")
    for k in range(12):
        box("Team_Store_Mullion", (sx - 17.0 + k * 3.1, sy + 10.3, 3.4), (0.14, 0.4, 5.6), "Steel_White")
    text("Sign_Team_Store", "LIONS  TEAM STORE", (sx, sy + 10.6, 7.4), 1.35, "Sign_White", font=FONT_DISPLAY, extrude=0.03)
    text("Sign_Vamos", "VAMOS, WE WILL GO AGAIN", (sx, sy + 10.65, 5.9), 0.78, "Sign_White", font=FONT_DISPLAY, extrude=0.02)

    # golden lion sculpture on the plaza axis side
    gx, gy = -52.0, -178.0
    box("Blocker_Statue_Plinth", (gx, gy, 0.75), (7.0, 5.0, 1.5), "Stone_Light")
    box("Statue_Plinth_Inscription", (gx, gy - 2.55, 0.8), (5.0, 0.1, 0.7), "Sign_Blue")

    def sp(x, y, z):
        return (gx + x, gy + y, 1.5 + z)

    ellipse("Golden_Lion_Torso", sp(0, 0.3, 1.55), (0.78, 1.5, 0.95), "Sculpture_Gold", 18, 10)
    ellipse("Golden_Lion_Head", sp(0, -1.0, 2.65), (0.7, 0.72, 0.76), "Sculpture_Gold", 18, 10)
    ellipse("Golden_Lion_Muzzle", sp(0, -1.62, 2.5), (0.46, 0.36, 0.34), "Sculpture_Gold", 14, 8)
    for x in (-0.48, 0.48):
        ellipse("Golden_Lion_Ears", sp(x, -0.85, 3.3), (0.2, 0.18, 0.24), "Sculpture_Gold", 12, 8)
    for x, y in [(-0.5, 1.15), (0.5, 1.15), (-0.52, -0.4), (0.52, -0.4)]:
        beam("Golden_Lion_Legs", sp(x, y, 0.1), sp(x, y, 1.6), 0.19, "Sculpture_Gold", 10)
        ellipse("Golden_Lion_Paws", sp(x, y - 0.14, 0.22), (0.28, 0.44, 0.18), "Sculpture_Gold", 12, 6)
    for j in range(26):
        a = j * math.tau / 26
        start = sp(0.66 * math.cos(a), -0.72 + 0.16 * math.sin(a), 2.62 + 0.7 * math.sin(a))
        end = sp(1.0 * math.cos(a), -0.18 + 0.28 * math.sin(a), 2.32 + 0.98 * math.sin(a))
        beam("Golden_Lion_Mane", start, end, 0.13, "Sculpture_Gold", 5)
    ellipse("Polished_Golden_Orb", sp(1.35, -1.35, 1.0), (0.95, 0.95, 0.95), "Polished_Gold", 28, 16)
    beam("Golden_Lion_Forearm", sp(0.55, -0.5, 1.7), sp(1.35, -1.3, 1.9), 0.2, "Sculpture_Gold", 10)
    prev = None
    for j in range(11):
        a = j / 10 * math.pi
        point = sp(0.55 + 0.4 * math.sin(a), 1.5 + 0.75 * math.sin(a / 2), 2.0 + 0.55 * math.cos(a))
        if prev:
            beam("Golden_Lion_Tail", prev, point, 0.09, "Sculpture_Gold", 6)
        prev = point

    # information kiosk and wayfinding
    box("Info_Kiosk_Body", (34.0, -192.0, 1.5), (4.4, 4.0, 3.0), "Facade_Panel")
    box("Info_Kiosk_Glass", (34.0, -189.9, 1.5), (3.6, 0.15, 2.0), "Glass_Storefront")
    box("Info_Kiosk_Roof", (34.0, -192.0, 3.1), (5.6, 5.2, 0.25), "Sign_Blue")
    text("Sign_Info", "안내  INFO", (34.0, -189.8, 2.6), 0.5, "Sign_White", font=FONT_KR, extrude=0.01)

    # flag poles along the plaza edge
    for k in range(9):
        x = -60.0 + k * 15.0
        beam("Plaza_Flag_Pole", (x, -208.0, PLAZA_Z), (x, -208.0, 12.0), 0.1, "Steel_White", 8)
        box("Plaza_Flag", (x + 0.9, -208.0, 10.6), (1.8, 0.06, 1.2), "Sign_Blue")

    # benches, bollards, bike racks
    for k in range(10):
        x = -135.0 + k * 30.0
        for y in (-150.0, -198.0):
            box("Plaza_Bench_Seat", (x, y, 0.62), (2.6, 0.65, 0.12), "Tree_Bark")
            box("Plaza_Bench_Back", (x, y + 0.32, 0.86), (2.6, 0.1, 0.5), "Tree_Bark")
            for dx in (-1.1, 1.1):
                box("Plaza_Bench_Leg", (x + dx, y, 0.3), (0.12, 0.6, 0.6), "Steel_Dark")
    for k in range(22):
        x = -158.0 + k * 15.0
        for y in (-137.0, -216.0):
            beam("Plaza_Bollard", (x, y, PLAZA_Z), (x, y, PLAZA_Z + 0.9), 0.09, "Steel_Dark", 8)
    for k in range(6):
        box("Plaza_Bike_Rack", (-120.0 + k * 3.0, -188.0, 0.5), (0.08, 2.0, 0.8), "Steel_Galvanized")

    # planted beds with trees and hedges along the plaza edges
    beds = [
        (-150.0, -146.0, -125.0, -140.0),
        (125.0, -146.0, 150.0, -140.0),
        (-150.0, -214.0, -120.0, -206.0),
        (20.0, -214.0, 60.0, -206.0),
    ]
    for x0, y0, x1, y1 in beds:
        box("Plaza_Planter_Curb", ((x0 + x1) / 2, (y0 + y1) / 2, PLAZA_Z + 0.2), (x1 - x0, y1 - y0, 0.4), "Stone_Light")
        box("Planter_Soil", ((x0 + x1) / 2, (y0 + y1) / 2, PLAZA_Z + 0.38), (x1 - x0 - 0.6, y1 - y0 - 0.6, 0.05), "Planter_Soil")
        count = max(1, int((x1 - x0) / 7))
        for k in range(count):
            tx = x0 + 3.5 + (x1 - x0 - 7) * (k + 0.5) / count
            tree(tx, (y0 + y1) / 2, PLAZA_Z + 0.4, 4.2, "A")

    flush()
    log("plaza")


# ---------------------------------------------------------------------------
# Trees (batched, low poly, deterministic)
# ---------------------------------------------------------------------------


def tree(x: float, y: float, z: float, height: float = 8.0, variant: str = "A", spread: float = 1.0):
    RNG.seed(int(abs(x * 13 + y * 7 + height * 31)) % 2_000_000_000)
    trunk_h = height * (0.42 if variant != "C" else 0.55)
    radius = max(0.12, height * 0.028)
    beam("Tree_Trunk", (x, y, z), (x + RNG.uniform(-0.3, 0.3), y + RNG.uniform(-0.3, 0.3), z + trunk_h), radius, "Tree_Bark", 6)
    if variant == "A":
        blobs = [(0.0, 0.0, trunk_h + height * 0.30, height * 0.34), (0.0, 0.0, trunk_h + height * 0.52, height * 0.24)]
    elif variant == "B":
        blobs = [
            (-height * 0.12, 0.0, trunk_h + height * 0.28, height * 0.30),
            (height * 0.12, 0.05, trunk_h + height * 0.34, height * 0.27),
            (0.0, -height * 0.1, trunk_h + height * 0.50, height * 0.22),
        ]
    else:
        blobs = [(0.0, 0.0, trunk_h + height * 0.22, height * 0.20), (0.0, 0.0, trunk_h + height * 0.38, height * 0.16)]
    material_name = {"A": "Tree_Leaves_A", "B": "Tree_Leaves_B", "C": "Tree_Leaves_C"}[variant]
    for bx, by, bz, br in blobs:
        ellipse(
            "Tree_Canopy_" + variant,
            (x + bx, y + by, z + bz),
            (br * spread, br * spread, br * 0.82),
            material_name,
            9,
            5,
        )


def hedge(x0: float, y0: float, x1: float, y1: float, z: float = 0.0, height: float = 1.1) -> None:
    length = math.hypot(x1 - x0, y1 - y0)
    box(
        "Plaza_Shrubs",
        ((x0 + x1) / 2, (y0 + y1) / 2, z + height / 2),
        (length, 1.1, height),
        "Hedge",
        math.atan2(y1 - y0, x1 - x0),
    )

# ---------------------------------------------------------------------------
# Roads: Dalgubeol-daero (10 lanes) and Ya-gujeonseol-ro
# ---------------------------------------------------------------------------
ROAD_Y = -245.0
ROAD_HALF = 20.0
SIDEWALK = 4.6


def road_surface(name: str, x0: float, y0: float, x1: float, y1: float, z: float = 0.06) -> None:
    rect(name, x0, y0, x1, y1, z, "WalkSurface_Asphalt")


def dashed_line(x0: float, y0: float, x1: float, y1: float, width: float, dash: float, gap: float, z: float, mat: str = "WhitePaint") -> None:
    length = math.hypot(x1 - x0, y1 - y0)
    if length < 0.1:
        return
    ux, uy = (x1 - x0) / length, (y1 - y0) / length
    pos = 0.0
    while pos < length:
        end = min(length, pos + dash)
        line(
            "Road_Lane_Dashes",
            x0 + ux * pos,
            y0 + uy * pos,
            x0 + ux * end,
            y0 + uy * end,
            width,
            z,
            mat,
        )
        pos += dash + gap


def build_roads() -> None:
    # carriageways, split at the Ya-gujeonseol-ro junction (x -228..-202)
    for x0, x1 in [(-720.0, -228.0), (-202.0, 720.0)]:
        road_surface("WalkSurface_Road_Dalgubeol", x0, ROAD_Y - ROAD_HALF, x1, ROAD_Y + ROAD_HALF)
        # planted median
        box("Road_Median_Curb", ((x0 + x1) / 2, ROAD_Y, 0.16), (x1 - x0, 4.0, 0.32), "Stone_Light")
        rect("WalkSurface_Median_Soil", x0, ROAD_Y - 1.6, x1, ROAD_Y + 1.6, 0.33, "Planter_Soil")
        for k in range(int((x1 - x0) / 9.0)):
            hx = x0 + 4.5 + k * 9.0
            if hx > x1 - 3:
                break
            ellipse("Plaza_Shrubs", (hx, ROAD_Y, 0.62), (1.15, 1.15, 0.55), "Hedge", 8, 4)
        # near sidewalk + bike path, far sidewalk
        rect("WalkSurface_Road_Sidewalk", x0, ROAD_Y + ROAD_HALF, x1, ROAD_Y + ROAD_HALF + SIDEWALK, 0.14, "WalkSurface_Paving")
        rect("WalkSurface_Red_Cycleway", x0, ROAD_Y + ROAD_HALF + 0.15, x1, ROAD_Y + ROAD_HALF + 2.6, 0.16, "RedPath")
        rect("WalkSurface_Road_Sidewalk", x0, ROAD_Y - ROAD_HALF - SIDEWALK, x1, ROAD_Y - ROAD_HALF, 0.14, "WalkSurface_Paving")
        curb("Road_Curb", [(x0, ROAD_Y + ROAD_HALF), (x1, ROAD_Y + ROAD_HALF)])
        curb("Road_Curb", [(x0, ROAD_Y - ROAD_HALF), (x1, ROAD_Y - ROAD_HALF)])
        # lane paint: 5 lanes each direction
        line("Road_Edge_Line", x0, ROAD_Y + 19.4, x1, ROAD_Y + 19.4, 0.16, 0.075, "WhitePaint")
        line("Road_Edge_Line", x0, ROAD_Y - 19.4, x1, ROAD_Y - 19.4, 0.16, 0.075, "WhitePaint")
        line("Road_Centre_Lines", x0, ROAD_Y + 2.2, x1, ROAD_Y + 2.2, 0.14, 0.075, "YellowPaint")
        line("Road_Centre_Lines", x0, ROAD_Y - 2.2, x1, ROAD_Y - 2.2, 0.14, 0.075, "YellowPaint")
        for offset in (5.8, 9.4, 13.0, 16.6):
            dashed_line(x0, ROAD_Y + offset, x1, ROAD_Y + offset, 0.14, 5.0, 7.0, 0.075)
            dashed_line(x0, ROAD_Y - offset, x1, ROAD_Y - offset, 0.14, 5.0, 7.0, 0.075)

    # Ya-gujeonseol-ro (north-south), 6 lanes + median
    YX = -215.0
    for y0, y1 in [(-720.0, ROAD_Y - ROAD_HALF), (ROAD_Y + ROAD_HALF, 150.0)]:
        rect("WalkSurface_Road_Yagujeonseol", YX - 13.0, y0, YX + 13.0, y1, 0.06, "WalkSurface_Asphalt")
        rect("WalkSurface_Road_Sidewalk", YX - 17.6, y0, YX - 13.0, y1, 0.14, "WalkSurface_Paving")
        rect("WalkSurface_Road_Sidewalk", YX + 13.0, y0, YX + 17.6, y1, 0.14, "WalkSurface_Paving")
        curb("Road_Curb", [(YX - 13.0, y0), (YX - 13.0, y1)])
        curb("Road_Curb", [(YX + 13.0, y0), (YX + 13.0, y1)])
        box("Road_Median_Curb", (YX, (y0 + y1) / 2, 0.16), (2.6, y1 - y0, 0.32), "Stone_Light")
        for offset in (3.2, 6.9, 10.6):
            dashed_line(YX + offset, y0, YX + offset, y1, 0.14, 5.0, 7.0, 0.075)
            dashed_line(YX - offset, y0, YX - offset, y1, 0.14, 5.0, 7.0, 0.075)
        for k in range(int((y1 - y0) / 12.0)):
            ty = y0 + 6.0 + k * 12.0
            if ty > y1 - 4:
                break
            ellipse("Plaza_Shrubs", (YX, ty, 0.62), (0.85, 0.85, 0.5), "Hedge", 8, 4)

    # junction
    rect("WalkSurface_Intersection", YX - 13.0, ROAD_Y - ROAD_HALF, YX + 13.0, ROAD_Y + ROAD_HALF, 0.06, "WalkSurface_Asphalt")

    # crosswalks + traffic islands
    for cx in (0.0, YX):
        for side in (-1, 1):
            y = ROAD_Y + side * (ROAD_HALF + 2.2)
            for k in range(12):
                box(
                    "Zebra_Crosswalks",
                    (cx - 19.8 + k * 3.6, y, 0.17),
                    (1.5, 4.4, 0.03),
                    "WhitePaint",
                )
        box("Med_Traffic_Island", (cx, ROAD_Y, 0.32), (7.0, 4.2, 0.5), "Stone_Light")
        box("Med_Island_Guard", (cx, ROAD_Y, 0.95), (7.0, 0.3, 0.5), "Steel_Galvanized")
        for side in (-1, 1):
            box("Junction_Stop_Lines", (cx + side * 21.0, ROAD_Y, 0.085), (0.4, 16.0, 0.03), "WhitePaint")

    # traffic signals at the junction
    for sx, sy, yaw in [(-33, ROAD_Y + 22.0, 0.0), (33, ROAD_Y - 22.0, math.pi), (-33, ROAD_Y - 22.0, 0.0)]:
        beam("Signal_Mast", (YX + sx, sy, 0.0), (YX + sx, sy, 6.4), 0.13, "Steel_Dark", 8)
        beam("Signal_Arm", (YX + sx, sy, 6.2), (YX + sx + (14.0 if sy > ROAD_Y else -14.0), sy, 6.2), 0.1, "Steel_Dark", 6)
        for k in range(3):
            box("Signal_Housing", (YX + sx + (7.0 if sy > ROAD_Y else -7.0) + k * 2.4, sy, 6.0), (0.7, 0.5, 1.6), "Steel_Dark")
            box("Signal_Lens", (YX + sx + (7.0 if sy > ROAD_Y else -7.0) + k * 2.4, sy + 0.28, 6.0), (0.4, 0.1, 0.4), "Night_Road_Lamps")

    # street trees on both sidewalks (ginkgo on the park side, zelkova opposite)
    x = -700.0
    while x < 700.0:
        if abs(x - YX) > 20 and not (-24.0 < x < 24.0):
            for side in (-1, 1):
                yy = ROAD_Y + side * (ROAD_HALF + 2.6)
                variant = "C" if side > 0 else "A"
                tree(x, yy, 0.2, 9.5 if variant == "C" else 8.0, variant, 0.85)
        x += 13.0
    # street lamps
    y = -700.0
    while y < 720.0:
        for side in (-1, 1):
            yy = ROAD_Y + side * (ROAD_HALF + 3.2)
            if abs(y - YX) < 22:
                continue
            beam("Lamp_Pole", (y, yy, 0.2), (y, yy, 9.6), 0.11, "Steel_Dark", 8)
            beam("Lamp_Arm", (y, yy, 9.5), (y, yy - side * 2.2, 9.9), 0.08, "Steel_Dark", 6)
            box("Night_Road_Lamps_Lamphead", (y, yy - side * 2.4, 9.85), (1.2, 0.55, 0.16), "Night_Road_Lamps")
        y += 34.0

    flush()
    log("roads")


# ---------------------------------------------------------------------------
# Daegongwon station (exits 4 and 5)
# ---------------------------------------------------------------------------


def station_exit(x: float, y: float, number: int) -> None:
    label = f"대공원역 {number}번출구"
    english = f"Daegongwon  Exit {number}"
    # twin glass canopy
    for dx in (-6.4, 6.4):
        for dy in (-3.2, 3.2):
            beam("Station_Column", (x + dx, y + dy, 0.2), (x + dx, y + dy, 5.4), 0.16, "Steel_White", 8)
    box("Station_Canopy", (x, y, 5.62), (15.0, 8.4, 0.34), "Glass_Clear")
    box("Station_Canopy_Frame", (x, y, 5.85), (15.4, 8.8, 0.22), "Steel_White")
    for k in range(7):
        box("Station_Canopy_Rib", (x - 7.0 + k * 2.33, y, 5.5), (0.12, 8.4, 0.16), "Steel_White")
    # entrance box with the stair mouth
    box("Station_Entrance_Glass", (x, y, 1.9), (12.0, 5.6, 3.6), "Glass_Storefront")
    box("Station_Entrance_Frame", (x, y, 3.6), (12.4, 6.0, 0.3), "Steel_White")
    box("Station_Stair_Mouth", (x, y - 2.6, 3.0), (7.2, 0.3, 0.5), "Sign_Navy")
    # steps descending into the mouth (visual)
    for k in range(5):
        box(
            "Station_Stair_Step",
            (x, y + 2.3 - k * 0.55, 1.2 - k * 0.22),
            (7.0, 0.55, 0.22),
            "Stone_Light",
        )
    box("Station_Dark_Interior", (x, y + 0.2, 0.05), (7.0, 2.2, 0.1), "Sign_Navy")
    # glass balustrade
    for dx in (-3.7, 3.7):
        box("Station_Balustrade", (x + dx, y + 0.6, 1.6), (0.12, 5.4, 1.1), "Glass_Clear")
    # station name pylon
    px, py = x + 8.6, y + 1.0
    beam("Station_Pylon_Post", (px, py, 0.2), (px, py, 6.2), 0.12, "Steel_Dark", 8)
    box("Station_Pylon_Sign", (px, py, 5.2), (2.6, 0.35, 3.4), "Sign_Navy")
    text("Sign_Station_KR", label, (px, py - 0.22, 5.9), 0.52, "Sign_White", font=FONT_KR, extrude=0.02)
    text("Sign_Station_Line", "대구도시철도 2호선", (px, py - 0.22, 5.15), 0.23, "Sign_White", font=FONT_KR, extrude=0.01)
    text("Sign_Station_EN", english, (px, py - 0.22, 4.55), 0.24, "Sign_White", font=FONT_DISPLAY, extrude=0.01)
    # subway roundel
    ellipse("Station_Roundel", (px, py - 0.3, 3.35), (0.5, 0.5, 0.5), "Sign_Red", 20, 4)
    box("Station_Roundel_Band", (px, py - 0.55, 3.35), (0.9, 0.2, 0.26), "Sign_White")
    # night sign glow
    box("Night_Sign_LED_Station", (px, py - 0.42, 5.95), (2.3, 0.06, 0.14), "Night_Sign_LED")


def build_station() -> None:
    rect("WalkSurface_Plaza_Paving", -120.0, -272.0, 120.0, -350.0, 0.15, "WalkSurface_Paving")
    station_exit(-58.0, -288.0, 5)
    station_exit(52.0, -288.0, 4)
    # station hall behind the exits
    box("Station_Hall", (0.0, -330.0, 4.4), (110.0, 34.0, 8.8), "Facade_Panel")
    box("Station_Hall_Glass", (0.0, -312.9, 4.0), (100.0, 0.4, 6.4), "Glass_Storefront")
    box("Station_Hall_Band", (0.0, -312.8, 8.4), (110.5, 0.6, 1.4), "Sign_Navy")
    text("Sign_Station_Hall", "대공원역  DAEGONGWON STATION", (0.0, -313.2, 8.4), 1.15, "Sign_White", font=FONT_KR, extrude=0.03)
    for k in range(10):
        box("Station_Hall_Mullion", (-45.0 + k * 10.0, -312.7, 4.0), (0.22, 0.5, 6.4), "Steel_White")
    # bus stop on the far sidewalk
    for k in range(4):
        beam("Bus_Stop_Post", (-95.0 + k * 6.0, -266.6, 0.2), (-95.0 + k * 6.0, -266.6, 3.0), 0.07, "Steel_Galvanized", 6)
    box("Bus_Stop_Roof", (-90.5, -266.2, 3.1), (19.0, 2.6, 0.18), "Glass_Clear")
    box("Bus_Stop_Bench", (-90.5, -265.4, 0.6), (4.0, 0.6, 0.12), "Tree_Bark")
    text("Sign_Bus_Stop", "대공원역앞  버스정류장", (-90.5, -267.6, 2.3), 0.42, "Sign_White", font=FONT_KR, extrude=0.02)
    flush()
    log("station")


# ---------------------------------------------------------------------------
# Parking
# ---------------------------------------------------------------------------
CAR_VARIANTS = 6


def parked_car(x: float, y: float, yaw: float, color: int) -> None:
    paint = f"Car_Paint_{color % CAR_VARIANTS}"
    ca, sa = math.cos(yaw), math.sin(yaw)

    def local(cx, cy, cz, sx, sy, sz, mat, name="Parked_Cars"):
        verts = []
        for vx, vy, vz in [
            (-sx / 2, -sy / 2, -sz / 2),
            (sx / 2, -sy / 2, -sz / 2),
            (sx / 2, sy / 2, -sz / 2),
            (-sx / 2, sy / 2, -sz / 2),
            (-sx / 2, -sy / 2, sz / 2),
            (sx / 2, -sy / 2, sz / 2),
            (sx / 2, sy / 2, sz / 2),
            (-sx / 2, sy / 2, sz / 2),
        ]:
            verts.append(
                (
                    x + (cx + vx) * ca - (cy + vy) * sa,
                    y + (cx + vx) * sa + (cy + vy) * ca,
                    cz + vz,
                )
            )
        add(name, verts, BOX_FACES, mat)

    local(0.0, 0.0, 0.55, 1.85, 4.5, 0.62, paint)
    local(0.0, -0.15, 1.06, 1.63, 2.5, 0.48, "Car_Glass")
    local(0.0, -0.15, 1.32, 1.55, 2.2, 0.08, paint)
    for wx, wy in [(-0.92, -1.42), (0.92, -1.42), (-0.92, 1.42), (0.92, 1.42)]:
        local(wx, wy, 0.33, 0.24, 0.68, 0.62, "Car_Tire")
    local(0.0, 2.26, 0.62, 1.7, 0.1, 0.14, "Car_Trim")
    local(0.0, -2.26, 0.62, 1.7, 0.1, 0.14, "Car_Trim")
    local(-0.66, 2.28, 0.72, 0.42, 0.06, 0.16, "Car_Lamp")
    local(0.66, 2.28, 0.72, 0.42, 0.06, 0.16, "Car_Lamp")
    local(-0.66, -2.28, 0.72, 0.42, 0.06, 0.16, "Sign_Red")
    local(0.66, -2.28, 0.72, 0.42, 0.06, 0.16, "Sign_Red")


def parking_lot(name: str, x0: float, y0: float, x1: float, y1: float, rows: int, seed: int) -> None:
    rng = random.Random(seed)
    rect(f"WalkSurface_Parking_{name}", x0, y0, x1, y1, 0.07, "WalkSurface_Asphalt")
    width = x1 - x0
    stall_w = 2.6
    stall_d = 5.2
    aisle = 6.4
    row_h = stall_d * 2 + aisle
    count_x = int((width - 6) / stall_w)
    spacing = 0.0
    y = y0 + 3.0
    for row in range(rows):
        if y + stall_d * 2 > y1 - 2:
            break
        for k in range(count_x):
            sx = x0 + 3.0 + k * stall_w
            if k % 8 == 4:
                continue
            for side in (0, 1):
                sy = y + (stall_d if side else 0)
                line("Parking_Stall_Line", sx, sy - stall_d / 2, sx, sy + stall_d / 2, 0.1, 0.09, "WhitePaint")
                if rng.random() < 0.62:
                    parked_car(sx + stall_w / 2, sy, 0.0, rng.randrange(CAR_VARIANTS))
        line("Parking_Stall_Line", x0 + 3.0, y, x1 - 3.0, y, 0.1, 0.09, "WhitePaint")
        line("Parking_Stall_Line", x0 + 3.0, y + stall_d * 2, x1 - 3.0, y + stall_d * 2, 0.1, 0.09, "WhitePaint")
        y += row_h
    # planted islands + lamps
    for k in range(int(width / 26)):
        ix = x0 + 13.0 + k * 26.0
        for iy in (y0 + 4.0, y1 - 5.0):
            box("Parking_Island_Curb", (ix, iy, 0.2), (6.0, 2.6, 0.4), "Stone_Light")
            box("Planter_Soil", (ix, iy, 0.42), (5.4, 2.0, 0.06), "Planter_Soil")
            tree(ix, iy, 0.45, 7.5, "A", 0.9)
    for k in range(int(width / 34)):
        lx = x0 + 10.0 + k * 34.0
        beam("Parking_Light_Pole", (lx, y1 - 2.0, 0.1), (lx, y1 - 2.0, 9.0), 0.1, "Steel_Dark", 8)
        box("Night_Road_Lamps_Parking", (lx, y1 - 2.6, 8.9), (1.1, 0.6, 0.16), "Night_Road_Lamps")
    # entrance booth
    bx, by = x1 - 8.0, y1 - 6.0
    box("Parking_Booth", (bx, by, 1.6), (4.0, 3.0, 3.2), "Facade_Panel")
    box("Parking_Booth_Roof", (bx, by, 3.35), (5.0, 4.0, 0.3), "Sign_Blue")
    box("Parking_Gate_Arm", (bx - 3.5, by, 1.1), (4.0, 0.16, 0.16), "Sign_Red")
    text("Sign_Parking", f"{name} 주차장  P{name}", (bx, by - 1.6, 2.6), 0.42, "Sign_White", font=FONT_KR, extrude=0.01)


def build_parking() -> None:
    parking_lot("1", 168.0, -214.0, 344.0, -34.0, 5, 41)
    parking_lot("2", -346.0, -214.0, -252.0, -92.0, 3, 42)
    # landscaped buffer between the plaza and Ya-gujeonseol-ro
    rect("WalkSurface_Plaza_Paving", -202.0, -221.0, -162.0, -132.0, 0.14, "WalkSurface_Paving")
    for k in range(9):
        tree(-196.0, -212.0 + k * 10.0, 0.1, 8.4, "B", 0.95)
    hedge(-200.0, -218.0, -166.0, -218.0, 0.2, 1.0)
    # P1 / P2 wayfinding pylons near the road
    for name, x, y in [("1", 178.0, -222.0), ("2", -240.0, -222.0)]:
        beam("Parking_Sign_Post", (x, y, 0.0), (x, y, 5.0), 0.12, "Steel_Dark", 8)
        box("Parking_Sign_Panel", (x, y, 4.2), (3.2, 0.25, 2.0), "Sign_Blue")
        text("Sign_Parking_Pylon", f"P{name}", (x, y - 0.16, 4.2), 1.0, "Sign_White", font=FONT_DISPLAY, extrude=0.02)
    flush()
    log("parking")


# ---------------------------------------------------------------------------
# Landscape: outfield berm, picnic zone, hill forest, city edge
# ---------------------------------------------------------------------------


def build_landscape() -> None:
    # grass berm beyond the outfield wall
    berm = []
    for k in range(25):
        t = k / 24
        angle = math.pi * t
        berm.append((math.cos(angle) * 86.0, 66.0 + math.sin(angle) * 16.0))
    flat_poly("WalkSurface_Berm", berm, 0.22, "WalkSurface_Berm")
    # picnic tables and playground behind the outfield
    for k in range(14):
        x = -70.0 + (k % 7) * 23.0
        y = 74.0 + (k // 7) * 7.0
        box("Picnic_Table_Top", (x, y, 0.95), (1.9, 0.9, 0.1), "Tree_Bark")
        box("Picnic_Table_Bench", (x, y - 0.75, 0.6), (1.9, 0.4, 0.08), "Tree_Bark")
        box("Picnic_Table_Bench", (x, y + 0.75, 0.6), (1.9, 0.4, 0.08), "Tree_Bark")
        for dx in (-0.7, 0.7):
            box("Picnic_Table_Leg", (x + dx, y, 0.45), (0.1, 0.8, 0.9), "Steel_Dark")
    # sand playground with a low wall
    flat_poly(
        "Sand_Playground",
        [(x, y) for x, y in [(-16, 78), (16, 78), (20, 92), (0, 98), (-20, 92)]],
        0.26,
        "Infield_Clay",
    )
    curb("Play_Ground_Curb", [(-16, 78), (16, 78), (20, 92), (0, 98), (-20, 92), (-16, 78)], 0.4, 0.36, "Stone_Light")
    for k in range(6):
        beam("Play_Ground_Fence", (-20 + k * 8.0, 96.0, 0.2), (-20 + k * 8.0, 96.0, 1.6), 0.05, "Steel_Galvanized", 5)
    # low fence along the berm
    for k in range(30):
        x = -86.0 + k * 6.0
        z = 0.2 + max(0.0, 2.0 - abs(x) / 60.0)
        beam("Berm_Fence_Post", (x, 82.0, 0.2), (x, 82.0, 1.5), 0.04, "Steel_Galvanized", 5)
    box("Berm_Fence_Rail", (0.0, 82.0, 1.4), (176.0, 0.06, 0.06), "Steel_Galvanized")

    # hill forest: pines and broadleaf trees
    rng = random.Random(7)
    for k in range(520):
        x = rng.uniform(-430.0, 430.0)
        y = rng.uniform(150.0, 470.0)
        if abs(x) < 120 and y < 210:
            continue
        z = hill_height(x, y) - 0.2
        if z < -1:
            continue
        variant = "C" if rng.random() < 0.55 else "A"
        tree(x, y, z, rng.uniform(6.5, 11.5), variant, rng.uniform(0.8, 1.1))
    # street trees along the far side of the plaza, clear of the entrance axis
    for k in range(28):
        x = -162.0 + k * 12.0
        if abs(x) < 26.0:
            continue
        tree(x, -218.0, 0.2, 8.6, "B", 0.9)
    # city edge blocks far to the north for skyline depth
    rng = random.Random(11)
    for k in range(26):
        x = -560.0 + rng.uniform(-30, 30) + k * 44.0
        y = -520.0 + rng.uniform(-60, 40)
        h = rng.uniform(26.0, 62.0)
        box("Distant_Urban_Block", (x, y, h / 2), (rng.uniform(22, 38), rng.uniform(18, 30), h), "Facade_Panel")
    flush()
    log("landscape")


# ---------------------------------------------------------------------------
# Driveable car (runtime object) + traffic
# ---------------------------------------------------------------------------


def build_driveable_car() -> None:
    root = bpy.data.objects.new("Driveable_Car", None)
    COL.objects.link(root)
    root.location = (-130.0, ROAD_Y + 10.0, 0.1)
    root.rotation_euler = (0.0, 0.0, -math.pi / 2)
    root["driveable"] = True

    def car_mesh(name, verts, faces, mat, bevel=0.0):
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(verts, [], faces)
        mesh.update()
        obj = bpy.data.objects.new(name, mesh)
        COL.objects.link(obj)
        obj.parent = root
        mesh.materials.append(MATS[mat])
        if bevel:
            for other in bpy.context.selected_objects:
                other.select_set(False)
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            modifier = obj.modifiers.new("Soft_edges", "BEVEL")
            modifier.width = bevel
            modifier.segments = 3
            bpy.ops.object.modifier_apply(modifier=modifier.name)
        return obj

    def car_box(name, center, size, mat, bevel=0.0):
        x, y, z = center
        a, b, c = (v / 2 for v in size)
        verts = [
            (x - a, y - b, z - c),
            (x + a, y - b, z - c),
            (x + a, y + b, z - c),
            (x - a, y + b, z - c),
            (x - a, y - b, z + c),
            (x + a, y - b, z + c),
            (x + a, y + b, z + c),
            (x - a, y + b, z + c),
        ]
        return car_mesh(name, verts, BOX_FACES, mat, bevel)

    sections = [(-2.3, 0.7, 0.34, 0.66), (-2.0, 0.9, 0.3, 0.8), (-1.0, 0.95, 0.3, 0.9), (0.9, 0.95, 0.3, 0.9), (2.0, 0.87, 0.34, 0.76), (2.3, 0.7, 0.4, 0.62)]
    verts = []
    for y, w, lo, hi in sections:
        verts.extend([(-w, y, lo), (w, y, lo), (w, y, hi), (-w, y, hi)])
    faces = [(3, 2, 1, 0), (20, 21, 22, 23)]
    for j in range(len(sections) - 1):
        for k in range(4):
            faces.append((j * 4 + k, j * 4 + (k + 1) % 4, (j + 1) * 4 + (k + 1) % 4, (j + 1) * 4 + k))
    body = car_mesh("Car_Painted_Body", verts, faces, "Car_Paint_3", 0.07)
    cabin = [
        (-0.82, -1.15, 0.88),
        (0.82, -1.15, 0.88),
        (0.82, 0.95, 0.88),
        (-0.82, 0.95, 0.88),
        (-0.62, -0.72, 1.44),
        (0.62, -0.72, 1.44),
        (0.62, 0.3, 1.44),
        (-0.62, 0.3, 1.44),
    ]
    car_mesh("Car_Glass_Cabin", cabin, [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7), (4, 5, 6, 7)], "Car_Glass", 0.03)
    car_box("Car_Painted_Roof", (0, -0.2, 1.45), (1.3, 1.05, 0.07), "Car_Paint_3", 0.04)
    car_box("Car_Front_Grille", (0, 2.27, 0.52), (0.8, 0.05, 0.18), "Car_Trim", 0.02)
    for side in (-1, 1):
        car_box("Car_Headlamp", (side * 0.55, 2.16, 0.72), (0.46, 0.1, 0.15), "Car_Lamp", 0.03)
        car_box("Car_Taillamp", (side * 0.55, -2.22, 0.72), (0.44, 0.08, 0.12), "Sign_Red", 0.02)
        car_box("Car_Side_Mirror", (side * 1.02, 0.66, 1.02), (0.24, 0.18, 0.14), "Car_Paint_3", 0.03)
        car_box("Car_Door_Handle", (side * 0.97, -0.2, 0.88), (0.04, 0.22, 0.07), "Car_Trim", 0.01)
        for wheel_y in (-1.45, 1.45):
            for name, radius, depth, mat in (("Tire", 0.35, 0.24, "Car_Tire"), ("Alloy", 0.23, 0.255, "Car_Trim")):
                verts = []
                for x in (side * 0.9 - depth / 2, side * 0.9 + depth / 2):
                    for j in range(18):
                        angle = j * math.tau / 18
                        verts.append((x, wheel_y + radius * math.sin(angle), 0.35 + radius * math.cos(angle)))
                faces = [tuple(reversed(range(18))), tuple(range(18, 36))]
                faces += [(j, (j + 1) % 18, (j + 1) % 18 + 18, j + 18) for j in range(18)]
                car_mesh("Car_Wheel_" + name, verts, faces, mat)
    # contact shadow
    shadow_verts = [(-1.15, -2.45, 0.02), (1.15, -2.45, 0.02), (1.15, 2.45, 0.02), (-1.15, 2.45, 0.02)]
    shadow = car_mesh("Car_Contact_Shadow", shadow_verts, [(0, 1, 2, 3)], "Car_Tire")
    shadow.data.materials[0] = MATS["Car_Trim"]
    log("driveable car")


def build_traffic() -> None:
    rng = random.Random(23)
    for k in range(9):
        lane = ROAD_Y + (5.8 if k % 2 else -5.8) + (0 if k % 3 else 4.0)
        x = -420.0 + k * 92.0 + rng.uniform(-12, 12)
        parked_car(x, lane, 0.0 if k % 2 else math.pi, k)
    for k in range(5):
        y = 60.0 - k * 90.0
        parked_car(-215.0 + (6.0 if k % 2 else -6.0), y, math.pi / 2 if k % 2 else -math.pi / 2, k + 2)
    flush()
    log("traffic")

build_plaza()
build_roads()
build_station()
build_parking()
build_landscape()
build_driveable_car()
build_traffic()

# ---------------------------------------------------------------------------
# Preview lighting + camera
# ---------------------------------------------------------------------------


def setup_daylight() -> None:
    world = bpy.data.worlds.new("LSV4_Sky")
    SCENE.world = world
    world.use_nodes = True
    background = world.node_tree.nodes["Background"]
    background.inputs[0].default_value = (*srgb("#c3d8ea"), 1.0)
    background.inputs[1].default_value = 1.0
    sun_data = bpy.data.lights.new("LSV4_Sun", "SUN")
    sun_data.energy = 4.0
    sun_data.angle = math.radians(1.6)
    sun_data.color = (1.0, 0.96, 0.90)
    sun = bpy.data.objects.new("LSV4_Sun", sun_data)
    COL.objects.link(sun)
    sun.rotation_euler = (math.radians(50), 0.0, math.radians(38))


def setup_camera(name: str, location, target, lens: float = 45.0, ortho: float | None = None):
    data = bpy.data.cameras.new(name)
    data.lens = lens
    data.clip_start = 0.5
    data.clip_end = 4000.0
    if ortho:
        data.type = "ORTHO"
        data.ortho_scale = ortho
    camera = bpy.data.objects.new(name, data)
    COL.objects.link(camera)
    camera.location = location
    camera.rotation_euler = (Vector(target) - Vector(location)).to_track_quat("-Z", "Y").to_euler()
    return camera


def render(path: Path, resolution=(1600, 1000), samples: int = 32) -> None:
    if SKIP_RENDER:
        return
    # Cycles on CPU: the pipeline must run on headless machines without a GPU.
    SCENE.render.engine = "CYCLES"
    SCENE.cycles.device = "CPU"
    SCENE.cycles.samples = samples
    SCENE.cycles.use_denoising = os.environ.get("LSV4_DENOISE", "0") == "1"
    SCENE.cycles.max_bounces = 6
    SCENE.cycles.diffuse_bounces = 3
    SCENE.cycles.glossy_bounces = 3
    SCENE.cycles.transmission_bounces = 2
    SCENE.cycles.use_adaptive_sampling = True
    SCENE.cycles.adaptive_threshold = 0.05
    SCENE.render.resolution_x, SCENE.render.resolution_y = resolution
    SCENE.render.resolution_percentage = 100
    SCENE.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    SCENE.render.engine = "BLENDER_EEVEE_NEXT"
    log(f"render {path.name}")


RENDER_MODE = os.environ.get("LSV4_RENDER", "all")
DO_EXPORT = os.environ.get("LSV4_EXPORT", "1") != "0"


def setup_night() -> list:
    """Night preview: dark sky plus blue facade wash and warm plaza pools."""
    world = SCENE.world
    background = world.node_tree.nodes["Background"]
    background.inputs[0].default_value = (*srgb("#070b1c"), 1.0)
    background.inputs[1].default_value = 0.25
    sun = bpy.data.objects.get("LSV4_Sun")
    if sun:
        sun.data.energy = 0.35
        sun.data.color = (0.55, 0.68, 1.0)
    created = []
    for x in (-70.0, 0.0, 70.0):
        data = bpy.data.lights.new(f"Night_Wash_{int(x)}", "AREA")
        data.energy = 16000.0
        data.shape = "RECTANGLE"
        data.size = 34.0
        data.size_y = 12.0
        data.color = (0.35, 0.55, 1.0)
        obj = bpy.data.objects.new(f"Night_Wash_{int(x)}", data)
        COL.objects.link(obj)
        obj.location = (x, -152.0, 16.0)
        obj.rotation_euler = (Vector((x, -132.0, 14.0)) - obj.location).to_track_quat("-Z", "Y").to_euler()
        created.append(obj)
    for x, y in [(-40.0, -190.0), (40.0, -175.0)]:
        data = bpy.data.lights.new(f"Night_Plaza_{int(x)}", "AREA")
        data.energy = 5000.0
        data.size = 16.0
        data.color = (1.0, 0.82, 0.6)
        obj = bpy.data.objects.new(f"Night_Plaza_{int(x)}", data)
        COL.objects.link(obj)
        obj.location = (x, y, 9.0)
        obj.rotation_euler = (0.0, 0.0, 0.0)
        created.append(obj)
    return created


setup_daylight()
if RENDER_MODE in ("all", "aerial"):
    SCENE.camera = setup_camera("LSV4_Aerial_Camera", (330.0, -440.0, 265.0), (0.0, -60.0, 8.0), 40.0)
    render(REF_DIR / "aerial-v4.png", (1280, 800), 20)
if RENDER_MODE in ("all", "plaza"):
    SCENE.camera = setup_camera("LSV4_Plaza_Camera", (6.0, -206.0, 6.2), (0.0, -130.0, 16.0), 32.0)
    render(REF_DIR / "plaza-v4.png", (1152, 720), 24)
if RENDER_MODE in ("all", "night"):
    night_lights = setup_night()
    SCENE.camera = setup_camera("LSV4_Night_Camera", (-60.0, -238.0, 16.0), (20.0, -110.0, 20.0), 40.0)
    LSV4_NIGHT_DENOISE = True
    SCENE.cycles.use_denoising = True
    render(REF_DIR / "night-v4.png", (1152, 720), 40)
    for obj in night_lights:
        bpy.data.objects.remove(obj, do_unlink=True)
if not DO_EXPORT:
    log("render-only run finished")
    raise SystemExit(0)

# ===========================================================================
# Collision index, web export, blend save, manifest
# ===========================================================================


def physical(ob) -> bool:
    if ob.type != "MESH" or ob.get("stable_logo"):
        return False
    parent = ob.parent
    while parent:
        if parent.name.startswith("Driveable_Car"):
            return False
        parent = parent.parent
    skip = (
        "WalkSurface",
        "Sky",
        "Night_",
        "Field_",
        "Foul_Lines",
        "Home_Plate",
        "Batters_Box",
        "Catchers_Box",
        "Infield_",
        "Road_",
        "Zebra_",
        "Junction_",
        "Parking_Stall",
        "Plaza_Paving",
        "Drain_Slots",
        "Signal_Housing",
        "Seat_",
        "Bowl_Step",
        "Tree_Canopy",
        "Grass_",
        "Parking_Stall_Line",
        "Grand_Stair_Riser",
        "Med_Traffic_Island",
        "Distant_Urban",
    )
    if ob.name.startswith(skip):
        return False
    # thin ground decals never block a walker
    if ob.name.startswith("Parking_Stall_Line"):
        return False
    return True


def object_solids(ob) -> list[dict]:
    mesh = ob.data
    count = len(mesh.vertices)
    if count == 0:
        return []
    edges = np.empty(len(mesh.edges) * 2, dtype=np.int32)
    mesh.edges.foreach_get("vertices", edges)
    edges = edges.reshape(-1, 2)
    parent = np.arange(count, dtype=np.int32)

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for a, b in edges:
        ra, rb = find(int(a)), find(int(b))
        if ra != rb:
            parent[rb] = ra
    groups: dict[int, list[int]] = {}
    for i in range(count):
        groups.setdefault(find(i), []).append(i)
    coords = np.empty(count * 3, dtype=np.float64)
    mesh.vertices.foreach_get("co", coords)
    coords = coords.reshape(-1, 3)
    matrix = np.array(ob.matrix_world)
    world = coords @ matrix[:3, :3].T + matrix[:3, 3]
    # Blender (x, y, z) -> web (x, -y, z)
    pts_all = np.stack([world[:, 0], -world[:, 1], world[:, 2]], axis=1)
    solids = []
    for indices in groups.values():
        if len(indices) < 4:
            continue
        p = pts_all[indices]
        xy = p[:, :2]
        zlo, zhi = float(p[:, 2].min()), float(p[:, 2].max())
        if zhi - zlo < 0.1 and zhi < 0.4:
            continue
        center = xy.mean(axis=0)
        q = xy - center
        xx = float((q[:, 0] * q[:, 0]).mean())
        zz = float((q[:, 1] * q[:, 1]).mean())
        xz = float((q[:, 0] * q[:, 1]).mean())
        angle = 0.5 * math.atan2(2 * xz, xx - zz)
        c, s = math.cos(angle), math.sin(angle)
        ax = q[:, 0] * c + q[:, 1] * s
        az = -q[:, 0] * s + q[:, 1] * c
        lo0, hi0 = float(ax.min()), float(ax.max())
        lo1, hi1 = float(az.min()), float(az.max())
        if hi0 - lo0 > 260 or hi1 - lo1 > 260:
            continue
        u = (lo0 + hi0) / 2
        v = (lo1 + hi1) / 2
        solids.append(
            dict(
                cx=round(float(center[0] + u * c - v * s), 4),
                cz=round(float(center[1] + u * s + v * c), 4),
                hx=round(max(0.02, (hi0 - lo0) / 2), 4),
                hz=round(max(0.02, (hi1 - lo1) / 2), 4),
                yaw=round(angle, 6),
                minY=round(zlo, 4),
                maxY=round(zhi, 4),
            )
        )
    return solids


def build_collision() -> tuple[list[dict], list[dict]]:
    solids: list[dict] = []
    for ob in list(COL.objects):
        if physical(ob):
            solids.extend(object_solids(ob))
    night = []
    # floodlight anchors
    for cx, cy in [(-168.0, -96.0), (168.0, -96.0), (-168.0, 96.0), (168.0, 96.0)]:
        night.append(dict(kind="flood", position=[cx * 0.94, 46.0, -cy * 0.94], target=[0.0, 12.0, 0.0]))
    # facade wash
    for x, y in [(0.0, -138.0), (120.0, -40.0), (-120.0, -40.0)]:
        night.append(dict(kind="facade", position=[x, 18.0, -y], target=[x * 0.6, 8.0, -y * 0.6]))
    # plaza and roadside lamps
    for x in range(-150, 160, 30):
        night.append(dict(kind="road", position=[float(x), 7.2, 222.0], target=[float(x), 0.0, 222.0]))
    for y in range(-200, -110, 24):
        night.append(dict(kind="road", position=[-150.0, 7.2, -y], target=[-150.0, 0.0, -y]))
    log(f"collision ({len(solids)} solids)")
    return solids, night


solids, night_lights = build_collision()
collision = dict(
    boxes=[],
    solids=solids,
    spawn=[0.0, 1.7, 165.0],
    overview=[320.0, 250.0, 430.0],
    vehicleSpawn=[-130.0, 0.1, 235.0, -math.pi / 2],
    nightLights=night_lights,
    units="meters",
    version="district-v4",
    source="Blender v4 procedural district build; oriented bounds per loose component",
)
(OUT / "lionspark-collision.json").write_text(json.dumps(collision, separators=(",", ":")), encoding="utf-8")
log(f"collision json {(OUT / 'lionspark-collision.json').stat().st_size / 1e6:.1f} MB")

# ---- GLB export ----
for ob in bpy.data.objects:
    ob.select_set(False)
selected = [ob for ob in COL.objects if ob.type in {"MESH", "EMPTY"}]
for ob in selected:
    ob.select_set(True)
bpy.context.view_layer.objects.active = selected[0] if selected else None

import contextlib
import io

with contextlib.redirect_stdout(io.StringIO()):
    bpy.ops.export_scene.gltf(
        filepath=str(OUT / "lionspark.glb"),
        export_format="GLB",
        use_selection=True,
        use_active_scene=True,
        use_visible=False,
        use_renderable=False,
        export_apply=True,
        export_yup=True,
        export_extras=True,
        export_animations=False,
        export_image_format="AUTO",
        export_draco_mesh_compression_enable=True,
        export_draco_mesh_compression_level=6,
        export_draco_position_quantization=16,
        export_draco_normal_quantization=10,
        export_draco_texcoord_quantization=12,
    )
log(f"glb {(OUT / 'lionspark.glb').stat().st_size / 1e6:.1f} MB")

(OUT / "lionspark-scene.json").write_text(
    json.dumps(
        dict(
            version="district-v4",
            footprintSides=8,
            footprint=P,
            clock="Asia/Seoul live epoch time",
            solidCount=len(solids),
            vehicle="Driveable_Car",
            district=[
                "octagonal stadium with two-tier bowl",
                "outfield scoreboard 36 x 20.4 m on steel frame",
                "Dalgubeol-daero 10 lanes with median planting",
                "Daegongwon station exits 4 and 5",
                "gate 2 plaza, ticket box, team store, golden lion",
                "P1 and P2 parking",
                "outfield berm, sand playground, Yeonhosan forest hill",
            ],
            features=[
                "procedural PBR materials with packed textures",
                "mowing stripes and infield clay",
                "cantilever roof with trusses and skylights",
                "night facade wash, floodlights and road lamps",
                "walking, driving, oriented per-object collision",
            ],
            source="Procedural v4 build script; interpretative reconstruction of the supplied references",
        ),
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)


def scrub_glb(path: Path) -> None:
    """Remove PNG text metadata (local file paths) from embedded textures."""
    data = path.read_bytes()
    magic, version, total = struct.unpack("<III", data[:12])
    if magic != 0x46546C67:
        return
    offset = 12
    chunks = []
    while offset < len(data):
        length, kind = struct.unpack("<II", data[offset : offset + 8])
        payload = data[offset + 8 : offset + 8 + length]
        chunks.append([kind, payload])
        offset += 8 + length
    json_chunk = json.loads(chunks[0][1].decode("utf-8"))
    views = json_chunk.get("bufferViews", [])
    images = json_chunk.get("images", [])
    png_sig = b"\x89PNG\r\n\x1a\n"

    def clean_png(blob: bytes) -> bytes:
        if not blob.startswith(png_sig):
            return blob
        out = blob[:8]
        pos = 8
        removed = False
        while pos + 8 <= len(blob):
            length = struct.unpack(">I", blob[pos : pos + 4])[0]
            ctype = blob[pos + 4 : pos + 8]
            end = pos + 12 + length
            if ctype not in (b"tEXt", b"iTXt", b"zTXt", b"tIME"):
                out += blob[pos:end]
            else:
                removed = True
            pos = end
        return out if removed else blob

    bin_chunk = chunks[1][1]
    view_map = {}
    new_bin = bytearray()
    for view in views:
        start = view.get("byteOffset", 0)
        length = view["byteLength"]
        view_map[id(view)] = (len(new_bin), length)
        new_bin += bin_chunk[start : start + length]
        while len(new_bin) % 4:
            new_bin.append(0)
    # clean the image buffer views in place
    for image in images:
        index = image.get("bufferView")
        if index is None:
            continue
        view = views[index]
        start = view.get("byteOffset", 0)
        length = view["byteLength"]
        blob = bin_chunk[start : start + length]
        cleaned = clean_png(blob)
        if cleaned is not blob and len(cleaned) != length:
            # rebuild bin with the new blob
            shift = len(cleaned) - length
            head = bytes(new_bin[:start])
            tail = bytes(new_bin[start + length :])
            new_bin = bytearray(head + cleaned + tail)
            while len(new_bin) % 4:
                new_bin.append(0)
            for j in range(index + 1, len(views)):
                other = views[j]
                other["byteOffset"] = other.get("byteOffset", 0) + shift
            view["byteLength"] = len(cleaned)
    json_chunk["buffers"][0]["byteLength"] = len(new_bin)
    new_json = json.dumps(json_chunk, separators=(",", ":")).encode("utf-8")
    while len(new_json) % 4:
        new_json += b" "
    while len(new_bin) % 4:
        new_bin.append(0)
    body = struct.pack("<II", len(new_json), 0x4E4F534A) + new_json
    body += struct.pack("<II", len(new_bin), 0x004E4942) + bytes(new_bin)
    path.write_bytes(struct.pack("<III", magic, version, 12 + len(body)) + body)


# Blender 4.2 writes packed textures without PNG text chunks, so no post-scrub is needed.

# ---- save the editable scene ----
SCENE.render.engine = "BLENDER_EEVEE_NEXT"
# leave the file opening on a useful overview camera
if "LSV4_Aerial_Camera" not in bpy.data.objects:
    SCENE.camera = setup_camera("LSV4_Aerial_Camera", (330.0, -440.0, 265.0), (0.0, -60.0, 8.0), 40.0)
else:
    SCENE.camera = bpy.data.objects["LSV4_Aerial_Camera"]
setup_daylight()
SCENE.render.resolution_x, SCENE.render.resolution_y = 1600, 1000
SCENE.frame_start, SCENE.frame_end = 1, 1
SCENE["version"] = "district-v4"
SCENE["units"] = "meters"
for other in list(bpy.data.scenes):
    if other != SCENE:
        bpy.data.scenes.remove(other)
used = set(SCENE.objects)
for ob in list(bpy.data.objects):
    if ob not in used:
        bpy.data.objects.remove(ob, do_unlink=True)
bpy.data.orphans_purge(do_recursive=True)
bpy.ops.file.pack_all()
blend_path = ASSETS / "lionspark-v4.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), compress=True)
log(f"blend {blend_path.stat().st_size / 1e6:.1f} MB")

manifest = dict(
    version="district-v4",
    blend=blend_path.name,
    blendBytes=blend_path.stat().st_size,
    blendSha256=hashlib.sha256(blend_path.read_bytes()).hexdigest(),
    glbBytes=(OUT / "lionspark.glb").stat().st_size,
    glbSha256=hashlib.sha256((OUT / "lionspark.glb").read_bytes()).hexdigest(),
    collisionBytes=(OUT / "lionspark-collision.json").stat().st_size,
    colliderCount=len(solids),
    nightLightCount=len(night_lights),
    seatCount=SEAT_COUNT,
    objects=len([ob for ob in COL.objects if ob.type == "MESH"]),
    blender="4.2.1 LTS",
    clock="Asia/Seoul real time",
)
(ASSETS / "v4-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
log(f"MANIFEST {manifest}")
