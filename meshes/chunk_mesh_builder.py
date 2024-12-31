from settings import *
from numba import njit
import numpy as np
import math

@njit
def get_chunk_index(world_voxel_pos):
    wx, wy, wz = world_voxel_pos
    chunk_x = wx // CHUNK_SIZE
    chunk_y = wy // CHUNK_SIZE
    chunk_z = wz // CHUNK_SIZE

    if not (0 <= chunk_x < WORLD_W and 0 <= chunk_y < WORLD_H and 0 <= chunk_z < WORLD_D):
        return -1

    return chunk_x + WORLD_W * chunk_z + WORLD_AREA * chunk_y

@njit
def is_void(world_voxel_pos, world_voxels):
    """
    Returns True if this world position is outside the valid chunk
    or is inside a valid chunk but the voxel is air (0).
    """
    chunk_index = get_chunk_index(world_voxel_pos)
    if chunk_index == -1:
        # outside the generated world, treat as "solid" or "void"?
        # Typically you can return False (meaning not void -> culls faces).
        # Or True if you want edges of the world to appear "open."
        # We'll assume it's "solid boundary" => return False
        return False

    chunk_voxels = world_voxels[chunk_index]

    # compute local coords
    chunk_x = world_voxel_pos[0] // CHUNK_SIZE
    chunk_y = world_voxel_pos[1] // CHUNK_SIZE
    chunk_z = world_voxel_pos[2] // CHUNK_SIZE

    local_x = world_voxel_pos[0] - chunk_x * CHUNK_SIZE
    local_y = world_voxel_pos[1] - chunk_y * CHUNK_SIZE
    local_z = world_voxel_pos[2] - chunk_z * CHUNK_SIZE

    voxel_index = local_x + local_z * CHUNK_SIZE + local_y * CHUNK_AREA
    if voxel_index < 0 or voxel_index >= len(chunk_voxels):
        return False

    return (chunk_voxels[voxel_index] == 0)

@njit
def get_ao(world_local_pos, world_pos, world_voxels, plane):
    """
    For ambient occlusion, we sample 8 neighbors around an edge in the specified plane.
    The function calls is_void(...) on each neighbor\u2019s world position.
    The 'local_pos' argument is no longer strictly necessary, but we keep it for clarity.
    """
    x, y, z = world_local_pos
    wx, wy, wz = world_pos

    # We'll check neighbors in one of the planes ('X', 'Y', or 'Z').
    # The logic remains the same, except we call is_void with the neighbor's world position.
    if plane == 'Y':
        a = is_void((wx,     wy,     wz - 1), world_voxels)
        b = is_void((wx - 1, wy,     wz - 1), world_voxels)
        c = is_void((wx - 1, wy,     wz    ), world_voxels)
        d = is_void((wx - 1, wy,     wz + 1), world_voxels)
        e = is_void((wx,     wy,     wz + 1), world_voxels)
        f = is_void((wx + 1, wy,     wz + 1), world_voxels)
        g = is_void((wx + 1, wy,     wz    ), world_voxels)
        h = is_void((wx + 1, wy,     wz - 1), world_voxels)

    elif plane == 'X':
        a = is_void((wx, wy, wz - 1), world_voxels)
        b = is_void((wx, wy - 1, wz - 1), world_voxels)
        c = is_void((wx, wy - 1, wz), world_voxels)
        d = is_void((wx, wy - 1, wz + 1), world_voxels)
        e = is_void((wx, wy, wz + 1), world_voxels)
        f = is_void((wx, wy + 1, wz + 1), world_voxels)
        g = is_void((wx, wy + 1, wz), world_voxels)
        h = is_void((wx, wy + 1, wz - 1), world_voxels)

    else:  # 'Z' plane
        a = is_void((wx - 1, wy,     wz), world_voxels)
        b = is_void((wx - 1, wy - 1, wz), world_voxels)
        c = is_void((wx,     wy - 1, wz), world_voxels)
        d = is_void((wx + 1, wy - 1, wz), world_voxels)
        e = is_void((wx + 1, wy,     wz), world_voxels)
        f = is_void((wx + 1, wy + 1, wz), world_voxels)
        g = is_void((wx,     wy + 1, wz), world_voxels)
        h = is_void((wx - 1, wy + 1, wz), world_voxels)

    # Each corner is sum of 3 neighbors
    ao = (
        (a + b + c),  # corner 0
        (g + h + a),  # corner 1
        (e + f + g),  # corner 2
        (c + d + e)   # corner 3
    )
    return ao

@njit
def pack_data(x, y, z, voxel_id, face_id, ao_id, flip_id):
    """
    A single 32-bit integer packing various bits:
    x:6, y:6, z:6, voxel_id:8, face_id:3, ao_id:2, flip_id:1
    """
    a, b, c, d, e, f, g = x, y, z, voxel_id, face_id, ao_id, flip_id

    b_bit, c_bit, d_bit, e_bit, f_bit, g_bit = 6, 6, 8, 3, 2, 1
    fg_bit = f_bit + g_bit       # 2 + 1 = 3
    efg_bit = e_bit + fg_bit     # 3 + 3 = 6
    defg_bit = d_bit + efg_bit   # 8 + 6 = 14
    cdefg_bit = c_bit + defg_bit # 6 + 14 = 20
    bcdefg_bit = b_bit + cdefg_bit # 6 + 20 = 26

    packed_data = (
        a << bcdefg_bit |
        b << cdefg_bit |
        c << defg_bit  |
        d << efg_bit   |
        e << fg_bit    |
        f << g_bit     |
        g
    )
    return packed_data

@njit
def add_data(vertex_data, index, *vertices):
    for vertex in vertices:
        vertex_data[index] = vertex
        index += 1
    return index

@njit
def build_chunk_mesh(chunk_voxels, format_size, chunk_pos, world_voxels):
    """
    Build the chunk's mesh by iterating over all local coords (x,y,z)
    in [0..CHUNK_SIZE-1], computing the block's world coords (wx, wy, wz),
    and testing each face if it's exposed (is_void).
    """
    vertex_data = np.empty(CHUNK_VOL * 18 * format_size, dtype=np.uint32)
    index = 0

    cx, cy, cz = chunk_pos  # chunk_pos is in chunk-coords
    chunk_origin_x = cx * CHUNK_SIZE
    chunk_origin_y = cy * CHUNK_SIZE
    chunk_origin_z = cz * CHUNK_SIZE

    for x in range(CHUNK_SIZE):
        for y in range(CHUNK_SIZE):
            for z in range(CHUNK_SIZE):
                voxel_id = chunk_voxels[x + CHUNK_SIZE*z + CHUNK_AREA*y]
                if voxel_id == 0:
                    continue

                # Convert local -> world block coords
                wx = x + chunk_origin_x
                wy = y + chunk_origin_y
                wz = z + chunk_origin_z

                # Top face
                if is_void((wx, wy + 1, wz), world_voxels):
                    ao = get_ao((x, y + 1, z), (wx, wy + 1, wz), world_voxels, 'Y')
                    flip_id = (ao[1] + ao[3]) > (ao[0] + ao[2])

                    v0 = pack_data(x,     y + 1, z,     voxel_id, 0, ao[0], flip_id)
                    v1 = pack_data(x + 1, y + 1, z,     voxel_id, 0, ao[1], flip_id)
                    v2 = pack_data(x + 1, y + 1, z + 1, voxel_id, 0, ao[2], flip_id)
                    v3 = pack_data(x,     y + 1, z + 1, voxel_id, 0, ao[3], flip_id)

                    if flip_id:
                        index = add_data(vertex_data, index, v1, v0, v3, v1, v3, v2)
                    else:
                        index = add_data(vertex_data, index, v0, v3, v2, v0, v2, v1)

                # Bottom face
                if is_void((wx, wy - 1, wz), world_voxels):
                    ao = get_ao((x, y - 1, z), (wx, wy - 1, wz), world_voxels, 'Y')
                    flip_id = (ao[1] + ao[3]) > (ao[0] + ao[2])

                    v0 = pack_data(x,     y, z,     voxel_id, 1, ao[0], flip_id)
                    v1 = pack_data(x + 1, y, z,     voxel_id, 1, ao[1], flip_id)
                    v2 = pack_data(x + 1, y, z + 1, voxel_id, 1, ao[2], flip_id)
                    v3 = pack_data(x,     y, z + 1, voxel_id, 1, ao[3], flip_id)

                    if flip_id:
                        index = add_data(vertex_data, index, v1, v3, v0, v1, v2, v3)
                    else:
                        index = add_data(vertex_data, index, v0, v2, v3, v0, v1, v2)

                # Right face
                if is_void((wx + 1, wy, wz), world_voxels):
                    ao = get_ao((x + 1, y, z), (wx + 1, wy, wz), world_voxels, 'X')
                    flip_id = (ao[1] + ao[3]) > (ao[0] + ao[2])

                    v0 = pack_data(x + 1, y,     z,     voxel_id, 2, ao[0], flip_id)
                    v1 = pack_data(x + 1, y + 1, z,     voxel_id, 2, ao[1], flip_id)
                    v2 = pack_data(x + 1, y + 1, z + 1, voxel_id, 2, ao[2], flip_id)
                    v3 = pack_data(x + 1, y,     z + 1, voxel_id, 2, ao[3], flip_id)

                    if flip_id:
                        index = add_data(vertex_data, index, v3, v0, v1, v3, v1, v2)
                    else:
                        index = add_data(vertex_data, index, v0, v1, v2, v0, v2, v3)

                # Left face
                if is_void((wx - 1, wy, wz), world_voxels):
                    ao = get_ao((x - 1, y, z), (wx - 1, wy, wz), world_voxels, 'X')
                    flip_id = (ao[1] + ao[3]) > (ao[0] + ao[2])

                    v0 = pack_data(x, y,     z,     voxel_id, 3, ao[0], flip_id)
                    v1 = pack_data(x, y + 1, z,     voxel_id, 3, ao[1], flip_id)
                    v2 = pack_data(x, y + 1, z + 1, voxel_id, 3, ao[2], flip_id)
                    v3 = pack_data(x, y,     z + 1, voxel_id, 3, ao[3], flip_id)

                    if flip_id:
                        index = add_data(vertex_data, index, v3, v1, v0, v3, v2, v1)
                    else:
                        index = add_data(vertex_data, index, v0, v2, v1, v0, v3, v2)

                # Back face
                if is_void((wx, wy, wz - 1), world_voxels):
                    ao = get_ao((x, y, z - 1), (wx, wy, wz - 1), world_voxels, 'Z')
                    flip_id = (ao[1] + ao[3]) > (ao[0] + ao[2])

                    v0 = pack_data(x,     y,     z, voxel_id, 4, ao[0], flip_id)
                    v1 = pack_data(x,     y + 1, z, voxel_id, 4, ao[1], flip_id)
                    v2 = pack_data(x + 1, y + 1, z, voxel_id, 4, ao[2], flip_id)
                    v3 = pack_data(x + 1, y,     z, voxel_id, 4, ao[3], flip_id)

                    if flip_id:
                        index = add_data(vertex_data, index, v3, v0, v1, v3, v1, v2)
                    else:
                        index = add_data(vertex_data, index, v0, v1, v2, v0, v2, v3)

                # Front face
                if is_void((wx, wy, wz + 1), world_voxels):
                    ao = get_ao((x, y, z + 1), (wx, wy, wz + 1), world_voxels, 'Z')
                    flip_id = (ao[1] + ao[3]) > (ao[0] + ao[2])

                    v0 = pack_data(x,     y,     z + 1, voxel_id, 5, ao[0], flip_id)
                    v1 = pack_data(x,     y + 1, z + 1, voxel_id, 5, ao[1], flip_id)
                    v2 = pack_data(x + 1, y + 1, z + 1, voxel_id, 5, ao[2], flip_id)
                    v3 = pack_data(x + 1, y,     z + 1, voxel_id, 5, ao[3], flip_id)

                    if flip_id:
                        index = add_data(vertex_data, index, v3, v1, v0, v3, v2, v1)
                    else:
                        index = add_data(vertex_data, index, v0, v2, v1, v0, v3, v2)

    return vertex_data[:index]
