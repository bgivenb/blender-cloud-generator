"""Run host integration cases in independent factory-startup Blender processes."""

import ast
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
TEST = ROOT / "tests" / "blender_integration.py"


def main():
    tree = ast.parse(TEST.read_text(encoding="utf-8"))
    cases = [
        f"{node.name}.{method.name}"
        for node in tree.body
        if isinstance(node, ast.ClassDef)
        for method in node.body
        if isinstance(method, ast.FunctionDef) and method.name.startswith("test_")
    ]
    if not cases:
        raise RuntimeError("No Blender integration cases discovered")
    for case in cases:
        print(f"Running isolated host case: {case}", flush=True)
        subprocess.run(
            [
                "blender",
                "--background",
                "--factory-startup",
                "--python-exit-code",
                "1",
                "--python",
                str(TEST),
                "--",
                case,
            ],
            cwd=ROOT,
            check=True,
        )
    print(f"Passed {len(cases)} isolated Blender cases", flush=True)


if __name__ == "__main__":
    main()
