"""Set up the parametric skeleton for the ThreeMan enclosure.

Creates, in the active document (or a new one if none is open):
  - Params        VarSet holding every dimension
  - Skeleton      Body with MasterSketch (PCB outline, notch, mounting holes)
                  and a SplitPlane datum at z = split_z
  - Base, Lid     empty Bodies, each with a SubShapeBinder to MasterSketch
                  and SplitPlane

Board data comes from ../ThreeMan_HW/ThreeMan_HW.kicad_pcb (Edge.Cuts and the
mounting-hole footprints), shifted so the board's bottom-left corner is the
origin and Y points up (KiCad is Y-down).

Run from FreeCAD via Macro > Execute, or: freecadcmd scripts/setup_skeleton.py
"""

import math

import FreeCAD as App
import Part
import Sketcher

V = App.Vector

PARAMS = [
    # name, value [mm], description
    ("pcb_x", 80.0, "PCB size along X"),
    ("pcb_y", 40.0, "PCB size along Y"),
    ("pcb_t", 1.6062, "PCB thickness"),
    ("corner_r", 3.5, "PCB corner radius"),
    ("hole_d", 3.2, "Mounting hole diameter"),
    ("hole_inset", 4.0, "Mounting hole centre distance from board edges"),
    ("notch_x", 22.0, "Bottom-edge notch: distance from left edge to notch start"),
    ("notch_w", 10.0, "Bottom-edge notch: opening width"),
    ("notch_r", 1.25, "Bottom-edge notch: fillet radius (depth = 2 * radius)"),
    ("wall", 2.0, "Enclosure wall thickness"),
    ("clearance", 0.5, "Gap between PCB and enclosure inner wall"),
    ("split_z", 8.0, "Z of the Base/Lid split plane (PLACEHOLDER, PCB bottom = 0)"),
]


def main():
    doc = App.ActiveDocument or App.newDocument("ThreeMan_Enclosure")
    if doc.getObject("Params"):
        raise RuntimeError("Params already exists in this document; aborting")

    params = make_varset(doc)
    skeleton = make_skeleton(doc)
    for name in ("Base", "Lid"):
        make_half(doc, name, skeleton)
    doc.recompute()
    return doc


def make_varset(doc):
    vs = doc.addObject("App::VarSet", "Params")
    for name, value, desc in PARAMS:
        vs.addProperty("App::PropertyLength", name, "Params", desc)
        setattr(vs, name, App.Units.Quantity(value, "mm"))
    return vs


def origin_feature(body, role):
    return next(f for f in body.Origin.OriginFeatures if f.Role == role)


def make_skeleton(doc):
    body = doc.addObject("PartDesign::Body", "Skeleton")
    sk = body.newObject("Sketcher::SketchObject", "MasterSketch")
    sk.AttachmentSupport = [(origin_feature(body, "XY_Plane"), "")]
    sk.MapMode = "FlatFace"
    build_master_sketch(sk)

    plane = body.newObject("PartDesign::Plane", "SplitPlane")
    plane.AttachmentSupport = [(origin_feature(body, "XY_Plane"), "")]
    plane.MapMode = "FlatFace"
    plane.setExpression("AttachmentOffset.Base.z", "Params.split_z")
    return body


def build_master_sketch(sk):
    # Initial geometry only needs to be close; the solver does the rest.
    W, H, r = 80.0, 40.0, 3.5
    nx, nw, nr = 22.0, 10.0, 1.25
    pi = math.pi

    def line(a, b):
        return sk.addGeometry(Part.LineSegment(V(*a, 0), V(*b, 0)), False)

    def arc(c, rad, a0, a1):
        # CCW arc from angle a0 to a1; point 1 = start (a0), point 2 = end (a1)
        return sk.addGeometry(
            Part.ArcOfCircle(Part.Circle(V(*c, 0), V(0, 0, 1), rad), a0, a1), False
        )

    # Outline, counter-clockwise from the bottom-left. Names: L = line, A = arc.
    L0 = line((r, 0), (nx, 0))
    A1 = arc((nx, nr), nr, -pi / 2, 0)                      # convex notch entry
    A2 = arc((nx + 2 * nr, nr), nr, pi / 2, pi)             # concave notch fillet
    L1 = line((nx + 2 * nr, 2 * nr), (nx + nw - 2 * nr, 2 * nr))  # notch bottom
    A3 = arc((nx + nw - 2 * nr, nr), nr, 0, pi / 2)         # concave notch fillet
    A4 = arc((nx + nw, nr), nr, pi, 3 * pi / 2)             # convex notch entry
    L2 = line((nx + nw, 0), (W - r, 0))
    A5 = arc((W - r, r), r, -pi / 2, 0)                     # bottom-right corner
    L3 = line((W, r), (W, H - r))
    A6 = arc((W - r, H - r), r, 0, pi / 2)                  # top-right corner
    L4 = line((W - r, H), (r, H))
    A7 = arc((r, H - r), r, pi / 2, pi)                     # top-left corner
    L5 = line((0, H - r), (0, r))
    A8 = arc((r, r), r, pi, 3 * pi / 2)                     # bottom-left corner

    # Mounting holes: BL, BR, TR, TL
    inset = 4.0
    hole_pos = [(inset, inset), (W - inset, inset), (W - inset, H - inset), (inset, H - inset)]
    HB = [sk.addGeometry(Part.Circle(V(x, y, 0), V(0, 0, 1), 1.6), False) for x, y in hole_pos]

    C = Sketcher.Constraint
    # Outline connectivity (tangent joins imply coincidence). Tuples: (g1, p1, g2, p2)
    joins = [
        (L0, 2, A1, 1), (A1, 2, A2, 2), (A2, 1, L1, 1), (L1, 2, A3, 2),
        (A3, 1, A4, 1), (A4, 2, L2, 1), (L2, 2, A5, 1), (A5, 2, L3, 1),
        (L3, 2, A6, 1), (A6, 2, L4, 1), (L4, 2, A7, 1), (A7, 2, L5, 1),
        (L5, 2, A8, 1), (A8, 2, L0, 1),
    ]
    for g1, p1, g2, p2 in joins:
        sk.addConstraint(C("Tangent", g1, p1, g2, p2))

    for g in (L0, L1, L2, L4):
        sk.addConstraint(C("Horizontal", g))
    for g in (L3, L5):
        sk.addConstraint(C("Vertical", g))

    # Anchor: bottom edge on the X axis, left edge on the Y axis
    sk.addConstraint(C("PointOnObject", L0, 1, -1))
    sk.addConstraint(C("PointOnObject", L5, 1, -2))
    sk.addConstraint(C("PointOnObject", L2, 1, -1))

    # Equal radii
    for g in (A5, A6, A7):
        sk.addConstraint(C("Equal", A8, g))
    for g in (A2, A3, A4):
        sk.addConstraint(C("Equal", A1, g))

    # Named dimensional constraints, each driven by Params.<name>
    driven = {}

    def dim(name, constraint, param):
        idx = sk.addConstraint(constraint)
        sk.renameConstraint(idx, name)
        driven[name] = param

    dim("pcb_x", C("DistanceX", L5, 1, L3, 1, W), "pcb_x")
    dim("pcb_y", C("DistanceY", L0, 1, L4, 1, H), "pcb_y")
    dim("corner_r", C("Radius", A8, r), "corner_r")
    dim("notch_x", C("DistanceX", L5, 1, A1, 1, nx), "notch_x")
    dim("notch_w", C("DistanceX", A1, 1, A4, 2, nw), "notch_w")
    dim("notch_r", C("Radius", A1, nr), "notch_r")
    dim("notch_d", C("DistanceY", L0, 1, L1, 1, 2 * nr), "notch_r * 2")

    # Holes
    bl, br, tr, tl = HB
    for g in (br, tr, tl):
        sk.addConstraint(C("Equal", bl, g))
    dim("hole_d", C("Diameter", bl, 3.2), "hole_d")
    dim("hole_inset_bl_x", C("DistanceX", L5, 1, bl, 3, inset), "hole_inset")
    dim("hole_inset_bl_y", C("DistanceY", L0, 1, bl, 3, inset), "hole_inset")
    dim("hole_inset_br_x", C("DistanceX", br, 3, L3, 1, inset), "hole_inset")
    dim("hole_inset_tl_y", C("DistanceY", tl, 3, L4, 1, inset), "hole_inset")
    sk.addConstraint(C("Horizontal", bl, 3, br, 3))
    sk.addConstraint(C("Vertical", br, 3, tr, 3))
    sk.addConstraint(C("Horizontal", tr, 3, tl, 3))
    sk.addConstraint(C("Vertical", bl, 3, tl, 3))

    for name, param in driven.items():
        sk.setExpression(f"Constraints.{name}", f"Params.{param}")


def make_half(doc, name, skeleton):
    body = doc.addObject("PartDesign::Body", name)
    sketch = doc.getObject("MasterSketch")
    plane = doc.getObject("SplitPlane")
    for label, src in (("MasterBinder", sketch), ("SplitBinder", plane)):
        binder = body.newObject("PartDesign::SubShapeBinder", label)
        binder.Support = [(src, "")]
    return body


if __name__ in ("__main__", "setup_skeleton"):
    main()
