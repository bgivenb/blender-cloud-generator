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
if mode in {"hidden", "parented"}:
    source.hide_render = True
    source.hide_set(True)
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
