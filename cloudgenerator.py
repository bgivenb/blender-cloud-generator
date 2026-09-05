bl_info = {
    "name": "Cloud Generator",
    "author": "Given Borthwick",
    "version": (2, 1, 0),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar > Cloud Generator",
    "description": "Build deterministic stylized cloud meshes with optional volume conversion",
    "category": "Object",
}

import bpy
from bpy.props import (
    BoolProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    PointerProperty,
)
from bpy.types import Operator, Panel, PropertyGroup

try:
    from .cloud_core import build_cloud_plan, validate_settings
except ImportError:  # Support direct execution from a source checkout.
    from cloud_core import build_cloud_plan, validate_settings


class CloudGeneratorProperties(PropertyGroup):
    cloud_type: EnumProperty(
        name="Cloud type",
        items=(
            ("CUMULUS", "Cumulus", "A compact, rounded cloud"),
            ("CUMULONIMBUS", "Cumulonimbus", "A vertically developed cloud"),
            ("STRATUS", "Stratus", "A wide, shallow cloud layer"),
        ),
        default="CUMULUS",
    )
    seed: IntProperty(name="Seed", default=7, min=0, max=2_147_483_647)
    chunk_count: IntProperty(name="Detail chunks", default=40, min=8, max=200)
    voxel_size: FloatProperty(name="Voxel size", default=0.18, min=0.02, max=1.0)
    target_detail: FloatProperty(name="Decimate ratio", default=0.35, min=0.01, max=1.0)
    create_volume: BoolProperty(name="Create volume", default=True)
    volume_resolution: IntProperty(
        name="Volume voxel amount", default=96, min=16, max=256
    )
    volume_density: FloatProperty(
        name="Volume density", default=0.5, min=0.01, max=10.0
    )
    at_cursor: BoolProperty(name="Place at 3D cursor", default=True)
    hide_mesh: BoolProperty(name="Hide source mesh", default=True)
    add_sky: BoolProperty(name="Add sky background", default=False)


def _activate(context, obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    context.view_layer.objects.active = obj


def _apply_modifier(context, obj, modifier):
    _activate(context, obj)
    bpy.ops.object.modifier_apply(modifier=modifier.name)


RAY_VISIBILITY = (
    "visible_camera",
    "visible_diffuse",
    "visible_glossy",
    "visible_transmission",
    "visible_volume_scatter",
    "visible_shadow",
)


def _hide_volume_source(cloud, created_materials):
    """Hide the surface without removing a modifier dependency from render evaluation."""
    cloud.hide_set(True)
    # Blender 4.0.2 can crash in Cycles when a Mesh to Volume source has hide_render set.
    cloud.hide_render = False
    for attribute in RAY_VISIBILITY:
        setattr(cloud, attribute, False)
    material = bpy.data.materials.new("Cloud Source Invisible Surface")
    created_materials.append(material)
    material["cloud_generator_invisible_source"] = True
    material.use_nodes = True
    nodes = material.node_tree.nodes
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    transparent = nodes.new("ShaderNodeBsdfTransparent")
    material.node_tree.links.new(transparent.outputs["BSDF"], output.inputs["Surface"])
    # Eevee also needs a transparent surface; the Cycles ray flags alone are insufficient.
    if hasattr(material, "surface_render_method"):
        material.surface_render_method = "DITHERED"
    elif hasattr(material, "blend_method"):
        material.blend_method = "HASHED"
    if hasattr(material, "shadow_method"):
        material.shadow_method = "NONE"
    cloud.data.materials.append(material)
    return material


def _add_sky(scene):
    previous = scene.world
    if (
        previous
        and previous.use_nodes
        and any(node.type == "TEX_SKY" for node in previous.node_tree.nodes)
    ):
        return
    world = (
        previous.copy() if previous else bpy.data.worlds.new("Cloud Generator World")
    )
    world.name = "Cloud Generator World"
    scene.world = world
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    if any(node.type == "TEX_SKY" for node in nodes):
        return
    background = next((node for node in nodes if node.type == "BACKGROUND"), None)
    output = next((node for node in nodes if node.type == "OUTPUT_WORLD"), None)
    if background is None:
        background = nodes.new("ShaderNodeBackground")
    if output is None:
        output = nodes.new("ShaderNodeOutputWorld")
    sky = nodes.new("ShaderNodeTexSky")
    links.new(sky.outputs["Color"], background.inputs["Color"])
    if not background.outputs["Background"].is_linked:
        links.new(background.outputs["Background"], output.inputs["Surface"])


class OBJECT_OT_GenerateCloud(Operator):
    bl_idname = "object.generate_cloud"
    bl_label = "Generate Cloud"
    bl_description = "Generate a repeatable cloud from the current seed and settings"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        props = context.scene.cloud_generator_props
        try:
            if context.mode != "OBJECT":
                raise ValueError("Switch to Object Mode before generating clouds.")
            validate_settings(
                props.cloud_type,
                props.chunk_count,
                props.voxel_size,
                props.target_detail,
            )
            plan = build_cloud_plan(props.cloud_type, props.chunk_count, props.seed)
            result = self._build(context, props, plan)
        except Exception as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}

        self.report({"INFO"}, f"Created {result.name} from seed {props.seed}")
        return {"FINISHED"}

    def _build(self, context, props, plan):
        original_selection = list(context.selected_objects)
        original_active = context.view_layer.objects.active
        original_world = context.scene.world
        cursor_location = context.scene.cursor.location.copy()
        collection = bpy.data.collections.new(f"CloudGenerator_{props.seed}")
        context.scene.collection.children.link(collection)
        pieces = []
        created_meshes = []
        created_volumes = []
        created_materials = []
        try:
            for index, spec in enumerate(plan):
                bpy.ops.mesh.primitive_ico_sphere_add(
                    subdivisions=2, radius=1, location=spec.location
                )
                piece = context.active_object
                created_meshes.append(piece.data)
                piece.name = f"cloud_piece_{index:03d}"
                piece.scale = spec.scale
                for owner in list(piece.users_collection):
                    owner.objects.unlink(piece)
                collection.objects.link(piece)
                pieces.append(piece)

            bpy.ops.object.select_all(action="DESELECT")
            for piece in pieces:
                piece.select_set(True)
            context.view_layer.objects.active = pieces[0]
            bpy.ops.object.join()
            cloud = context.active_object
            cloud.name = f"{props.cloud_type.lower()}_cloud_{props.seed}"
            cloud["cloud_generator"] = True
            cloud["cloud_seed"] = props.seed
            cloud["cloud_type"] = props.cloud_type
            cloud["cloud_chunks"] = props.chunk_count
            # Join inherits the first sphere's non-uniform scale; normalize before remeshing.
            bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

            remesh = cloud.modifiers.new("Cloud Voxel Remesh", "REMESH")
            remesh.mode = "VOXEL"
            remesh.voxel_size = props.voxel_size
            _apply_modifier(context, cloud, remesh)

            if props.target_detail < 1:
                decimate = cloud.modifiers.new("Cloud Decimate", "DECIMATE")
                decimate.ratio = props.target_detail
                _apply_modifier(context, cloud, decimate)

            for polygon in cloud.data.polygons:
                polygon.use_smooth = True

            if props.create_volume:
                volume_data = bpy.data.volumes.new(f"CloudVolume_{props.seed}")
                created_volumes.append(volume_data)
                volume = bpy.data.objects.new(f"cloud_volume_{props.seed}", volume_data)
                collection.objects.link(volume)
                volume["cloud_generator"] = True
                volume["cloud_seed"] = props.seed
                mesh_to_volume = volume.modifiers.new(
                    "Mesh to Volume", "MESH_TO_VOLUME"
                )
                mesh_to_volume.object = cloud
                mesh_to_volume.resolution_mode = "VOXEL_AMOUNT"
                mesh_to_volume.voxel_amount = props.volume_resolution
                mesh_to_volume.density = 1.0
                material = bpy.data.materials.new(f"Cloud Density {props.seed}")
                created_materials.append(material)
                material.use_nodes = True
                nodes = material.node_tree.nodes
                nodes.clear()
                output = nodes.new("ShaderNodeOutputMaterial")
                shader = nodes.new("ShaderNodeVolumePrincipled")
                shader.inputs["Density"].default_value = props.volume_density
                material.node_tree.links.new(
                    shader.outputs["Volume"], output.inputs["Volume"]
                )
                volume_data.materials.append(material)
                cloud.parent = volume
                if props.hide_mesh:
                    _hide_volume_source(cloud, created_materials)
                result = volume
            else:
                result = cloud

            if props.at_cursor:
                result.location += cursor_location

            if props.add_sky:
                _add_sky(context.scene)
            _activate(context, result)
            return result
        except Exception:
            for obj in list(collection.objects):
                bpy.data.objects.remove(obj, do_unlink=True)
            bpy.data.collections.remove(collection)
            if context.scene.world != original_world:
                generated_world = context.scene.world
                context.scene.world = original_world
                if generated_world and generated_world.users == 0:
                    bpy.data.worlds.remove(generated_world)
            bpy.ops.object.select_all(action="DESELECT")
            for obj in original_selection:
                obj.select_set(True)
            context.view_layer.objects.active = original_active
            raise
        finally:
            for pool, blocks in (
                (bpy.data.meshes, created_meshes),
                (bpy.data.volumes, created_volumes),
                (bpy.data.materials, created_materials),
            ):
                for block in blocks:
                    try:
                        if block.users == 0:
                            pool.remove(block)
                    except ReferenceError:
                        pass


class OBJECT_OT_UnhideCloudMeshes(Operator):
    bl_idname = "object.unhide_cloud_meshes"
    bl_label = "Unhide Generated Meshes"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        meshes = [
            obj
            for obj in context.view_layer.objects
            if obj.type == "MESH" and obj.get("cloud_generator")
        ]
        for obj in meshes:
            obj.hide_viewport = False
            obj.hide_render = False
            obj.hide_set(False)
            for attribute in RAY_VISIBILITY:
                setattr(obj, attribute, True)
            for index in reversed(range(len(obj.data.materials))):
                material = obj.data.materials[index]
                if material and material.get("cloud_generator_invisible_source"):
                    obj.data.materials.pop(index=index)
                    if material.users == 0:
                        bpy.data.materials.remove(material)
        self.report({"INFO"}, f"Unhid {len(meshes)} cloud mesh(es)")
        return {"FINISHED"}


class CLOUDGENERATOR_PT_MainPanel(Panel):
    bl_label = "Cloud Generator"
    bl_idname = "CLOUDGENERATOR_PT_main_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Cloud Generator"

    def draw(self, context):
        layout = self.layout
        props = context.scene.cloud_generator_props
        layout.prop(props, "cloud_type")
        layout.prop(props, "seed")
        layout.prop(props, "at_cursor")
        layout.prop(props, "chunk_count")
        layout.prop(props, "voxel_size")
        layout.prop(props, "target_detail")
        layout.prop(props, "create_volume")
        if props.create_volume:
            layout.prop(props, "volume_resolution")
            layout.prop(props, "volume_density")
            layout.prop(props, "hide_mesh")
        layout.prop(props, "add_sky")
        layout.operator("object.generate_cloud", icon="VOLUME_DATA")
        layout.operator("object.unhide_cloud_meshes", icon="HIDE_OFF")


CLASSES = (
    CloudGeneratorProperties,
    OBJECT_OT_GenerateCloud,
    OBJECT_OT_UnhideCloudMeshes,
    CLOUDGENERATOR_PT_MainPanel,
)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.cloud_generator_props = PointerProperty(
        type=CloudGeneratorProperties
    )


def unregister():
    del bpy.types.Scene.cloud_generator_props
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
