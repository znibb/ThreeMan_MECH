"""Export each enclosure half as an STL in print orientation.

Writes ThreeMan-Base.stl and ThreeMan-Lid.stl. The parametric Bodies are not
modified: each shape is copied, flipped if needed, and dropped onto Z = 0.

Run headless:   freecadcmd scripts/export_stl.py
or from the GUI: Macro > Execute (uses the active document).

Environment overrides: THREEMAN_OUT_DIR (output folder), THREEMAN_FCSTD (file),
THREEMAN_VERSION (e.g. v1.0.0, gives ThreeMan_v1.0.0_Base.stl instead).
"""

import os

import FreeCAD as App
import Mesh
import MeshPart

V = App.Vector

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
ROOT = os.path.dirname(HERE)
FCSTD = os.environ.get("THREEMAN_FCSTD", os.path.join(ROOT, "ThreeMan.FCStd"))
OUT_DIR = os.environ.get("THREEMAN_OUT_DIR", ROOT)
VERSION = os.environ.get("THREEMAN_VERSION", "")

# Body name -> rotate 180 deg about X before printing (closed face down)
BODIES = {"Base": False, "Lid": True}

LINEAR_DEFLECTION = 0.05  # mm, max distance between mesh and true surface
ANGULAR_DEFLECTION = 0.2  # rad


def main():
    doc = App.ActiveDocument or App.openDocument(FCSTD)
    doc.recompute()
    os.makedirs(OUT_DIR, exist_ok=True)

    for name, flip in BODIES.items():
        body = doc.getObject(name)
        if body is None:
            raise RuntimeError(f"Body '{name}' not found in {doc.Name}")
        shape = body.Shape.copy()
        if not shape.isValid():
            raise RuntimeError(f"{name}: shape is invalid, run Part > Check geometry")

        if flip:
            shape.rotate(V(0, 0, 0), V(1, 0, 0), 180)
        bb = shape.BoundBox
        shape.translate(V(-bb.XMin, -bb.YMin, -bb.ZMin))  # corner to origin, bottom on Z=0

        mesh = MeshPart.meshFromShape(
            Shape=shape,
            LinearDeflection=LINEAR_DEFLECTION,
            AngularDeflection=ANGULAR_DEFLECTION,
            Relative=False,
        )
        stem = f"ThreeMan_{VERSION}_{name}" if VERSION else f"ThreeMan-{name}"
        path = os.path.join(OUT_DIR, f"{stem}.stl")
        mesh.write(path)

        bb = mesh.BoundBox
        print(
            f"{name}: {path}\n"
            f"  {mesh.CountFacets} facets, "
            f"{bb.XLength:.2f} x {bb.YLength:.2f} x {bb.ZLength:.2f} mm, "
            f"solid={mesh.isSolid()}, volume={mesh.Volume:.0f} mm3"
        )


if __name__ in ("__main__", "export_stl"):
    main()
