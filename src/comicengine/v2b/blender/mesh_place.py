"""Place a baked Kenney GLB and stamp object-index. bpy only (no comicengine)."""

from __future__ import annotations

from pathlib import Path

import bpy


def force_opaque(obj: bpy.types.Object) -> None:
    for mat in obj.data.materials:
        if not mat or not getattr(mat, "use_nodes", False):
            continue
        try:
            mat.blend_method = "OPAQUE"
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


def place_glb(
    path: Path,
    *,
    name: str,
    loc: tuple[float, float, float],
    scale: float,
    pass_index: int,
) -> list[bpy.types.Object]:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    imported = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in imported if o.type == "MESH"]
    if not meshes:
        raise RuntimeError(f"no mesh in {path}")
    root = meshes[0]
    root.name = name
    root.location = loc
    root.scale = (scale, scale, scale)
    root.pass_index = pass_index
    for obj in meshes:
        obj.pass_index = pass_index
        if obj != root:
            obj.name = f"{name}_{obj.name}"
        force_opaque(obj)
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.normals_make_consistent(inside=False)
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.context.view_layer.update()
    return meshes
