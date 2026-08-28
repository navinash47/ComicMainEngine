"""Spec-driven AOV render. Blender Python cannot import comicengine.

blender --background --python build_scene.py -- --location PATH --out-dir PATH --cameras a,b [--characters dad,daughter]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy

_DIR = Path(__file__).resolve().parent
if str(_DIR) not in sys.path:
    sys.path.insert(0, str(_DIR))

from himym_p1 import (  # noqa: E402
    DAD_INDEX,
    MAYA_INDEX,
    add_cube,
    add_lineart_object,
    build_compositor,
    configure_cycles,
    configure_view_layers,
    look_at,
    mat,
    wipe_scene,
)
from humanoid import add_seated_dad, add_seated_maya  # noqa: E402


def _argv_after_double_dash() -> list[str]:
    if "--" in sys.argv:
        return sys.argv[sys.argv.index("--") + 1 :]
    return []


def build_from_spec(loc: dict, character_ids: list[str]) -> dict[str, bpy.types.Object]:
    mats: dict[str, bpy.types.Material] = {}
    for prim in loc["primitives"]:
        key = tuple(prim["color"]) + (float(prim.get("roughness") or 0.55),)
        if key not in mats:
            mats[key] = mat(prim["name"], tuple(prim["color"]), roughness=float(prim.get("roughness") or 0.55))
        add_cube(prim["name"], tuple(prim["scale"]), tuple(prim["loc"]), mats[key])

    wanted = set(character_ids)
    dad_m = mat("dad", (0.20, 0.24, 0.32))
    maya_m = mat("maya", (0.55, 0.32, 0.16))
    dad_hair = mat("dad_hair", (0.12, 0.10, 0.09), roughness=0.75)
    maya_hair = mat("maya_hair", (0.18, 0.10, 0.06), roughness=0.7)
    for ch in loc.get("characters") or []:
        cid = str(ch["id"])
        aliases = {"dad": {"dad"}, "daughter": {"daughter", "maya"}, "maya": {"daughter", "maya"}}
        names = aliases.get(cid, {cid})
        if not wanted or not (names & wanted):
            continue
        pose = str(ch.get("pose") or "seated")
        loc3 = tuple(ch["loc"])
        scale = float(ch.get("scale") or 1.0)
        if cid == "dad" and pose == "seated":
            add_seated_dad(loc3, dad_m, dad_hair, DAD_INDEX, scale=scale)
        elif cid in {"daughter", "maya"} and pose == "seated":
            add_seated_maya(loc3, maya_m, maya_hair, MAYA_INDEX, scale=scale)

    for light in loc["lights"]:
        bpy.ops.object.light_add(type=str(light.get("kind") or "AREA"), location=tuple(light["location"]))
        obj = bpy.context.active_object
        obj.name = light["name"]
        obj.data.energy = float(light["energy"])
        obj.data.color = tuple(light["color"])
        obj.data.size = float(light.get("size") or 0.4)
        if light.get("target"):
            look_at(obj, tuple(light["target"]))

    cameras: dict[str, bpy.types.Object] = {}
    for cam_id, spec in loc["cameras"].items():
        bpy.ops.object.camera_add(location=tuple(spec["location"]))
        cam = bpy.context.active_object
        cam.name = f"panel_cam_{cam_id}"
        cam.data.lens = float(spec["lens"])
        look_at(cam, tuple(spec["target"]))
        cameras[cam_id] = cam
    bpy.context.scene.camera = next(iter(cameras.values()))

    world = bpy.data.worlds.new("spec_world")
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        wc = loc.get("world_color") or (0.10, 0.09, 0.08)
        bg.inputs[0].default_value = (*tuple(wc), 1.0)
        bg.inputs[1].default_value = float(loc.get("world_strength") or 0.25)
    return cameras


def render_cameras(out_dir: Path, cameras: dict[str, bpy.types.Object], cam_ids: list[str], file_out) -> None:
    scene = bpy.context.scene
    for cam_id in cam_ids:
        cam_dir = out_dir / f"cam_{cam_id}"
        cam_dir.mkdir(parents=True, exist_ok=True)
        scene.camera = cameras[cam_id]
        file_out.directory = str(cam_dir)
        scene.render.filepath = str(cam_dir / "_cycles")
        bpy.ops.render.render(write_still=True)
        leftover = cam_dir / "_cycles.png"
        if leftover.is_file():
            leftover.unlink()
        print(f"wrote {cam_dir}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--location", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--cameras", required=True)
    parser.add_argument("--characters", default="")
    parser.add_argument("--samples", type=int, default=32)
    args = parser.parse_args(_argv_after_double_dash())
    loc = json.loads(Path(args.location).read_text())
    cam_ids = [c.strip() for c in args.cameras.split(",") if c.strip()]
    for cam_id in cam_ids:
        if cam_id not in loc["cameras"]:
            raise SystemExit(f"unknown camera {cam_id} for {loc.get('id')}")
    character_ids = [c.strip() for c in args.characters.split(",") if c.strip()]
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    wipe_scene()
    cameras = build_from_spec(loc, character_ids)
    add_lineart_object()
    configure_view_layers()
    configure_cycles(args.samples)
    file_out = build_compositor()
    render_cameras(out_dir, cameras, cam_ids, file_out)


if __name__ == "__main__":
    main()
