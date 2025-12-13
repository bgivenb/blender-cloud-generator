bl_info = {
    "name": "Cloud Generator",
    "author": "Given Borthwick",
    "version": (1, 8),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar > Cloud Generator",
    "description": "Generates realistic cumulus, cumulonimbus, and stratus clouds as mesh objects with volumetric effects.",
    "warning": "",
    "wiki_url": "",
    "category": "Object",
}

import bpy
import random
from bpy.props import EnumProperty, BoolProperty, FloatProperty, PointerProperty
from bpy.types import Operator, Panel, PropertyGroup


class CloudGeneratorProperties(PropertyGroup):
    cloud_type: EnumProperty(
        name="Cloud Type",
        description="Select the type of cloud to generate",
        items=[
            ('CUMULUS', "Cumulus", "Generate cumulus clouds"),
            ('CUMULONIMBUS', "Cumulonimbus", "Generate cumulonimbus clouds"),
            ('STRATUS', "Stratus", "Generate stratus clouds"),
        ],
        default='CUMULUS',
    )
    hide_mesh: BoolProperty(
        name="Hide Mesh",
        description="Hide the cloud mesh after generating the volumetric cloud",
        default=True,
    )
    add_sky: BoolProperty(
        name="Add Sky",
        description="Add a sky background to the scene",
        default=False,
    )
    
    target_detail: FloatProperty(
        name="Target Detail",
        description="Lower values result in fewer polygons (between 0 and 1)",
        default=0.1,
        min=0.01,
        max=1.0,
    )


class OBJECT_OT_GenerateCloud(Operator):
    bl_idname = "object.generate_cloud"
    bl_label = "Generate Cloud"
    bl_description = "Generates a realistic cumulus, cumulonimbus, or stratus cloud mesh with volumetric effects"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.cloud_generator_props

        # Ensure we're in Object Mode
        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode='OBJECT')

        # Create central sphere(s) based on cloud type
        central_spheres = []
        if props.cloud_type == 'CUMULUS':
            # Cumulus: Single central sphere
            bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(0, 0, 0))
            cloud_center = bpy.context.active_object
            cloud_center.name = "cumulus_cloud_center"
            cloud_center.scale = (4, 4, 4)
            central_spheres.append(cloud_center)
            bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(0, 0, 3))
            cloud_top = bpy.context.active_object
            cloud_top.name = "cumulus_cloud_top"
            cloud_top.scale = (4, 4, 4)
            cloud_top.location.x += random.uniform(-1.5, 1.5)
            cloud_top.location.y += random.uniform(-1.5, 1.5)
            central_spheres.append(cloud_top)
            
        elif props.cloud_type == 'STRATUS':
            # Stratus: Single central sphere, flattened
            bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(0, 0, 0))
            cloud_center = bpy.context.active_object
            cloud_center.name = "stratus_cloud_center"
            cloud_center.scale = (4, 3, 2)
            central_spheres.append(cloud_center)
        elif props.cloud_type == 'CUMULONIMBUS':
            # Cumulonimbus: Stacked central spheres
            for i in range(5):  # Initial sphere + 4 additional
                z_offset = i * 3  # 0, 3, 6, 9, 12
                if i == 1: 
                    scale = (5, 5, 5)
                elif 1 < i < 4:
                    scale = (3, 3, 3)
                else:
                    scale = (5, 5, 5)  # 5th sphere scaled larger

                bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(0, 0, z_offset))
                sphere = bpy.context.active_object
                sphere.name = f"cumulonimbus_cloud_center_{i+1}"
                sphere.scale = scale

                # Randomize x and y within (-1.5, 1.5), z remains as per stacking
                sphere.location.x += random.uniform(-1.5, 1.5)
                sphere.location.y += random.uniform(-1.5, 1.5)
                sphere.location.z = z_offset  # Ensure z is set correctly

                central_spheres.append(sphere)

        # Create cloud chunks
        cloud_chunks = []
        for i in range(1, 50):
            bpy.ops.mesh.primitive_uv_sphere_add(radius=1)
            chunk = bpy.context.active_object
            chunk.name = f"cloudchunk_{i:02d}"

            # Randomize location within specified ranges
            chunk.location.x = random.uniform(-3, 3)
            chunk.location.y = random.uniform(-6, 6)
            chunk.location.z = random.uniform(-1.5, 1.5)

            # Randomize scale between 0.5 and 1.5
            scale_factor = random.uniform(0.5, 2.5)
            chunk.scale = (scale_factor, scale_factor, scale_factor)

            cloud_chunks.append(chunk)

        # Join all central spheres into one object
        bpy.ops.object.select_all(action='DESELECT')
        for sphere in central_spheres:
            sphere.select_set(True)
        bpy.context.view_layer.objects.active = central_spheres[0]
        bpy.ops.object.join()
        joined_central = bpy.context.active_object
        if props.cloud_type == 'CUMULUS':
            joined_central.name = "cumulus_cloud"
        elif props.cloud_type == 'STRATUS':
            joined_central.name = "stratus_cloud"
        elif props.cloud_type == 'CUMULONIMBUS':
            joined_central.name = "cumulonimbus_cloud"

        # Join all cloud chunks into the central cloud
        bpy.ops.object.select_all(action='DESELECT')
        joined_central.select_set(True)
        for chunk in cloud_chunks:
            chunk.select_set(True)
        bpy.context.view_layer.objects.active = joined_central
        bpy.ops.object.join()
        joined_cloud = bpy.context.active_object

        # Apply Voxel Remesh
        bpy.ops.object.modifier_add(type='REMESH')
        remesh = joined_cloud.modifiers[-1]
        remesh.mode = 'VOXEL'
        remesh.voxel_size = 0.1
        bpy.ops.object.modifier_apply(modifier=remesh.name)

        # Apply Displace Modifier with Clouds Texture
        bpy.ops.object.modifier_add(type='DISPLACE')
        displace = joined_cloud.modifiers[-1]
        displace.name = "Displace_Clouds"

        # Create a new Clouds texture
        clouds_tex = bpy.data.textures.new(name="CloudNoise", type='CLOUDS')
        clouds_tex.noise_scale = random.uniform(0.8, 1.2)  # Set noise scale to 1 as specified

        # Assign the Clouds texture to the Displace modifier
        displace.texture = clouds_tex
        displace.strength = 0.5  # Adjust strength if needed

        bpy.ops.object.modifier_apply(modifier=displace.name)

        # Create, Scale, and Move a Cube
        bpy.ops.mesh.primitive_cube_add(location=(0, 0, 8))
        cube = bpy.context.active_object
        cube.name = "Environment_Cube"
        cube.scale = (8, 8, 7)  # Note: Z scale adjusted to 7 as per user's tweak

        # Apply Boolean Modifier
        bpy.ops.object.select_all(action='DESELECT')
        joined_cloud.select_set(True)
        bpy.context.view_layer.objects.active = joined_cloud

        # Add Boolean Modifier
        bpy.ops.object.modifier_add(type='BOOLEAN')
        boolean_mod = joined_cloud.modifiers[-1]
        boolean_mod.name = "Boolean_Intersect"
        boolean_mod.operation = 'INTERSECT'
        boolean_mod.object = cube

        try:
            # Addressing Blender 5.0+ boolean solver name change
            boolean_mod.solver = 'FLOAT'
        except TypeError:
            boolean_mod.solver = 'FAST'

        # Apply Boolean Modifier
        bpy.ops.object.modifier_apply(modifier=boolean_mod.name)

        # Delete the cube
        bpy.data.objects.remove(cube, do_unlink=True)

        # Remesh the Clouds Again
        bpy.ops.object.modifier_add(type='REMESH')
        remesh2 = joined_cloud.modifiers[-1]
        remesh2.mode = 'VOXEL'
        remesh2.voxel_size = 0.1
        bpy.ops.object.modifier_apply(modifier=remesh2.name)

        # Add Subdivision Surface Modifier
        bpy.ops.object.modifier_add(type='SUBSURF')
        subdiv = joined_cloud.modifiers[-1]
        subdiv.name = "Subdivision_Surface"
        subdiv.levels = 2
        subdiv.render_levels = 2
        subdiv.quality = 2
        subdiv.subdivision_type = 'CATMULL_CLARK'

        # Apply Subdivision Surface Modifier
        bpy.ops.object.modifier_apply(modifier=subdiv.name)

        # Apply Displace Modifier Again with strength 0.25
        bpy.ops.object.modifier_add(type='DISPLACE')
        displace2 = joined_cloud.modifiers[-1]
        displace2.name = "Displace_Clouds_Second"

        # Reuse the existing Clouds texture
        displace2.texture = clouds_tex
        displace2.strength = 0.25  # Set strength to 0.25 as specified

        bpy.ops.object.modifier_apply(modifier=displace2.name)
        
        # Apply Displace Modifier with Clouds Texture
        bpy.ops.object.modifier_add(type='DISPLACE')
        displace = joined_cloud.modifiers[-1]
        displace.name = "Displace_Clouds_Third"

        # Create a new Clouds texture
        clouds_tex2 = bpy.data.textures.new(name="CloudNoise2", type='CLOUDS')
        clouds_tex2.noise_scale = random.uniform(0.1, 0.13)  # Set noise scale to 1 as specified

        # Assign the Clouds texture to the Displace modifier
        displace.texture = clouds_tex2
        displace.strength = 0.05  # Adjust strength if needed

        # Decimate the Cloud Mesh using target_detail
        bpy.ops.object.modifier_add(type='DECIMATE')
        decimate = joined_cloud.modifiers[-1]
        decimate.name = "Decimate_Cloud"
        decimate.ratio = props.target_detail  # Correctly reference the property
        decimate.decimate_type = 'COLLAPSE'

        bpy.ops.object.modifier_apply(modifier=decimate.name)

        # Set Shading to Smooth
        bpy.ops.object.shade_smooth()

        # Add a Volume Object
        bpy.ops.object.add(type='VOLUME', location=(0, 0, 0))
        volume_obj = bpy.context.active_object
        volume_obj.name = "Cloud_Volume"

        # Add Mesh to Volume Modifier to the Volume Object
        mesh_to_volume = volume_obj.modifiers.new(name="MeshToVolume", type='MESH_TO_VOLUME')
        mesh_to_volume.object = joined_cloud  # Set the cloud mesh as the source
        mesh_to_volume.resolution_mode = 'VOXEL_AMOUNT'
        mesh_to_volume.voxel_amount = 150  # Set voxel amount to 150

        # Do Not Apply This Modifier

        # Add Volume Displace Modifier
        volume_displace = volume_obj.modifiers.new(name="VolumeDisplace", type='VOLUME_DISPLACE')
        volume_displace.strength = 2.5

        # Create a new Clouds texture for Volume Displace
        clouds_tex_volume = bpy.data.textures.new(name="CloudNoise_Volume", type='CLOUDS')
        clouds_tex_volume.noise_scale = 0.80  # Set size to 0.80
        clouds_tex_volume.noise_depth = 3     # Set depth to 3

        # Assign the texture to the Volume Displace modifier
        volume_displace.texture = clouds_tex_volume

        # Do Not Apply This Modifier

        # Set the cloud mesh as the child of the cloud volume
        joined_cloud.parent = volume_obj

        # Hide the Cloud Mesh based on the checkbox
        if props.hide_mesh:
            joined_cloud.hide_viewport = True
            joined_cloud.hide_render = True

        # *** New Step: Add Sky Background if Checked ***
        if props.add_sky:
            self.add_sky_background()

        self.report({'INFO'}, f"{props.cloud_type} cloud generated successfully with volumetric effects.")
        return {'FINISHED'}

    def add_sky_background(self):
        # Create or get the World
        if bpy.context.scene.world is None:
            bpy.context.scene.world = bpy.data.worlds.new(name="World")

        world = bpy.context.scene.world
        world.use_nodes = True
        nodes = world.node_tree.nodes
        links = world.node_tree.links

        # Check if Sky Texture node already exists to prevent duplication
        sky_node_exists = False
        for node in nodes:
            if node.type == 'TEX_SKY':
                sky_node_exists = True
                sky_tex_node = node
                break

        if not sky_node_exists:
            # Clear existing nodes
            nodes.clear()

            # Add Sky Texture node
            sky_tex_node = nodes.new(type='ShaderNodeTexSky')
            sky_tex_node.location = (-300, 0)

            # Add Background node
            background_node = nodes.new(type='ShaderNodeBackground')
            background_node.location = (-100, 0)

            # Add Output node
            output_node = nodes.new(type='ShaderNodeOutputWorld')
            output_node.location = (100, 0)

            # Link nodes
            links.new(sky_tex_node.outputs['Color'], background_node.inputs['Color'])
            links.new(background_node.outputs['Background'], output_node.inputs['Surface'])

        # Optionally, adjust Sky Texture parameters here
        # Example:
        # sky_tex_node.sky_type = 'HOSEK_WILKIE'
        # sky_tex_node.turbidity = 2.0
        # sky_tex_node.ground_albedo = 0.1


class OBJECT_OT_UnhideCloudMeshes(Operator):
    bl_idname = "object.unhide_cloud_meshes"
    bl_label = "Unhide Cloud Meshes"
    bl_description = "Unhide all hidden cloud meshes generated by the Cloud Generator"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # Iterate through all objects and unhide cloud meshes
        for obj in bpy.data.objects:
            if obj.name.startswith("cumulus_cloud") or obj.name.startswith("cumulonimbus_cloud") or obj.name.startswith("stratus_cloud"):
                obj.hide_viewport = False
                obj.hide_render = False
        self.report({'INFO'}, "All cloud meshes have been unhidden.")
        return {'FINISHED'}


class CLOUDGENERATOR_PT_MainPanel(Panel):
    bl_label = "Cloud Generator"
    bl_idname = "CLOUDGENERATOR_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Cloud Generator'

    def draw(self, context):
        layout = self.layout
        props = context.scene.cloud_generator_props

        layout.prop(props, "cloud_type")
        layout.prop(props, "hide_mesh")
        layout.prop(props, "add_sky")
        layout.prop(props, "target_detail")  # Add the Target Detail property to the UI

        if props.cloud_type in {'CUMULUS', 'CUMULONIMBUS', 'STRATUS'}:
            layout.operator("object.generate_cloud", icon='OUTLINER_OB_MESH')

        layout.separator()
        layout.operator("object.unhide_cloud_meshes", icon='HIDE_OFF')

        # Branding
        layout.separator()
        layout.label(text="Created by Given Borthwick", icon='INFO')


def register():
    bpy.utils.register_class(CloudGeneratorProperties)
    bpy.utils.register_class(OBJECT_OT_GenerateCloud)
    bpy.utils.register_class(OBJECT_OT_UnhideCloudMeshes)
    bpy.utils.register_class(CLOUDGENERATOR_PT_MainPanel)
    bpy.types.Scene.cloud_generator_props = PointerProperty(type=CloudGeneratorProperties)


def unregister():
    bpy.utils.unregister_class(CloudGeneratorProperties)
    bpy.utils.unregister_class(OBJECT_OT_GenerateCloud)
    bpy.utils.unregister_class(OBJECT_OT_UnhideCloudMeshes)
    bpy.utils.unregister_class(CLOUDGENERATOR_PT_MainPanel)
    del bpy.types.Scene.cloud_generator_props


if __name__ == "__main__":
    register()
