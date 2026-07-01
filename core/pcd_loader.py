"""PCD format loader for Real3D-AD dataset.

Point Cloud Data format support for .pcd files.
"""

import numpy as np


def load_pcd_file(path):
    """Load a PCD file and return (N, 3) point cloud.
    
    Supports ascii and binary PCD formats.
    """
    with open(path, 'rb') as f:
        header = []
        while True:
            line = f.readline().decode('ascii').strip()
            header.append(line)
            if line.startswith('DATA'):
                break
        
        # Parse header
        data_format = 'ascii'
        fields = []
        sizes = []
        types = []
        counts = []
        width = 0
        height = 0
        points = 0
        
        for line in header:
            if line.startswith('FIELDS'):
                fields = line.split()[1:]
            elif line.startswith('SIZE'):
                sizes = [int(x) for x in line.split()[1:]]
            elif line.startswith('TYPE'):
                types = line.split()[1:]
            elif line.startswith('COUNT'):
                counts = [int(x) for x in line.split()[1:]]
            elif line.startswith('WIDTH'):
                width = int(line.split()[1])
            elif line.startswith('HEIGHT'):
                height = int(line.split()[1])
            elif line.startswith('POINTS'):
                points = int(line.split()[1])
            elif line.startswith('DATA'):
                data_format = line.split()[1]
        
        if data_format == 'ascii':
            data = []
            for line in f:
                vals = line.decode('ascii').strip().split()
                if vals:
                    data.append([float(x) for x in vals[:3]])
            return np.array(data)
        elif data_format == 'binary':
            # Simple binary read — may need format-specific handling
            dtype_map = {'F': 'f4', 'I': 'i4', 'U': 'u4'}
            dtypes = [dtype_map.get(t, 'f4') for t in types]
            point_dtype = np.dtype(list(zip(fields, dtypes)))
            data = np.fromfile(f, dtype=point_dtype, count=points)
            xyz = np.column_stack([data['x'], data['y'], data['z']])
            return xyz
        else:
            raise ValueError(f"Unsupported PCD data format: {data_format}")
