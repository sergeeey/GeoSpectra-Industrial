"""3D scan loaders: STL, PLY, OBJ, XYZ → point cloud (N, 3).

ADR-IND-003: Unified loader interface.
All loaders return (N, 3) numpy array of float64 points.
Auto-detects format from extension if not specified.
"""

import numpy as np
import trimesh


def load_pointcloud(path, n_points=5000, format=None):
    """Load 3D file and sample point cloud.
    
    Args:
        path: path to 3D file
        n_points: target number of points to sample
        format: optional format override ('stl', 'ply', 'obj', 'xyz')
    
    Returns:
        (N, 3) numpy array of points, or None if failed
    """
    try:
        if format == 'xyz' or str(path).endswith('.xyz'):
            pts = np.loadtxt(path)
            if pts.shape[1] > 3:
                pts = pts[:, :3]
            return pts
        
        mesh = trimesh.load(path, force='mesh')
        if hasattr(mesh, 'sample'):
            pts = mesh.sample(n_points)
        else:
            pts = np.array(mesh.vertices)
        return np.array(pts, dtype=np.float64)
    except Exception as e:
        print(f"Error loading {path}: {e}")
        return None


def mesh_info(path):
    """Get mesh info without loading full point cloud."""
    try:
        mesh = trimesh.load(path, force='mesh')
        return {
            "n_vertices": len(mesh.vertices),
            "n_faces": len(mesh.faces) if hasattr(mesh, 'faces') else 0,
            "bounds": mesh.bounds.tolist(),
            "is_watertight": mesh.is_watertight if hasattr(mesh, 'is_watertight') else None,
        }
    except Exception as e:
        return {"error": str(e)}
