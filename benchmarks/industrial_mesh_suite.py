"""Realistic industrial mesh suite."""

import numpy as np
import trimesh


def create_bracket():
    """Aerospace mounting bracket."""
    base = trimesh.creation.box(extents=[4.0, 0.4, 2.5])
    rib = trimesh.creation.box(extents=[0.4, 1.5, 2.5])
    rib.apply_translation([0, 0.8, 0])
    bracket = trimesh.util.concatenate([base, rib])
    return bracket


def create_gear():
    """Mechanical gear."""
    n_teeth = 12
    outer_r = 1.5
    inner_r = 1.2
    angles = np.linspace(0, 2*np.pi, n_teeth*2 + 1)[:-1]
    radii = np.where(np.arange(len(angles)) % 2 == 0, outer_r, inner_r)
    points = np.column_stack([radii * np.cos(angles), radii * np.sin(angles)])
    import trimesh.path.polygons as polygons
    from trimesh.creation import extrude_polygon
    polygon = polygons.points_to_polygon(points)
    gear = extrude_polygon(polygon, height=0.5)
    return gear


def create_connector():
    """Cylindrical connector."""
    body = trimesh.creation.cylinder(radius=0.8, height=2.0)
    flange = trimesh.creation.cylinder(radius=1.2, height=0.3)
    flange.apply_translation([0, 0, 0.8])
    return trimesh.util.concatenate([body, flange])


def create_housing():
    """Box-like enclosure."""
    box = trimesh.creation.box(extents=[3.0, 2.0, 1.5])
    return box


def create_manifold():
    """Y-shaped pipe junction."""
    main_pipe = trimesh.creation.cylinder(radius=0.4, height=2.0)
    branch1 = trimesh.creation.cylinder(radius=0.3, height=1.5)
    branch1.apply_translation([0.8, 0.8, 0])
    branch2 = trimesh.creation.cylinder(radius=0.3, height=1.5)
    branch2.apply_translation([-0.8, 0.8, 0])
    return trimesh.util.concatenate([main_pipe, branch1, branch2])


INDUSTRIAL_MESHES = {
    "bracket": create_bracket,
    "gear": create_gear,
    "connector": create_connector,
    "housing": create_housing,
    "manifold": create_manifold,
}
