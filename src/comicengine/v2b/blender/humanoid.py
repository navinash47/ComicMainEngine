"""Block humanoids for Blender 2B. Import only from bpy scripts (no comicengine)."""

from __future__ import annotations

import math

import bpy


def _apply(obj: bpy.types.Object, material: bpy.types.Material, pass_index: int) -> bpy.types.Object:
    obj.pass_index = pass_index
    if obj.data.materials:
        obj.data.materials[0] = material
    else:
        obj.data.materials.append(material)
    return obj


def cube(
    name: str,
    scale: tuple[float, float, float],
    loc: tuple[float, float, float],
    material: bpy.types.Material,
    pass_index: int = 0,
    rotation: tuple[float, float, float] | None = None,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = scale
    if rotation:
        obj.rotation_euler = rotation
    return _apply(obj, material, pass_index)


def sphere(
    name: str,
    radius: float,
    loc: tuple[float, float, float],
    material: bpy.types.Material,
    pass_index: int,
    scale: tuple[float, float, float] | None = None,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, location=loc)
    obj = bpy.context.active_object
    obj.name = name
    if scale:
        obj.scale = scale
    return _apply(obj, material, pass_index)


def cylinder(
    name: str,
    radius: float,
    depth: float,
    loc: tuple[float, float, float],
    material: bpy.types.Material,
    pass_index: int,
    rotation: tuple[float, float, float] | None = None,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth, location=loc)
    obj = bpy.context.active_object
    obj.name = name
    if rotation:
        obj.rotation_euler = rotation
    return _apply(obj, material, pass_index)


def _curly_hair(
    prefix: str,
    head_loc: tuple[float, float, float],
    head_r: float,
    hair_m: bpy.types.Material,
    pass_index: int,
) -> None:
    hx, hy, hz = head_loc
    offsets = (
        (0.00, 0.00, head_r * 0.95),
        (0.12, 0.04, head_r * 0.70),
        (-0.12, 0.05, head_r * 0.68),
        (0.08, -0.10, head_r * 0.55),
        (-0.09, -0.08, head_r * 0.58),
        (0.00, 0.12, head_r * 0.45),
        (0.14, 0.00, head_r * 0.35),
    )
    for i, (dx, dy, dz) in enumerate(offsets):
        sphere(f"{prefix}_hair_{i}", head_r * 0.38, (hx + dx, hy + dy, hz + dz), hair_m, pass_index)


def _ponytail(
    prefix: str,
    head_loc: tuple[float, float, float],
    head_r: float,
    hair_m: bpy.types.Material,
    pass_index: int,
) -> None:
    hx, hy, hz = head_loc
    sphere(f"{prefix}_hair_cap", head_r * 0.95, (hx, hy + 0.02, hz + head_r * 0.15), hair_m, pass_index)
    cylinder(
        f"{prefix}_pony",
        head_r * 0.18,
        head_r * 1.6,
        (hx, hy + head_r * 0.85, hz - head_r * 0.15),
        hair_m,
        pass_index,
        rotation=(math.radians(55), 0.0, 0.0),
    )


def add_seated_dad(
    loc: tuple[float, float, float],
    material: bpy.types.Material,
    hair_m: bpy.types.Material,
    pass_index: int,
    scale: float = 1.0,
) -> None:
    """Hip at loc. Faces -Y (camera). Sweater + curly hair."""
    s = scale
    x, y, z = loc
    pelvis = (x, y, z)
    torso = (x, y + 0.02 * s, z + 0.28 * s)
    neck = (x, y + 0.01 * s, z + 0.48 * s)
    head = (x, y - 0.02 * s, z + 0.68 * s)
    cube(f"dad_pelvis", (0.22 * s, 0.16 * s, 0.10 * s), pelvis, material, pass_index)
    cube(f"dad_torso", (0.24 * s, 0.14 * s, 0.22 * s), torso, material, pass_index)
    cube(f"dad_sweater", (0.26 * s, 0.16 * s, 0.24 * s), (x, y + 0.01 * s, z + 0.26 * s), material, pass_index)
    cylinder("dad_neck", 0.05 * s, 0.10 * s, neck, material, pass_index)
    sphere("dad_head", 0.13 * s, head, material, pass_index, scale=(1.0, 0.92, 1.08))
    _curly_hair("dad", head, 0.13 * s, hair_m, pass_index)
    for side, sx in (("l", -1.0), ("r", 1.0)):
        cylinder(
            f"dad_arm_{side}",
            0.045 * s,
            0.32 * s,
            (x + sx * 0.28 * s, y - 0.02 * s, z + 0.28 * s),
            material,
            pass_index,
            rotation=(0.0, math.radians(sx * 12), 0.0),
        )
        cube(
            f"dad_hand_{side}",
            (0.04 * s, 0.05 * s, 0.03 * s),
            (x + sx * 0.30 * s, y - 0.04 * s, z + 0.10 * s),
            material,
            pass_index,
        )
        cube(
            f"dad_thigh_{side}",
            (0.07 * s, 0.18 * s, 0.06 * s),
            (x + sx * 0.09 * s, y - 0.16 * s, z + 0.02 * s),
            material,
            pass_index,
        )
        cylinder(
            f"dad_calf_{side}",
            0.045 * s,
            0.28 * s,
            (x + sx * 0.10 * s, y - 0.32 * s, z - 0.16 * s),
            material,
            pass_index,
        )


def add_seated_maya(
    loc: tuple[float, float, float],
    material: bpy.types.Material,
    hair_m: bpy.types.Material,
    pass_index: int,
    scale: float = 0.86,
) -> None:
    """Hip at loc. Faces -Y. Hoodie + ponytail."""
    s = scale
    x, y, z = loc
    head = (x, y - 0.02 * s, z + 0.62 * s)
    cube("maya_pelvis", (0.18 * s, 0.14 * s, 0.09 * s), (x, y, z), material, pass_index)
    cube("maya_hoodie", (0.22 * s, 0.16 * s, 0.22 * s), (x, y + 0.02 * s, z + 0.24 * s), material, pass_index)
    sphere("maya_hood", 0.12 * s, (x, y + 0.06 * s, z + 0.44 * s), material, pass_index)
    cylinder("maya_neck", 0.04 * s, 0.08 * s, (x, y, z + 0.44 * s), material, pass_index)
    sphere("maya_head", 0.11 * s, head, material, pass_index, scale=(1.0, 0.95, 1.05))
    _ponytail("maya", head, 0.11 * s, hair_m, pass_index)
    for side, sx in (("l", -1.0), ("r", 1.0)):
        cylinder(
            f"maya_arm_{side}",
            0.038 * s,
            0.28 * s,
            (x + sx * 0.24 * s, y, z + 0.24 * s),
            material,
            pass_index,
            rotation=(0.0, math.radians(sx * 10), 0.0),
        )
        cube(
            f"maya_thigh_{side}",
            (0.055 * s, 0.16 * s, 0.05 * s),
            (x + sx * 0.07 * s, y - 0.14 * s, z + 0.01 * s),
            material,
            pass_index,
        )
        cylinder(
            f"maya_pant_{side}",
            0.04 * s,
            0.26 * s,
            (x + sx * 0.08 * s, y - 0.28 * s, z - 0.14 * s),
            material,
            pass_index,
        )


def add_standing_dad(
    loc: tuple[float, float, float],
    material: bpy.types.Material,
    hair_m: bpy.types.Material,
    pass_index: int,
    scale: float = 1.0,
) -> None:
    """Feet near z=0. Faces -Y. No sofa."""
    s = scale
    x, y, z = loc
    cube("dad_pelvis", (0.20 * s, 0.12 * s, 0.10 * s), (x, y, z + 0.92 * s), material, pass_index)
    cube("dad_torso", (0.22 * s, 0.13 * s, 0.24 * s), (x, y, z + 1.18 * s), material, pass_index)
    cube("dad_sweater", (0.24 * s, 0.15 * s, 0.26 * s), (x, y, z + 1.16 * s), material, pass_index)
    cylinder("dad_neck", 0.05 * s, 0.10 * s, (x, y, z + 1.38 * s), material, pass_index)
    head = (x, y - 0.02 * s, z + 1.56 * s)
    sphere("dad_head", 0.13 * s, head, material, pass_index, scale=(1.0, 0.92, 1.08))
    _curly_hair("dad", head, 0.13 * s, hair_m, pass_index)
    for side, sx in (("l", -1.0), ("r", 1.0)):
        cylinder(
            f"dad_arm_{side}",
            0.045 * s,
            0.42 * s,
            (x + sx * 0.28 * s, y, z + 1.10 * s),
            material,
            pass_index,
        )
        cube(
            f"dad_hand_{side}",
            (0.04 * s, 0.05 * s, 0.03 * s),
            (x + sx * 0.28 * s, y, z + 0.86 * s),
            material,
            pass_index,
        )
        cylinder(
            f"dad_leg_{side}",
            0.05 * s,
            0.80 * s,
            (x + sx * 0.08 * s, y, z + 0.48 * s),
            material,
            pass_index,
        )
        cube(
            f"dad_foot_{side}",
            (0.05 * s, 0.10 * s, 0.03 * s),
            (x + sx * 0.08 * s, y - 0.04 * s, z + 0.04 * s),
            material,
            pass_index,
        )


def add_standing_maya(
    loc: tuple[float, float, float],
    material: bpy.types.Material,
    hair_m: bpy.types.Material,
    pass_index: int,
    scale: float = 0.86,
) -> None:
    s = scale
    x, y, z = loc
    cube("maya_pelvis", (0.16 * s, 0.11 * s, 0.08 * s), (x, y, z + 0.88 * s), material, pass_index)
    cube("maya_hoodie", (0.20 * s, 0.14 * s, 0.22 * s), (x, y, z + 1.10 * s), material, pass_index)
    sphere("maya_hood", 0.11 * s, (x, y + 0.05 * s, z + 1.28 * s), material, pass_index)
    cylinder("maya_neck", 0.04 * s, 0.08 * s, (x, y, z + 1.28 * s), material, pass_index)
    head = (x, y - 0.02 * s, z + 1.44 * s)
    sphere("maya_head", 0.11 * s, head, material, pass_index, scale=(1.0, 0.95, 1.05))
    _ponytail("maya", head, 0.11 * s, hair_m, pass_index)
    for side, sx in (("l", -1.0), ("r", 1.0)):
        cylinder(
            f"maya_arm_{side}",
            0.038 * s,
            0.36 * s,
            (x + sx * 0.24 * s, y, z + 1.04 * s),
            material,
            pass_index,
        )
        cylinder(
            f"maya_pant_{side}",
            0.042 * s,
            0.72 * s,
            (x + sx * 0.07 * s, y, z + 0.44 * s),
            material,
            pass_index,
        )
        cube(
            f"maya_foot_{side}",
            (0.045 * s, 0.09 * s, 0.03 * s),
            (x + sx * 0.07 * s, y - 0.03 * s, z + 0.04 * s),
            material,
            pass_index,
        )
