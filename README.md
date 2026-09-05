# Cloud Generator for Blender

[![Tests](https://github.com/bgivenb/blender-cloud-generator/actions/workflows/test.yml/badge.svg)](https://github.com/bgivenb/blender-cloud-generator/actions/workflows/test.yml)

A Blender add-on for generating stylized cumulus, cumulonimbus, and stratus clouds from repeatable procedural layouts. A seed and a small set of bounded controls produce a joined, remeshed cloud mesh with optional volume conversion and sky setup.

<a href="https://www.reddit.com/r/blender/comments/1gqi1mj/i_made_a_cloud_generator_plugin_free_download/"><img src="docs/images/original-reddit-demo.gif" alt="Original Cloud Generator workflow in Blender" width="720"></a>

*Excerpt from the original Blender walkthrough. [Watch the complete demo and discussion on r/blender](https://www.reddit.com/r/blender/comments/1gqi1mj/i_made_a_cloud_generator_plugin_free_download/).*

### Current deterministic mesh output

![A stylized cloud generated from seed 29](docs/images/cloud-example.png)

## Design

- **Repeatable:** the same cloud type, chunk count, and seed generate the same sphere plan.
- **Controllable:** chunk count, voxel size, decimation ratio, volume resolution, and volume density make the quality/performance trade-off explicit.
- **Scene-friendly:** place the cloud at the 3D cursor or world origin. Optional sky setup copies the scene's world instead of editing one shared by other scenes.
- **Non-destructive by default:** source objects are generated in a dedicated collection; optional volume conversion can hide rather than delete its source mesh.
- **Failure-aware:** incomplete generated collections and unused generated data are cleaned up; selection and the active object are restored if the operation fails.
- **Testable:** procedural planning is isolated in `cloud_core.py` and covered without requiring Blender.

## Install

1. Download the add-on ZIP and matching `.sha256` file from the [latest release](https://github.com/bgivenb/blender-cloud-generator/releases/latest).
2. Verify the archive against the published SHA-256 checksum.
3. In Blender 3.6 or newer, open **Edit → Preferences → Add-ons → Install** and select the downloaded ZIP.
4. Enable **Cloud Generator**.
5. Open the 3D Viewport sidebar (`N`) and choose **Cloud Generator**.

To build the same installable archive from a source checkout, run `python scripts/package_addon.py`; the ZIP and checksum are written to `dist/`.

## Use

In Object Mode, select a cloud type and seed, tune the detail controls, and click **Generate Cloud**. Reuse the seed for the same base layout. The cloud is placed at the 3D cursor by default; disable **Place at 3D cursor** to use the world origin.

**Create volume** adds a live Mesh to Volume modifier and a connected Principled Volume material. Set **Volume voxel amount** for resolution and **Volume density** for the material's density multiplier. **Hide source mesh** hides the generated mesh without disabling it in the viewport dependency graph; **Unhide Generated Meshes** affects only the current view layer. Use a volume-capable render engine and suitable lighting to inspect the volume.

Voxel remeshing now uses unit-scale geometry rather than inheriting the first sphere's non-uniform scale. This fixes inconsistent voxel dimensions but can change meshes generated with the same v2.0 settings. Seeded sphere layouts remain unchanged. Voxel values are in Blender scene units, not a conversion from the scene's displayed unit system.

Very small voxel sizes and high chunk counts can be expensive. Start with the defaults and reduce voxel size only when the silhouette needs more detail.

## Development

Run the dependency-free tests:

```bash
python -m unittest discover -s tests -v
```

Run host integration tests for cursor placement, unit scale, volume setup, shared worlds, and failure cleanup:

```bash
blender --background --factory-startup --python-exit-code 1 --python tests/blender_integration.py
```

Rebuild the checked-in example image:

```bash
blender --background --python scripts/render_example.py
```

Build and checksum the installable add-on archive with:

```bash
python scripts/package_addon.py
blender --background --factory-startup --python-exit-code 1 --python scripts/verify_package.py
```

Version 2.1 was tested locally with Blender 4.5.11 LTS. CI also tests Ubuntu 24.04's Blender package and prints its version. [Changes in 2.1](CHANGELOG.md).

## Scope

This is an independent hobby project and a compact exploration of deterministic procedural modeling around Blender's stateful API.

## License

[CC0 1.0 Universal](LICENSE)
