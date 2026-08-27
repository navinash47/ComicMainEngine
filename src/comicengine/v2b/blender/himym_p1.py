"""Standalone bpy script: HIMYM ep1 panel 1 living-room two-shot.

Run via blender --background --python himym_p1.py -- --out PATH
Does not import comicengine (Blender's Python is separate).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy
from mathutils import Vector


SEED = 42
SAMPLES = 32
RES_X = 768
RES_Y = 1152


def _argv_after_double_dash() -> list[str]:
    if "--" in sys.argv:
        return sys.argv[sys.argv.index("--") + 1 :]
    return []


def look_at(obj: bpy.types.Object, target: tuple[float, float, float]) -> None:
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def wipe_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for block in (bpy.data.meshes, bpy.data.materials, bpy.data.lights, bpy.data.cameras):
        for item in list(block):
            block.remove(item)


def mat(name: str, color: tuple[float, float, float], roughness: float = 0.55) -> bpy.types.Material:
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        if "Roughness" in bsdf.inputs:
            bsdf.inputs["Roughness"].default_value = roughness
    return m


def add_cube(name: str, scale: tuple[float, float, float], loc: tuple[float, float, float], material: bpy.types.Material) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = scale
    obj.data.materials.append(material)
    return obj


def add_capsule(name: str, loc: tuple[float, float, float], scale: float, material: bpy.types.Material) -> bpy.types.Object:
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.22 * scale, location=(loc[0], loc[1], loc[2] + 0.42 * scale))
    head = bpy.context.active_object
    head.name = f"{name}_head"
    head.data.materials.append(material)
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.18 * scale,
        depth=0.55 * scale,
        location=(loc[0], loc[1], loc[2] + 0.12 * scale),
    )
    body = bpy.context.active_object
    body.name = f"{name}_body"
    body.data.materials.append(material)
    return body


def build_living_room() -> None:
    wall = mat("wall", (0.22, 0.20, 0.18))
    floor_m = mat("floor", (0.28, 0.22, 0.18), roughness=0.7)
    sofa_m = mat("sofa", (0.18, 0.22, 0.28))
    dad_m = mat("dad", (0.20, 0.24, 0.32))
    maya_m = mat("maya", (0.55, 0.32, 0.16))
    lamp_m = mat("lamp", (0.85, 0.75, 0.45), roughness=0.35)

    add_cube("floor", (4.5, 4.5, 0.08), (0.0, 0.2, -0.04), floor_m)
    add_cube("wall_back", (4.5, 0.1, 2.6), (0.0, 2.0, 1.3), wall)
    add_cube("wall_left", (0.1, 4.5, 2.6), (-2.2, 0.2, 1.3), wall)
    add_cube("wall_right", (0.1, 4.5, 2.6), (2.2, 0.2, 1.3), wall)
    add_cube("sofa_base", (1.45, 0.5, 0.22), (0.05, 0.55, 0.22), sofa_m)
    add_cube("sofa_back", (1.45, 0.16, 0.5), (0.05, 0.78, 0.58), sofa_m)
    add_cube("lamp_stand", (0.06, 0.06, 0.85), (-1.35, 0.1, 0.85), lamp_m)

    # Sit on the sofa cushion (top ~0.33). Stage-right of Maya = camera-left.
    add_capsule("dad", (-0.38, 0.50, 0.55), 1.05, dad_m)
    add_capsule("maya", (0.42, 0.52, 0.50), 0.86, maya_m)

    bpy.ops.object.light_add(type="AREA", location=(-1.35, -0.2, 1.7))
    lamp = bpy.context.active_object
    lamp.name = "key_lamp"
    lamp.data.energy = 90.0
    lamp.data.color = (1.0, 0.82, 0.62)
    lamp.data.size = 0.4
    look_at(lamp, (0.05, 0.5, 0.7))

    bpy.ops.object.light_add(type="AREA", location=(0.5, -1.6, 1.9))
    fill = bpy.context.active_object
    fill.name = "fill"
    fill.data.energy = 14.0
    fill.data.color = (0.55, 0.62, 0.85)
    fill.data.size = 1.4

    bpy.ops.object.camera_add(location=(0.2, -4.15, 1.45))
    cam = bpy.context.active_object
    cam.name = "panel_cam"
    cam.data.lens = 45
    look_at(cam, (0.05, 0.55, 0.75))
    bpy.context.scene.camera = cam

    world = bpy.data.worlds.new("dim_world")
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (0.10, 0.09, 0.08, 1.0)
        bg.inputs[1].default_value = 0.25


def configure_cycles() -> None:
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.render.resolution_x = RES_X
    scene.render.resolution_y = RES_Y
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.film_transparent = False
    scene.cycles.samples = SAMPLES
    scene.cycles.seed = SEED
    scene.cycles.use_denoising = False
    scene.cycles.device = "CPU"
    scene.frame_current = 1
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.refresh_devices()
        metal = [d for d in prefs.devices if "METAL" in d.type or d.type == "METAL"]
        if metal:
            scene.cycles.device = "GPU"
            for d in prefs.devices:
                d.use = d in metal or d.type == "CPU"
    except Exception:
        scene.cycles.device = "CPU"


def render_to(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args(_argv_after_double_dash())
    wipe_scene()
    build_living_room()
    configure_cycles()
    render_to(Path(args.out))
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
