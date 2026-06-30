"""Realistic industrial mesh suite — complex shapes closer to real parts.

Simulates actual industrial components:
- bracket: aerospace mounting bracket with ribs and holes
- gear: mechanical gear with teeth
- connector: cylindrical connector with pin holes
- housing: box-like enclosure with mounting features
- manifold: Y-shaped pipe junction
"""

import numpy as np
import trimesh


def create_bracket():
    """Aerospace mounting bracket with base, rib, and mounting holes."""
    base = trimesh.creation.box(extents=[4.0, 0.4, 2.5])
    rib = trimesh.creation.box(extents=[0.4, 1.5, 2.5])
    rib.apply_translation([0, 0.8, 0])
    
    hole1 = trimesh.creation.cylinder(radius=0.25, height=0.5)
    hole1.apply_translation([1.5, 0, 0.8])
    hole2 = trimesh.creation.cylinder(radius=0.25, height=0.5)
    hole2.apply_translation([-1.5, 0, 0.8])
    hole3 = trimesh.creation.cylinder(radius=0.2, height=0.5)
    hole3.apply_translation([1.5, 0, -0.8])
    
    bracket = trimesh.util.concatenate([base, rib])
    return bracket


def create_gear():
    """Mechanical gear with teeth."""
    from trimesh.creation import extrude_polygon
    import trimesh.path.polygons as polygons
    
    n_teeth = 12
    outer_r = 1.5
    inner_r = 1.2
    
    angles = np.linspace(0, 2*np.pi, n_teeth*2 + 1)[:-1]
    radii = np.where(np.arange(len(angles)) % 2 == 0, outer_r, inner_r)
    points = np.column_stack([radii * np.cos(angles), radii * np.sin(angles)])
    
    polygon = polygons.points_to_polygon(points)
    gear = extrude_polygon(polygon, height=0.5)
    
    hole = trimesh.creation.cylinder(radius=0.4, height=0.6)
    hole.apply_translation([0, 0, 0.25])
    
    gear = trimesh.util.concatenate([gear, hole])
    return gear


def create_connector():
    """Cylindrical connector with pin arrangement."""
    body = trimesh.creation.cylinder(radius=0.8, height=2.0)
    
    flange = trimesh.creation.cylinder(radius=1.2, height=0.3)
    flange.apply_translation([0, 0, 0.8])
    
    for angle in [0, np.pi/2, np.pi, 3*np.pi/2]:
        hole = trimesh.creation.cylinder(radius=0.1, height=0.4)
        hole.apply_translation([0.6*np.cos(angle), 0.6*np.sin(angle), 0.8])
        body = trimesh.util.concatenate([body, hole])
    
    body = trimesh.util.concatenate([body, flange])
    return body


def create_housing():
    """Box-like enclosure with mounting tabs."""
    box = trimesh.creation.box(extents=[3.0, 2.0, 1.5])
    
    for x in [-1.8, 1.8]:
        for y in [-1.3, 1.3]:
            tab = trimesh.creation.box(extents=[0.5, 0.5, 0.2])
            tab.apply_translation([x, y, -0.65])
            box = trimesh.util.concatenate([box, tab])
    
    recess = trimesh.creation.box(extents=[2.0, 1.2, 0.3])
    recess.apply_translation([0, 0, 0.6])
    box = trimesh.util.concatenate([box, recess])
    
    return box


def create_manifold():
    """Y-shaped pipe junction."""
    main_pipe = trimesh.creation.cylinder(radius=0.4, height=2.0)
    
    branch1 = trimesh.creation.cylinder(radius=0.3, height=1.5)
    branch1.apply_translation([0.8, 0.8, 0])
    
    branch2 = trimesh.creation.cylinder(radius=0.3, height=1.5)
    branch2.apply_translation([-0.8, 0.8, 0])
    
    junction = trimesh.util.concatenate([main_pipe, branch1, branch2])
    return junction


INDUSTRIAL_MESHES = {
    "bracket": create_bracket,
    "gear": create_gear,
    "connector": create_connector,
    "housing": create_housing,
    "manifold": create_manifold,
}


def get_mesh(name):
    if name not in INDUSTRIAL_MESHES:
        raise ValueError(f"Unknown mesh: {name}. Available: {list(INDUSTRIAL_MESHES.keys())}")
    return INDUSTRIAL_MESHES[name]()
