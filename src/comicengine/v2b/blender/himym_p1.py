"""Standalone bpy script: HIMYM ep1 panel 1 living-room two-shot AOVs.

Run via blender --background --python himym_p1.py -- --out-dir PATH
Does not import comicengine (Blender's Python is separate).

Writes per camera under out-dir/cam_{a,b,c}/:
  beauty_01.png, depth_01.png, lineart_01.png, normal_01.png, index_01.png

Blender 5.2 Freestyle-as-pass is empty; lineart is Grease Pencil Line Art
composited on black (not canny-from-beauty). index RGB is dad=R, maya=G.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy
from mathutils import Vector

_DIR = Path(__file__).resolve().parent
if str(_DIR) not in sys.path:
    sys.path.insert(0, str(_DIR))
from humanoid import add_seated_dad, add_seated_maya  # noqa: E402


SEED = 42
SAMPLES = 32
RES_X = 768
RES_Y = 1152
DAD_INDEX = 1
MAYA_INDEX = 2
LINE_RADIUS = 0.012

# Hero two-shot, closer, slight profile — same sofa, walls in frame.
CAMERAS = {
    "a": {"location": (0.18, -3.55, 1.32), "lens": 38.0, "target": (0.05, 0.55, 0.72)},
    "b": {"location": (0.10, -2.45, 1.12), "lens": 50.0, "target": (0.05, 0.52, 0.70)},
    "c": {"location": (1.55, -3.00, 1.28), "lens": 42.0, "target": (0.08, 0.55, 0.72)},
}


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
    for block in (bpy.data.meshes, bpy.data.materials, bpy.data.lights, bpy.data.cameras, bpy.data.grease_pencils):
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


def add_cube(
    name: str,
    scale: tuple[float, float, float],
    loc: tuple[float, float, float],
    material: bpy.types.Material,
    pass_index: int = 0,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = scale
    obj.pass_index = pass_index
    obj.data.materials.append(material)
    return obj


def build_living_room() -> dict[str, bpy.types.Object]:
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

    dad_hair = mat("dad_hair", (0.12, 0.10, 0.09), roughness=0.75)
    maya_hair = mat("maya_hair", (0.18, 0.10, 0.06), roughness=0.7)
    add_seated_dad((-0.38, 0.50, 0.42), dad_m, dad_hair, DAD_INDEX, scale=1.05)
    add_seated_maya((0.42, 0.52, 0.40), maya_m, maya_hair, MAYA_INDEX, scale=0.86)

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

    cameras: dict[str, bpy.types.Object] = {}
    for cam_id, spec in CAMERAS.items():
        bpy.ops.object.camera_add(location=spec["location"])
        cam = bpy.context.active_object
        cam.name = f"panel_cam_{cam_id}"
        cam.data.lens = spec["lens"]
        look_at(cam, spec["target"])
        cameras[cam_id] = cam
    bpy.context.scene.camera = cameras["a"]

    world = bpy.data.worlds.new("dim_world")
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (0.10, 0.09, 0.08, 1.0)
        bg.inputs[1].default_value = 0.25
    return cameras


def add_lineart_object() -> bpy.types.Collection:
    bpy.ops.object.grease_pencil_add(type="LINEART_SCENE", use_in_front=True)
    gp = bpy.context.active_object
    gp.name = "LineArt"
    modifier = gp.modifiers[0]
    modifier.radius = LINE_RADIUS
    modifier.opacity = 1.0
    modifier.use_contour = True
    modifier.use_crease = True
    modifier.use_intersection = True
    style = gp.data.materials[0].grease_pencil
    style.show_stroke = True
    style.show_fill = False
    style.color = (1.0, 1.0, 1.0, 1.0)

    col = bpy.data.collections.new("lineart")
    scene = bpy.context.scene
    if col.name not in scene.collection.children:
        scene.collection.children.link(col)
    for existing in list(gp.users_collection):
        existing.objects.unlink(gp)
    col.objects.link(gp)
    return col


def _layer_collection(layer_coll: bpy.types.LayerCollection, name: str) -> bpy.types.LayerCollection | None:
    if layer_coll.name == name:
        return layer_coll
    for child in layer_coll.children:
        found = _layer_collection(child, name)
        if found:
            return found
    return None


def configure_view_layers() -> tuple[bpy.types.ViewLayer, bpy.types.ViewLayer]:
    scene = bpy.context.scene
    beauty = scene.view_layers[0]
    beauty.name = "beauty"
    beauty.use_pass_combined = True
    beauty.use_pass_z = True
    beauty.use_pass_normal = True
    beauty.use_pass_object_index = True
    beauty.use_pass_grease_pencil = False
    beauty.use_freestyle = False
    excluded = _layer_collection(beauty.layer_collection, "lineart")
    if excluded:
        excluded.exclude = True
    beauty.update_render_passes()

    if "lines" in scene.view_layers:
        lines = scene.view_layers["lines"]
    else:
        lines = scene.view_layers.new("lines")
    lines.use_pass_combined = True
    lines.use_pass_grease_pencil = True
    lines.use_pass_z = False
    lines.use_pass_normal = False
    lines.use_pass_object_index = False
    lines.use_freestyle = False
    lines.update_render_passes()
    return beauty, lines


def configure_cycles(samples: int) -> None:
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.render.resolution_x = RES_X
    scene.render.resolution_y = RES_Y
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.film_transparent = False
    scene.render.use_compositing = True
    scene.render.use_sequencer = False
    scene.render.use_freestyle = False
    scene.cycles.samples = samples
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


def _file_item(fo: bpy.types.CompositorNodeOutputFile, name: str, socket: str, color_mode: str) -> None:
    item = fo.file_output_items.new(socket, name)
    item.override_node_format = True
    item.format.file_format = "PNG"
    item.format.color_mode = color_mode
    item.save_as_render = False


def build_compositor() -> bpy.types.CompositorNodeOutputFile:
    scene = bpy.context.scene
    ng = bpy.data.node_groups.new("V2BComp", "CompositorNodeTree")
    ng.interface.new_socket(name="Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    rl_b = ng.nodes.new("CompositorNodeRLayers")
    rl_b.layer = "beauty"
    rl_l = ng.nodes.new("CompositorNodeRLayers")
    rl_l.layer = "lines"
    go = ng.nodes.new("NodeGroupOutput")
    norm = ng.nodes.new("CompositorNodeNormalize")
    inv = ng.nodes.new("CompositorNodeInvert")
    id_dad = ng.nodes.new("CompositorNodeIDMask")
    id_maya = ng.nodes.new("CompositorNodeIDMask")
    comb = ng.nodes.new("CompositorNodeCombineColor")
    black = ng.nodes.new("CompositorNodeRGB")
    black.outputs[0].default_value = (0.0, 0.0, 0.0, 1.0)
    over = ng.nodes.new("CompositorNodeAlphaOver")
    fo = ng.nodes.new("CompositorNodeOutputFile")
    fo.file_name = ""
    fo.format.media_type = "IMAGE"
    fo.format.file_format = "PNG"
    _file_item(fo, "beauty_01", "RGBA", "RGB")
    _file_item(fo, "depth_01", "FLOAT", "BW")
    _file_item(fo, "lineart_01", "RGBA", "RGB")
    _file_item(fo, "normal_01", "VECTOR", "RGB")
    _file_item(fo, "index_01", "RGBA", "RGB")

    id_dad.inputs["Index"].default_value = DAD_INDEX
    id_maya.inputs["Index"].default_value = MAYA_INDEX
    comb.inputs["Blue"].default_value = 0.0
    comb.inputs["Alpha"].default_value = 1.0

    links = ng.links
    links.new(rl_b.outputs["Image"], go.inputs["Image"])
    links.new(rl_b.outputs["Image"], fo.inputs["beauty_01"])
    links.new(rl_b.outputs["Depth"], norm.inputs[0])
    links.new(norm.outputs[0], inv.inputs["Color"])
    links.new(inv.outputs[0], fo.inputs["depth_01"])
    links.new(rl_b.outputs["Normal"], fo.inputs["normal_01"])
    links.new(rl_b.outputs["Object Index"], id_dad.inputs["ID value"])
    links.new(rl_b.outputs["Object Index"], id_maya.inputs["ID value"])
    links.new(id_dad.outputs["Alpha"], comb.inputs["Red"])
    links.new(id_maya.outputs["Alpha"], comb.inputs["Green"])
    links.new(comb.outputs["Image"], fo.inputs["index_01"])
    links.new(black.outputs[0], over.inputs["Background"])
    links.new(rl_l.outputs["Grease Pencil"], over.inputs["Foreground"])
    links.new(over.outputs[0], fo.inputs["lineart_01"])
    scene.compositing_node_group = ng
    return fo


def render_cameras(out_dir: Path, cameras: dict[str, bpy.types.Object], cam_ids: list[str], file_out: bpy.types.CompositorNodeOutputFile) -> None:
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
    parser.add_argument("--out-dir", dest="out_dir")
    parser.add_argument("--out", help="B1 alias: write cam_a beauty to this PNG as well")
    parser.add_argument("--cameras", default="a,b,c")
    parser.add_argument("--samples", type=int, default=SAMPLES)
    args = parser.parse_args(_argv_after_double_dash())
    if args.out_dir:
        out_dir = Path(args.out_dir)
    elif args.out:
        out_dir = Path(args.out).resolve().parent
    else:
        raise SystemExit("need --out-dir or --out")
    cam_ids = [c.strip() for c in args.cameras.split(",") if c.strip()]
    for cam_id in cam_ids:
        if cam_id not in CAMERAS:
            raise SystemExit(f"unknown camera {cam_id}; expected a,b,c")
    out_dir.mkdir(parents=True, exist_ok=True)
    wipe_scene()
    cameras = build_living_room()
    add_lineart_object()
    configure_view_layers()
    configure_cycles(args.samples)
    file_out = build_compositor()
    render_cameras(out_dir, cameras, cam_ids, file_out)
    if args.out:
        src = out_dir / "cam_a" / "beauty_01.png"
        dest = Path(args.out)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(src.read_bytes())
        print(f"wrote {dest}")


if __name__ == "__main__":
    main()
