"""Dad (and optional Maya contrast) standing turntable AOVs. No sofa.

blender --background --python dad_turntable.py -- --out-dir PATH [--character dad|maya] [--quick]
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

_DIR = Path(__file__).resolve().parent
if str(_DIR) not in sys.path:
    sys.path.insert(0, str(_DIR))

from himym_p1 import (  # noqa: E402
    DAD_INDEX,
    MAYA_INDEX,
    add_lineart_object,
    build_compositor,
    configure_cycles,
    configure_view_layers,
    look_at,
    mat,
    wipe_scene,
)
from humanoid import add_standing_dad, add_standing_maya  # noqa: E402
from turntable_views import view_specs  # noqa: E402

SEED = 42
SAMPLES = 32
RES_X = 512
RES_Y = 768
RADIUS = 2.7
TARGET = (0.0, 0.0, 1.05)


def _argv_after_double_dash() -> list[str]:
    if "--" in sys.argv:
        return sys.argv[sys.argv.index("--") + 1 :]
    return []


def orbit(azimuth: float, elevation: float) -> tuple[float, float, float]:
    az = math.radians(azimuth)
    el = math.radians(elevation)
    x = TARGET[0] + RADIUS * math.cos(el) * math.sin(az)
    y = TARGET[1] - RADIUS * math.cos(el) * math.cos(az)
    z = TARGET[2] + RADIUS * math.sin(el)
    return (x, y, z)


def build_turntable(character: str) -> None:
    floor_m = mat("tt_floor", (0.42, 0.42, 0.40), roughness=0.85)
    dad_m = mat("dad", (0.20, 0.24, 0.32))
    maya_m = mat("maya", (0.55, 0.32, 0.16))
    dad_hair = mat("dad_hair", (0.12, 0.10, 0.09), roughness=0.75)
    maya_hair = mat("maya_hair", (0.18, 0.10, 0.06), roughness=0.7)
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.0, 0.0, -0.04))
    floor = bpy.context.active_object
    floor.name = "tt_floor"
    floor.scale = (6.0, 6.0, 0.08)
    floor.data.materials.append(floor_m)

    if character == "maya":
        add_standing_maya((0.0, 0.0, 0.0), maya_m, maya_hair, MAYA_INDEX, scale=0.86)
    else:
        add_standing_dad((0.0, 0.0, 0.0), dad_m, dad_hair, DAD_INDEX, scale=1.0)

    bpy.ops.object.light_add(type="AREA", location=(-1.4, -1.1, 2.2))
    key = bpy.context.active_object
    key.name = "key_lamp"
    key.data.energy = 110.0
    key.data.color = (1.0, 0.84, 0.64)
    key.data.size = 0.5
    look_at(key, TARGET)

    bpy.ops.object.light_add(type="AREA", location=(1.6, -0.8, 1.8))
    fill = bpy.context.active_object
    fill.name = "fill"
    fill.data.energy = 18.0
    fill.data.color = (0.55, 0.62, 0.85)
    fill.data.size = 1.6

    bpy.ops.object.camera_add(location=orbit(0, 12))
    cam = bpy.context.active_object
    cam.name = "tt_cam"
    cam.data.lens = 50.0
    look_at(cam, TARGET)
    bpy.context.scene.camera = cam

    world = bpy.data.worlds.new("tt_world")
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (0.55, 0.54, 0.52, 1.0)
        bg.inputs[1].default_value = 0.45


def render_views(out_dir: Path, views: list[dict[str, object]], file_out, samples: int) -> None:
    scene = bpy.context.scene
    cam = scene.camera
    scene.render.resolution_x = RES_X
    scene.render.resolution_y = RES_Y
    for spec in views:
        vid = str(spec["id"])
        dest = out_dir / vid
        dest.mkdir(parents=True, exist_ok=True)
        cam.location = Vector(orbit(float(spec["azimuth"]), float(spec["elevation"])))
        look_at(cam, TARGET)
        file_out.directory = str(dest)
        scene.render.filepath = str(dest / "_cycles")
        bpy.ops.render.render(write_still=True)
        leftover = dest / "_cycles.png"
        if leftover.is_file():
            leftover.unlink()
        print(f"wrote {dest}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--character", choices=("dad", "maya"), default="dad")
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--samples", type=int, default=SAMPLES)
    args = parser.parse_args(_argv_after_double_dash())
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    views = view_specs(quick=args.quick)
    (out_dir / "views.json").write_text(
        __import__("json").dumps({"character": args.character, "views": views}, indent=2) + "\n"
    )
    wipe_scene()
    build_turntable(args.character)
    add_lineart_object()
    configure_view_layers()
    configure_cycles(args.samples)
    bpy.context.scene.render.resolution_x = RES_X
    bpy.context.scene.render.resolution_y = RES_Y
    file_out = build_compositor()
    render_views(out_dir, views, file_out, args.samples)


if __name__ == "__main__":
    main()
