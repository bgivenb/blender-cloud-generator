"""Real Blender checks for volume setup, transforms, and failure cleanup."""

from pathlib import Path
import faulthandler
import sys
import tempfile
import unittest
from unittest.mock import patch

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cloudgenerator as addon

faulthandler.enable(all_threads=True)


class BlenderIntegrationTests(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.mesh.primitive_cube_add()
        self.original = bpy.context.active_object
        self.props = bpy.context.scene.cloud_generator_props
        self.props.chunk_count = 8
        self.props.voxel_size = 0.8
        self.props.target_detail = 1
        self.props.create_volume = False
        bpy.context.scene.cursor.location = (10, 20, 30)

    def test_cloud_uses_cursor_unit_scale_and_no_orphan_meshes(self):
        count = len(bpy.data.meshes)
        self.assertEqual(bpy.ops.object.generate_cloud(), {"FINISHED"})
        cloud = bpy.context.active_object
        self.assertEqual(tuple(cloud.location), (10, 20, 30))
        self.assertEqual(tuple(cloud.scale), (1, 1, 1))
        self.assertGreater(len(cloud.data.polygons), 0)
        self.assertEqual(len(bpy.data.meshes), count + 1)
        self.assertEqual(tuple(self.original.location), (0, 0, 0))

    def test_volume_has_shader_live_source_and_controls(self):
        self.props.create_volume = True
        self.props.volume_resolution = 32
        self.props.volume_density = 0.7
        self.assertEqual(bpy.ops.object.generate_cloud(), {"FINISHED"})
        volume = bpy.context.active_object
        self.assertEqual(volume.type, "VOLUME")
        self.assertEqual(tuple(volume.location), (10, 20, 30))
        modifier = volume.modifiers[0]
        self.assertEqual(modifier.voxel_amount, 32)
        source = modifier.object
        self.assertFalse(source.hide_viewport)
        self.assertTrue(source.hide_get())
        self.assertFalse(source.hide_render)
        self.assertFalse(source.visible_camera)
        self.assertTrue(
            source.data.materials[0].get("cloud_generator_invisible_source")
        )
        self.assertEqual(source.parent, volume)
        shader = next(
            node
            for node in volume.data.materials[0].node_tree.nodes
            if node.type == "PRINCIPLED_VOLUME"
        )
        self.assertAlmostEqual(shader.inputs["Density"].default_value, 0.7)
        bpy.ops.object.unhide_cloud_meshes()
        self.assertFalse(source.hide_get())
        self.assertTrue(source.visible_camera)
        self.assertEqual(len(source.data.materials), 0)

    def test_sky_does_not_edit_world_shared_with_another_scene(self):
        shared = bpy.data.worlds.new("Shared world")
        shared.use_nodes = True
        bpy.context.scene.world = shared
        other = bpy.data.scenes.new("Other scene")
        other.world = shared
        self.props.add_sky = True
        self.props.at_cursor = False
        bpy.ops.object.generate_cloud()
        self.assertEqual(other.world, shared)
        self.assertNotEqual(bpy.context.scene.world, shared)
        self.assertFalse(any(node.type == "TEX_SKY" for node in shared.node_tree.nodes))
        self.assertEqual(tuple(bpy.context.active_object.location), (0, 0, 0))

    def test_failure_restores_selection_and_removes_generated_data(self):
        counts = (
            len(bpy.data.objects),
            len(bpy.data.meshes),
            len(bpy.data.collections),
        )
        with patch.object(
            addon,
            "_apply_modifier",
            side_effect=RuntimeError("injected remesh failure"),
        ):
            with self.assertRaisesRegex(RuntimeError, "injected remesh failure"):
                bpy.ops.object.generate_cloud()
        self.assertEqual(
            counts,
            (len(bpy.data.objects), len(bpy.data.meshes), len(bpy.data.collections)),
        )
        self.assertEqual(bpy.context.selected_objects, [self.original])
        self.assertEqual(bpy.context.active_object, self.original)

    def test_late_failure_removes_volume_material_and_private_world(self):
        self.props.create_volume = self.props.add_sky = True
        pools = (
            bpy.data.objects,
            bpy.data.meshes,
            bpy.data.volumes,
            bpy.data.materials,
            bpy.data.worlds,
            bpy.data.collections,
        )
        counts = tuple(len(pool) for pool in pools)
        original_activate = addon._activate

        def fail_on_volume(context, obj):
            if obj.type == "VOLUME":
                raise RuntimeError("injected late failure")
            original_activate(context, obj)

        with patch.object(addon, "_activate", side_effect=fail_on_volume):
            with self.assertRaisesRegex(RuntimeError, "injected late failure"):
                bpy.ops.object.generate_cloud()
        self.assertEqual(counts, tuple(len(pool) for pool in pools))
        self.assertIsNone(bpy.context.scene.world)

    def test_hidden_source_produces_visible_volume_render(self):
        self._assert_volume_render("CYCLES")

    def test_hidden_source_produces_visible_eevee_volume_render(self):
        engine = (
            "BLENDER_EEVEE_NEXT" if bpy.app.version >= (4, 2, 0) else "BLENDER_EEVEE"
        )
        self._assert_volume_render(engine)

    def _assert_volume_render(self, engine):
        self.original.hide_render = True
        self.props.create_volume = True
        self.props.at_cursor = False
        self.props.volume_resolution = 32
        bpy.ops.object.generate_cloud()
        volume = bpy.context.active_object
        scene = bpy.context.scene
        # Use a complete render scene, including an explicit world, across host versions.
        scene.world = bpy.data.worlds.new("Volume render test world")
        scene.world.use_nodes = True
        bpy.ops.object.camera_add(location=(16, -20, 12))
        camera = bpy.context.active_object
        camera.rotation_euler = (
            (Vector((0, 0, 1)) - camera.location).to_track_quat("-Z", "Y").to_euler()
        )
        scene.camera = camera
        bpy.ops.object.light_add(type="AREA", location=(5, -10, 15))
        bpy.context.active_object.data.energy = 1500
        bpy.context.active_object.data.size = 10
        scene.render.engine = engine
        scene.cycles.device = "CPU"
        scene.cycles.samples = 2
        scene.cycles.use_denoising = False
        scene.render.resolution_x = scene.render.resolution_y = 32
        scene.render.resolution_percentage = 100
        scene.render.film_transparent = True
        scene.render.image_settings.color_mode = "RGBA"
        with tempfile.TemporaryDirectory() as directory:
            scene.render.filepath = str(Path(directory) / "volume.png")
            bpy.ops.render.render(write_still=True)
            image = bpy.data.images.load(scene.render.filepath)
            try:
                self.assertGreater(
                    max(image.pixels[:][3::4]),
                    0.01,
                    "Hidden source produced an empty volume",
                )
            finally:
                bpy.data.images.remove(image)
            volume.hide_render = True
            scene.render.filepath = str(Path(directory) / "source-only.png")
            bpy.ops.render.render(write_still=True)
            image = bpy.data.images.load(scene.render.filepath)
            try:
                self.assertLessEqual(
                    max(image.pixels[:][3::4]),
                    0.01,
                    "Hidden source surface leaked into the render",
                )
            finally:
                bpy.data.images.remove(image)


addon.register()
try:
    names = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    suite = (
        unittest.defaultTestLoader.loadTestsFromNames(
            names, module=sys.modules[__name__]
        )
        if names
        else unittest.defaultTestLoader.loadTestsFromTestCase(BlenderIntegrationTests)
    )
    result = unittest.TextTestRunner(verbosity=2).run(suite)
finally:
    addon.unregister()
if not result.wasSuccessful():
    raise RuntimeError("Blender integration tests failed")
