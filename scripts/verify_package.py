"""Verify checksums and register the packaged add-on in Blender, not the checkout."""

from hashlib import sha256
import importlib
from pathlib import Path
import sys
import tempfile
from zipfile import ZipFile

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from package_addon import DIST, PACKAGE, VERSION, SOURCES

archives = list(DIST.glob(f"*-v{VERSION}.zip"))
if len(archives) != 1:
    raise RuntimeError("Build exactly one current-version add-on ZIP first.")
archive = archives[0]
expected = archive.with_suffix(".zip.sha256").read_text().split()[0]
assert sha256(archive.read_bytes()).hexdigest() == expected, "Checksum mismatch"

with tempfile.TemporaryDirectory(prefix="blender-package-") as directory:
    with ZipFile(archive) as bundle:
        assert set(bundle.namelist()) == set(SOURCES), "Unexpected package contents"
        bundle.extractall(directory)
    sys.path.insert(0, directory)
    addon = importlib.import_module(PACKAGE)
    assert Path(addon.__file__).is_relative_to(directory), (
        "Imported checkout instead of package"
    )
    assert addon.bl_info["version"] == tuple(map(int, VERSION.split(".")))
    addon.register()
    addon.unregister()
    sys.path.remove(directory)

print(f"Verified installation: {PACKAGE} {VERSION} on Blender {bpy.app.version_string}")
