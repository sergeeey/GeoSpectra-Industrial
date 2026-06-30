"""PCD format loader for Real3D-AD dataset.

PCD (Point Cloud Data) is the standard format used by the Real3D-AD
benchmark. This loader reads ASCII and binary PCD files.
"""

import numpy as np


def load_pcd(filepath):
    """Load a PCD file and return (N, 3) point cloud.
    
    Supports ASCII and binary PCD formats.
    """
    with open(filepath, 'rb') as f:
        header = []
        while True:
            line = f.readline().decode('utf-8', errors='replace').strip()
            if line.startswith('DATA'):
                data_type = line.split()[1]
                break
            header.append(line)
    
    header_dict = {}
    for line in header:
        parts = line.split()
        if len(parts) >= 2:
            header_dict[parts[0]] = parts[1:]
    
    n_points = int(header_dict.get('POINTS', [0])[0])
    
    if data_type == 'ascii':
        points = np.loadtxt(filepath, skiprows=len(header) + 1)
    elif data_type == 'binary':
        with open(filepath, 'rb') as f:
            for _ in range(len(header) + 1):
                f.readline()
            points = np.fromfile(f, dtype=np.float32, count=n_points * 4)
            points = points.reshape(-1, 4)[:, :3]
    else:
        raise ValueError(f"Unsupported PCD data type: {data_type}")
    
    return np.array(points, dtype=np.float64)
