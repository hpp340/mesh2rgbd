from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from typing import Tuple

import numpy as np
import os

from plyfile import PlyData
from skimage import io
from time import time

from .cython import mesh_core_cython


## TODO
## TODO: c++ version
def read_obj(obj_name):
    ''' read mesh
    '''
    return 0


# ------------------------- write
def write_asc(path, vertices):
    '''
    Args:
        vertices: shape = (nver, 3)
    '''
    if path.split('.')[-1] == 'asc':
        np.savetxt(path, vertices)
    else:
        np.savetxt(path + '.asc', vertices)


def write_obj_with_colors(obj_name, vertices, triangles, colors):
    ''' Save 3D face model with texture represented by colors.
    Args:
        obj_name: str
        vertices: shape = (nver, 3)
        triangles: shape = (ntri, 3)
        colors: shape = (nver, 3)
    '''
    triangles = triangles.copy()
    triangles += 1  # meshlab start with 1

    if obj_name.split('.')[-1] != 'obj':
        obj_name = obj_name + '.obj'

    # write obj
    with open(obj_name, 'w') as f:

        # write vertices & colors
        for i in range(vertices.shape[0]):
            # s = 'v {} {} {} \n'.format(vertices[0,i], vertices[1,i], vertices[2,i])
            s = 'v {} {} {} {} {} {}\n'.format(vertices[i, 0], vertices[i, 1], vertices[i, 2], colors[i, 0],
                                               colors[i, 1], colors[i, 2])
            f.write(s)

        # write f: ver ind/ uv ind
        [k, ntri] = triangles.shape
        for i in range(triangles.shape[0]):
            # s = 'f {} {} {}\n'.format(triangles[i, 0], triangles[i, 1], triangles[i, 2])
            s = 'f {} {} {}\n'.format(triangles[i, 2], triangles[i, 1], triangles[i, 0])
            f.write(s)


## TODO: c++ version
def write_obj_with_texture(obj_name, vertices, triangles, texture, uv_coords):
    ''' Save 3D face model with texture represented by texture map.
    Ref: https://github.com/patrikhuber/eos/blob/bd00155ebae4b1a13b08bf5a991694d682abbada/include/eos/core/Mesh.hpp
    Args:
        obj_name: str
        vertices: shape = (nver, 3)
        triangles: shape = (ntri, 3)
        texture: shape = (256,256,3)
        uv_coords: shape = (nver, 3) max value<=1
    '''
    if obj_name.split('.')[-1] != 'obj':
        obj_name = obj_name + '.obj'
    mtl_name = obj_name.replace('.obj', '.mtl')
    texture_name = obj_name.replace('.obj', '_texture.png')

    triangles = triangles.copy()
    triangles += 1  # mesh lab start with 1

    # write obj
    with open(obj_name, 'w') as f:
        # first line: write mtlib(material library)
        s = "mtllib {}\n".format(os.path.abspath(mtl_name))
        f.write(s)

        # write vertices
        for i in range(vertices.shape[0]):
            s = 'v {} {} {}\n'.format(vertices[i, 0], vertices[i, 1], vertices[i, 2])
            f.write(s)

        # write uv coords
        for i in range(uv_coords.shape[0]):
            s = 'vt {} {}\n'.format(uv_coords[i, 0], 1 - uv_coords[i, 1])
            f.write(s)

        f.write("usemtl FaceTexture\n")

        # write f: ver ind/ uv ind
        for i in range(triangles.shape[0]):
            s = 'f {}/{} {}/{} {}/{}\n'.format(triangles[i, 2], triangles[i, 2], triangles[i, 1], triangles[i, 1],
                                               triangles[i, 0], triangles[i, 0])
            f.write(s)

    # write mtl
    with open(mtl_name, 'w') as f:
        f.write("newmtl FaceTexture\n")
        s = 'map_Kd {}\n'.format(os.path.abspath(texture_name))  # map to image
        f.write(s)

    # write texture as png
    imsave(texture_name, texture)


# c++ version
def write_obj_with_colors_texture(obj_name, vertices, triangles, colors, texture, uv_coords):
    ''' Save 3D face model with texture. 
    Ref: https://github.com/patrikhuber/eos/blob/bd00155ebae4b1a13b08bf5a991694d682abbada/include/eos/core/Mesh.hpp
    Args:
        obj_name: str
        vertices: shape = (nver, 3)
        triangles: shape = (ntri, 3)
        colors: shape = (nver, 3)
        texture: shape = (256,256,3)
        uv_coords: shape = (nver, 3) max value<=1
    '''
    if obj_name.split('.')[-1] != 'obj':
        obj_name = obj_name + '.obj'
    mtl_name = obj_name.replace('.obj', '.mtl')
    texture_name = obj_name.replace('.obj', '_texture.png')

    triangles = triangles.copy()
    triangles += 1  # mesh lab start with 1

    # write obj
    vertices, colors, uv_coords = vertices.astype(np.float32).copy(), colors.astype(
        np.float32).copy(), uv_coords.astype(np.float32).copy()
    mesh_core_cython.write_obj_with_colors_texture_core(str.encode(obj_name), str.encode(os.path.abspath(mtl_name)),
                                                        vertices, triangles, colors, uv_coords, vertices.shape[0],
                                                        triangles.shape[0], uv_coords.shape[0])

    # write mtl
    with open(mtl_name, 'w') as f:
        f.write("newmtl FaceTexture\n")
        s = 'map_Kd {}\n'.format(os.path.abspath(texture_name))  # map to image
        f.write(s)

    # write texture as png
    io.imsave(texture_name, texture)


def load_ply(path: str) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """ Load vertices and triangles from .ply file
    Args:
        path: path to file
    Returns:
        ply_vertices: [nver, 3]
        ply_triangles: [ntri, 3]
        ply_colors: [nver, 3]
    """
    plydata = PlyData.read(path)
    tri_data = plydata['face'].data['vertex_indices']
    ply_triangles = np.vstack(tri_data)
    ply_vertices = np.array([plydata['vertex']['x'], plydata['vertex']['y'], plydata['vertex']['z']]).T

    ply_colors = np.array([])
    try:
        ply_colors = np.array([plydata['vertex']['red'], plydata['vertex']['green'], plydata['vertex']['blue']]).T
    except:
        print("Warning: .ply does not contain color information in expected location.")
        pass

    return ply_vertices, ply_triangles, ply_colors
