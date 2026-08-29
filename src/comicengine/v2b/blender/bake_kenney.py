"""Bake Kenney protagonist FBX + skin PNG into static seated/standing GLBs.

blender --background --python bake_kenney.py -- --extract DIR --out-dir DIR --character dad --pose seated
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Euler, Vector

_DIR = Path(__file__).resolve().parent
if str(_DIR) not in sys.path:
    sys.path.insert(0, str(_DIR))


def _argv_after_double_dash() -> list[str]:
    if "--" in sys.argv:
        return sys.argv[sys.argv.index("--") + 1 :]
    return []


def wipe() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for coll in (bpy.data.meshes, bpy.data.armatures, bpy.data.materials, bpy.data.images, bpy.data.cameras, bpy.data.lights):
        for item in list(coll):
            coll.remove(item)


def world_bbox(obj: bpy.types.Object) -> tuple[Vector, Vector]:
    coords = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    xs = [c.x for c in coords]
    ys = [c.y for c in coords]
    zs = [c.z for c in coords]
    return Vector((min(xs), min(ys), min(zs))), Vector((max(xs), max(ys), max(zs)))


def force_opaque(obj: bpy.types.Object) -> None:
    for mat in obj.data.materials:
        if not mat or not mat.use_nodes:
            continue
        try:
            mat.blend_method = "OPAQUE"
        except Exception:
            pass
        if hasattr(mat, "surface_render_method"):
            try:
                mat.surface_render_method = "DITHERED"
            except Exception:
                pass
        nt = mat.node_tree
        bsdf = nt.nodes.get("Principled BSDF")
        if not bsdf or "Alpha" not in bsdf.inputs:
            continue
        for link in list(nt.links):
            if link.to_socket == bsdf.inputs["Alpha"]:
                nt.links.remove(link)
        bsdf.inputs["Alpha"].default_value = 1.0


def assign_skin(mesh: bpy.types.Object, png: Path) -> None:
    img = bpy.data.images.load(str(png))
    img.name = png.stem
    mat = mesh.data.materials[0] if mesh.data.materials else bpy.data.materials.new("skin")
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    if bsdf:
        nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    if not mesh.data.materials:
        mesh.data.materials.append(mat)
    else:
        mesh.data.materials[0] = mat
    force_opaque(mesh)


def set_euler(bone: bpy.types.PoseBone, x: float, y: float, z: float) -> None:
    bone.rotation_mode = "XYZ"
    bone.rotation_euler = Euler((math.radians(x), math.radians(y), math.radians(z)))


def pose_character(arm: bpy.types.Object, pose: str) -> None:
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="POSE")
    pb = arm.pose.bones
    # Arms slightly off T-pose so the turntable is a person, not a crucifix.
    if "LeftArm" in pb:
        set_euler(pb["LeftArm"], 8, 0, 62)
    if "RightArm" in pb:
        set_euler(pb["RightArm"], 8, 0, -62)
    if "LeftForeArm" in pb:
        set_euler(pb["LeftForeArm"], 18, 0, 8)
    if "RightForeArm" in pb:
        set_euler(pb["RightForeArm"], 18, 0, -8)
    if pose == "seated":
        if "Hips" in pb:
            set_euler(pb["Hips"], -14, 0, 0)
        if "Spine" in pb:
            set_euler(pb["Spine"], 10, 0, 0)
        if "Chest" in pb:
            set_euler(pb["Chest"], 8, 0, 0)
        if "LeftUpLeg" in pb:
            set_euler(pb["LeftUpLeg"], 86, 0, 10)
        if "RightUpLeg" in pb:
            set_euler(pb["RightUpLeg"], 86, 0, -10)
        if "LeftLeg" in pb:
            set_euler(pb["LeftLeg"], 82, 0, 0)
        if "RightLeg" in pb:
            set_euler(pb["RightLeg"], 82, 0, 0)
        if "LeftFoot" in pb:
            set_euler(pb["LeftFoot"], -18, 0, 0)
        if "RightFoot" in pb:
            set_euler(pb["RightFoot"], -18, 0, 0)
        if "LeftArm" in pb:
            set_euler(pb["LeftArm"], 35, 8, 35)
        if "RightArm" in pb:
            set_euler(pb["RightArm"], 35, -8, -35)
        if "LeftForeArm" in pb:
            set_euler(pb["LeftForeArm"], 55, 0, 0)
        if "RightForeArm" in pb:
            set_euler(pb["RightForeArm"], 55, 0, 0)
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.context.view_layer.update()


def apply_armature(mesh: bpy.types.Object, arm: bpy.types.Object) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    mesh.select_set(True)
    bpy.context.view_layer.objects.active = mesh
    for mod in list(mesh.modifiers):
        if mod.type == "ARMATURE":
            bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.delete()


def origin_at(mesh: bpy.types.Object, world: Vector) -> None:
    bpy.context.scene.cursor.location = world
    bpy.ops.object.select_all(action="DESELECT")
    mesh.select_set(True)
    bpy.context.view_layer.objects.active = mesh
    bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
    mesh.location = (0.0, 0.0, 0.0)
    bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)


def bake(extract: Path, out_dir: Path, character: str, pose: str, skin: str, fbx_rel: str, target_height: float) -> dict[str, object]:
    wipe()
    fbx = extract / fbx_rel
    png = extract / skin
    if not fbx.is_file():
        raise SystemExit(f"missing FBX {fbx}")
    if not png.is_file():
        raise SystemExit(f"missing skin {png}")
    bpy.ops.import_scene.fbx(filepath=str(fbx))
    extras = [o for o in bpy.data.objects if o.type in {"CAMERA", "LIGHT"} or o.name == "Cube"]
    bpy.ops.object.select_all(action="DESELECT")
    for o in extras:
        o.select_set(True)
    if extras:
        bpy.ops.object.delete()
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    if not meshes or not arms:
        raise SystemExit(f"expected mesh+armature, got meshes={len(meshes)} arms={len(arms)}")
    mesh = meshes[0]
    arm = arms[0]
    assign_skin(mesh, png)
    lo, hi = world_bbox(mesh)
    height = max(hi.z - lo.z, 1e-4)
    s = target_height / height
    arm.scale = (s, s, s)
    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bpy.context.view_layer.update()
    pose_character(arm, pose)
    bpy.context.view_layer.update()
    hips = Vector((0.0, 0.0, 0.0))
    if "Hips" in arm.pose.bones:
        hips = (arm.matrix_world @ arm.pose.bones["Hips"].matrix).translation.copy()
    apply_armature(mesh, arm)
    bpy.ops.object.select_all(action="DESELECT")
    mesh.select_set(True)
    bpy.context.view_layer.objects.active = mesh
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    bpy.context.view_layer.update()
    if pose == "seated":
        origin_at(mesh, hips)
    else:
        lo, hi = world_bbox(mesh)
        origin_at(mesh, Vector((0.0, 0.0, lo.z)))
    lo, hi = world_bbox(mesh)
    dest = out_dir / f"{character}_{pose}.glb"
    dest.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    mesh.select_set(True)
    bpy.context.view_layer.objects.active = mesh
    bpy.ops.export_scene.gltf(
        filepath=str(dest),
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_materials="EXPORT",
        export_texcoords=True,
        export_normals=True,
        export_image_format="AUTO",
    )
    meta = {
        "character": character,
        "pose": pose,
        "glb": str(dest),
        "bytes": dest.stat().st_size,
        "bbox_min": [round(lo.x, 4), round(lo.y, 4), round(lo.z, 4)],
        "bbox_max": [round(hi.x, 4), round(hi.y, 4), round(hi.z, 4)],
        "target_height": target_height,
        "skin": skin,
    }
    (dest.with_suffix(".json")).write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps(meta))
    return meta


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--extract", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--character", required=True)
    parser.add_argument("--pose", choices=("standing", "seated"), required=True)
    parser.add_argument("--skin", required=True)
    parser.add_argument("--fbx", default="Model/characterMedium.fbx")
    parser.add_argument("--target-height", type=float, required=True)
    args = parser.parse_args(_argv_after_double_dash())
    bake(
        Path(args.extract),
        Path(args.out_dir),
        args.character,
        args.pose,
        args.skin,
        args.fbx,
        args.target_height,
    )


if __name__ == "__main__":
    main()
