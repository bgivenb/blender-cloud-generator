"""Build a deterministic, installable Blender add-on archive."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
PACKAGE = "cloud_generator"
VERSION = "2.1.0"
SOURCES = {
    f"{PACKAGE}/LICENSE": ROOT / "LICENSE",
    f"{PACKAGE}/__init__.py": ROOT / "cloudgenerator.py",
    f"{PACKAGE}/cloud_core.py": ROOT / "cloud_core.py",
}


def main() -> None:
    DIST.mkdir(exist_ok=True)
    archive = DIST / f"cloud-generator-v{VERSION}.zip"
    with ZipFile(archive, "w") as bundle:
        for destination, source in sorted(SOURCES.items()):
            entry = ZipInfo(destination, date_time=(1980, 1, 1, 0, 0, 0))
            entry.compress_type = ZIP_DEFLATED
            entry.external_attr = 0o644 << 16
            bundle.writestr(entry, source.read_bytes(), compresslevel=9)

    digest = sha256(archive.read_bytes()).hexdigest()
    checksum = archive.with_suffix(".zip.sha256")
    checksum.write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    print(f"Built {archive.relative_to(ROOT)}")
    print(f"SHA-256 {digest}")


if __name__ == "__main__":
    main()
