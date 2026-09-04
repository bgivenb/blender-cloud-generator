bl_info = {
    "name": "Cloud Generator",
    "author": "Given Borthwick",
    "version": (2, 0, 0),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar > Cloud Generator",
    "description": "Build deterministic stylized cloud meshes with optional volume conversion",
    "category": "Object",
}

import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty, PointerProperty
from bpy.types import Operator, Panel, PropertyGroup

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
    hide_mesh: BoolProperty(name="Hide source mesh", default=True)
    add_sky: BoolProperty(name="Add sky background", default=False)


def _activate(context, obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    context.view_layer.objects.active = obj


def _apply_modifier(context, obj, modifier):
    _activate(context, obj)
    bpy.ops.object.modifier_apply(modifier=modifier.name)


def _add_sky(scene):
    if scene.world is None:
        scene.world = bpy.data.worlds.new("Cloud Generator World")
    world = scene.world
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
        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode="OBJECT")

        collection = bpy.data.collections.new(f"CloudGenerator_{props.seed}")
        context.scene.collection.children.link(collection)
        pieces = []
        try:
            for index, spec in enumerate(plan):
                bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1, location=spec.location)
                piece = context.active_object
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
                volume = bpy.data.objects.new(f"cloud_volume_{props.seed}", volume_data)
                collection.objects.link(volume)
                volume["cloud_generator"] = True
                mesh_to_volume = volume.modifiers.new("Mesh to Volume", "MESH_TO_VOLUME")
                mesh_to_volume.object = cloud
                mesh_to_volume.resolution_mode = "VOXEL_AMOUNT"
                mesh_to_volume.voxel_amount = 150
                cloud.parent = volume
                if props.hide_mesh:
                    cloud.hide_viewport = True
                    cloud.hide_render = True
                result = volume
            else:
                result = cloud

            if props.add_sky:
                _add_sky(context.scene)
            _activate(context, result)
            return result
        except Exception:
            for obj in list(collection.objects):
                bpy.data.objects.remove(obj, do_unlink=True)
            bpy.data.collections.remove(collection)
            raise


class OBJECT_OT_UnhideCloudMeshes(Operator):
    bl_idname = "object.unhide_cloud_meshes"
    bl_label = "Unhide Generated Meshes"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        meshes = [obj for obj in bpy.data.objects if obj.type == "MESH" and obj.get("cloud_generator")]
        for obj in meshes:
            obj.hide_viewport = False
            obj.hide_render = False
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
        layout.prop(props, "chunk_count")
        layout.prop(props, "voxel_size")
        layout.prop(props, "target_detail")
        layout.prop(props, "create_volume")
        if props.create_volume:
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
    bpy.types.Scene.cloud_generator_props = PointerProperty(type=CloudGeneratorProperties)


def unregister():
    del bpy.types.Scene.cloud_generator_props
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
