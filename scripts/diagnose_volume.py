"""Minimal native Mesh to Volume render, independent of Cloud Generator."""

import sys
import bpy

mode = sys.argv[sys.argv.index("--") + 1]
scene = bpy.context.scene
source = bpy.data.objects["Cube"]
data = bpy.data.volumes.new("Diagnostic volume")
volume = bpy.data.objects.new("Diagnostic volume", data)
scene.collection.objects.link(volume)
modifier = volume.modifiers.new("Mesh to Volume", "MESH_TO_VOLUME")
modifier.object = source
modifier.resolution_mode = "VOXEL_AMOUNT"
modifier.voxel_amount = 32
material = bpy.data.materials.new("Diagnostic density")
material.use_nodes = True
nodes = material.node_tree.nodes
nodes.clear()
output = nodes.new("ShaderNodeOutputMaterial")
shader = nodes.new("ShaderNodeVolumePrincipled")
shader.inputs["Density"].default_value = 0.5
material.node_tree.links.new(shader.outputs["Volume"], output.inputs["Volume"])
data.materials.append(material)
if mode in {"hidden", "parented", "render"}:
    source.hide_render = True
if mode in {"hidden", "parented", "viewport"}:
    source.hide_set(True)
if mode == "rays":
    for attribute in (
        "visible_camera",
        "visible_diffuse",
        "visible_glossy",
        "visible_transmission",
        "visible_volume_scatter",
        "visible_shadow",
    ):
        setattr(source, attribute, False)
if mode == "transparent":
    surface = bpy.data.materials.new("Invisible diagnostic source")
    surface.use_nodes = True
    surface.node_tree.nodes.clear()
    surface_output = surface.node_tree.nodes.new("ShaderNodeOutputMaterial")
    transparent = surface.node_tree.nodes.new("ShaderNodeBsdfTransparent")
    surface.node_tree.links.new(
        transparent.outputs["BSDF"], surface_output.inputs["Surface"]
    )
    source.data.materials.clear()
    source.data.materials.append(surface)
if mode == "parented":
    source.parent = volume
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 1
scene.cycles.use_denoising = False
scene.render.resolution_x = scene.render.resolution_y = 32
scene.render.resolution_percentage = 100
print(f"Native Mesh to Volume render: {mode}", flush=True)
bpy.ops.render.render()
