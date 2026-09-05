"""Deterministic planning helpers for the Blender Cloud Generator add-on."""

from __future__ import annotations

from dataclasses import dataclass
import random


CLOUD_TYPES = {"CUMULUS", "CUMULONIMBUS", "STRATUS"}


@dataclass(frozen=True)
class SphereSpec:
    location: tuple[float, float, float]
    scale: tuple[float, float, float]


def validate_settings(
    cloud_type: str, chunk_count: int, voxel_size: float, target_detail: float
) -> None:
    if cloud_type not in CLOUD_TYPES:
        raise ValueError(f"Unsupported cloud type: {cloud_type}")
    if not 8 <= chunk_count <= 200:
        raise ValueError("Chunk count must be between 8 and 200.")
    if not 0.02 <= voxel_size <= 1.0:
        raise ValueError("Voxel size must be between 0.02 and 1.0 scene units.")
    if not 0.01 <= target_detail <= 1.0:
        raise ValueError("Target detail must be between 0.01 and 1.0.")


def _anchors(cloud_type: str) -> list[SphereSpec]:
    if cloud_type == "CUMULUS":
        return [
            SphereSpec((0, 0, 0), (4, 4, 3)),
            SphereSpec((0, 0, 2.5), (3.2, 3.2, 3.2)),
        ]
    if cloud_type == "STRATUS":
        return [SphereSpec((0, 0, 0), (6, 4, 1.5))]
    return [
        SphereSpec((0, 0, 0), (4.5, 4.5, 3.5)),
        SphereSpec((0, 0, 3), (4, 4, 4)),
        SphereSpec((0, 0, 6), (3, 3, 3)),
        SphereSpec((0, 0, 9), (3.5, 3.5, 3.5)),
        SphereSpec((0, 0, 12), (5, 5, 3)),
    ]


def build_cloud_plan(cloud_type: str, chunk_count: int, seed: int) -> list[SphereSpec]:
    """Return repeatable sphere positions and scales for a cloud mesh."""

    validate_settings(cloud_type, chunk_count, 0.1, 0.1)
    rng = random.Random(seed)
    specs = list(_anchors(cloud_type))

    for _ in range(chunk_count):
        if cloud_type == "STRATUS":
            location = (rng.uniform(-5, 5), rng.uniform(-3, 3), rng.uniform(-0.8, 0.8))
            scale = (
                rng.uniform(0.7, 2.2),
                rng.uniform(0.7, 2.2),
                rng.uniform(0.4, 1.1),
            )
        elif cloud_type == "CUMULONIMBUS":
            z = rng.uniform(-1, 13)
            spread = 3.5 if z < 4 or z > 10 else 2.0
            location = (rng.uniform(-spread, spread), rng.uniform(-spread, spread), z)
            radius = rng.uniform(0.6, 2.3)
            scale = (radius, radius, radius * rng.uniform(0.8, 1.2))
        else:
            location = (rng.uniform(-4, 4), rng.uniform(-4, 4), rng.uniform(-1, 4.5))
            radius = rng.uniform(0.6, 2.2)
            scale = (radius, radius, radius * rng.uniform(0.8, 1.2))
        specs.append(SphereSpec(location, scale))

    return specs
