# Changelog

## 2.1.0

- Add 3D cursor placement and configurable volume resolution/density.
- Create a connected Principled Volume material for generated volumes.
- Normalize sphere-join scale before voxel remeshing; final geometry can differ from v2.0 at the same settings.
- Keep hidden source meshes available to viewport dependency evaluation.
- Copy worlds for optional sky setup, avoiding changes to other scenes sharing a world.
- Clean unused generated data and restore selection on failure.
- Add Blender integration tests and packaged-install verification to CI.

## 2.0.0

- Introduce deterministic sphere plans, bounded generation controls, cleanup, and packaging.
