"""Render the README example with Blender in background mode."""

from __future__ import annotations

import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "images" / "cloud-example.png"


def look_at(obj: bpy.types.Object, target: tuple[float, float, float]) -> None:
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def material(name: str, color: tuple[float, float, float, float], roughness: float = 0.6):
    result = bpy.data.materials.new(name)
    result.diffuse_color = color
    result.use_nodes = True
    shader = result.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = color
    shader.inputs["Roughness"].default_value = roughness
    return result


def main() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sys.path.insert(0, str(ROOT))
    import cloudgenerator as addon

    addon.register()
    props = bpy.context.scene.cloud_generator_props
    props.cloud_type = "CUMULUS"
    props.seed = 29
    props.chunk_count = 46
    props.voxel_size = 0.15
    props.target_detail = 0.55
    props.create_volume = False
    props.add_sky = False

    result = bpy.ops.object.generate_cloud()
    if "FINISHED" not in result:
        raise RuntimeError(f"Cloud generation failed: {result}")
    cloud = bpy.context.active_object
    cloud.data.materials.append(material("Cloud", (0.93, 0.97, 1.0, 1.0), 0.9))

    bpy.ops.mesh.primitive_plane_add(size=80, location=(0, 0, -3.35))
    ground = bpy.context.active_object
    ground.name = "Example Ground"
    ground.data.materials.append(material("Ground", (0.055, 0.09, 0.14, 1.0), 0.72))

    bpy.ops.object.light_add(type="AREA", location=(-7, -9, 12))
    key = bpy.context.active_object
    key.name = "Key Light"
    key.data.energy = 1_500
    key.data.shape = "DISK"
    key.data.size = 8
    look_at(key, (0, 0, 1.5))

    bpy.ops.object.light_add(type="AREA", location=(8, 2, 7))
    fill = bpy.context.active_object
    fill.name = "Fill Light"
    fill.data.energy = 900
    fill.data.color = (0.40, 0.62, 1.0)
    fill.data.size = 7
    look_at(fill, (0, 0, 1.0))

    bpy.ops.object.light_add(type="AREA", location=(0, 6, 9))
    rim = bpy.context.active_object
    rim.name = "Rim Light"
    rim.data.energy = 1_100
    rim.data.color = (1.0, 0.58, 0.25)
    rim.data.size = 5
    look_at(rim, (0, 0, 2.0))

    bpy.ops.object.camera_add(location=(18.0, -32.0, 13.0))
    camera = bpy.context.active_object
    camera.data.lens = 62
    look_at(camera, (0, 0, 0.8))
    bpy.context.scene.camera = camera

    world = bpy.data.worlds.new("Example World")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.012, 0.025, 0.06, 1.0)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.22
    bpy.context.scene.world = world

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = 960
    scene.render.resolution_y = 540
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    scene.render.filepath = str(OUTPUT)
    scene.render.image_settings.color_depth = "8"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.render.resolution_percentage = 100
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.render.render(write_still=True)
    print(f"Rendered {OUTPUT}")


if __name__ == "__main__":
    main()
