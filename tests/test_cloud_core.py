import unittest

from cloud_core import build_cloud_plan, validate_settings


class CloudCoreTests(unittest.TestCase):
    def test_same_seed_produces_same_plan(self):
        self.assertEqual(build_cloud_plan("CUMULUS", 20, 42), build_cloud_plan("CUMULUS", 20, 42))

    def test_different_seeds_change_plan(self):
        self.assertNotEqual(build_cloud_plan("STRATUS", 20, 1), build_cloud_plan("STRATUS", 20, 2))

    def test_cloud_shapes_include_expected_anchors(self):
        self.assertEqual(len(build_cloud_plan("STRATUS", 8, 1)), 9)
        self.assertEqual(len(build_cloud_plan("CUMULUS", 8, 1)), 10)
        self.assertEqual(len(build_cloud_plan("CUMULONIMBUS", 8, 1)), 13)

    def test_all_scales_are_positive(self):
        for cloud_type in ("STRATUS", "CUMULUS", "CUMULONIMBUS"):
            for sphere in build_cloud_plan(cloud_type, 25, 99):
                self.assertTrue(all(component > 0 for component in sphere.scale))

    def test_invalid_settings_are_rejected(self):
        invalid = (
            ("UNKNOWN", 20, 0.1, 0.5),
            ("CUMULUS", 7, 0.1, 0.5),
            ("CUMULUS", 20, 0.001, 0.5),
            ("CUMULUS", 20, 0.1, 1.1),
        )
        for values in invalid:
            with self.assertRaises(ValueError):
                validate_settings(*values)


if __name__ == "__main__":
    unittest.main()
