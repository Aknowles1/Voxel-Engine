# voxel_handler.py

from settings import *
from meshes.chunk_mesh_builder import get_chunk_index
import glm

class VoxelHandler:
    def __init__(self, world):
        self.app = world.app
        self.chunks = world.chunks

        # ray casting result
        self.chunk = None
        self.voxel_id = None
        self.voxel_index = None
        self.voxel_local_pos = None
        self.voxel_world_pos = None
        self.voxel_normal = None

        self.interaction_mode = 0  # 0: remove voxel   1: add voxel
        self.new_voxel_id = DIRT

    def is_colliding(self, position, debug=False):
        """
        Check if the given position collides with any voxel.
        :param position: A glm.vec3 (float) representing the position to check.
        :return: True if there is a collision, False otherwise.
        """
        # Convert float position to an integer world-space block position.
        voxel_world_pos = glm.ivec3(
            glm.floor(position.x),
            glm.floor(position.y),
            glm.floor(position.z)
        )

        # Get the chunk index from the world-space block coords
        chunk_index = get_chunk_index(voxel_world_pos)

        if debug:
            print(f"[is_colliding] Checking: {position} -> world block {voxel_world_pos}")
            print(f"[is_colliding] Chunk index = {chunk_index}")

        # If chunk index is out of world bounds, no collision in your finite world.
        if chunk_index < 0 or chunk_index >= len(self.chunks):
            if debug:
                print("[is_colliding] Out of valid chunk range -> no collision")
            return False

        chunk = self.chunks[chunk_index]
        if chunk is None:
            if debug:
                print("[is_colliding] Chunk is None -> no collision")
            return False

        # Convert the world block position to local chunk coords
        # chunk.position is presumably (cx, cy, cz) in chunk-space
        local_pos = voxel_world_pos - glm.ivec3(chunk.position) * CHUNK_SIZE

        if debug:
            print(f"[is_colliding] Local pos = {local_pos}")

        # Range check for local coords
        if not (0 <= local_pos.x < CHUNK_SIZE and
                0 <= local_pos.y < CHUNK_SIZE and
                0 <= local_pos.z < CHUNK_SIZE):
            if debug:
                print("[is_colliding] Local position out of chunk bounds -> no collision")
            return False

        # -------------------------------
        # FIX THE INDEXING HERE:
        # (x, z, y) to match build_chunk_mesh & terrain_gen
        # -------------------------------
        x, y, z = local_pos.x, local_pos.y, local_pos.z
        voxel_index = x + (CHUNK_SIZE * z) + (CHUNK_AREA * y)  # <-- FIXED LINE HERE

        # Double-check in-bounds:
        if voxel_index < 0 or voxel_index >= len(chunk.voxels):
            if debug:
                print("[is_colliding] Invalid voxel index -> no collision")
            return False

        voxel_id = chunk.voxels[voxel_index]

        # Zero typically means "air" or "empty"
        collision = (voxel_id != 0)

        if debug:
            print(f"[is_colliding] voxel_id={voxel_id}, collision={collision}")
            print(f"Chunk position (in chunk coords): {chunk.position}")
            print(f"World block position: {voxel_world_pos}")
            print(f"Local chunk coords: {local_pos}")
            print(f"Hit collision type: {collision}")
            print(f"chunk.voxels[{voxel_index}] = {voxel_id}")

        return collision

    def set_voxel_type(self, type_id):
        self.new_voxel_id = type_id

    def add_voxel(self):
        if self.voxel_id:
            # check voxel id along normal
            result = self.get_voxel_id(self.voxel_world_pos + self.voxel_normal)
            if not result[0]:  # i.e. if that position is empty
                _, voxel_index, _, chunk = result
                chunk.voxels[voxel_index] = self.new_voxel_id
                chunk.mesh.rebuild()
                if chunk.is_empty:
                    chunk.is_empty = False

    def rebuild_adj_chunk(self, adj_voxel_pos):
        index = get_chunk_index(adj_voxel_pos)
        if index != -1:
            self.chunks[index].mesh.rebuild()

    def rebuild_adjacent_chunks(self):
        lx, ly, lz = self.voxel_local_pos
        wx, wy, wz = self.voxel_world_pos

        if lx == 0:
            self.rebuild_adj_chunk((wx - 1, wy, wz))
        elif lx == CHUNK_SIZE - 1:
            self.rebuild_adj_chunk((wx + 1, wy, wz))

        if ly == 0:
            self.rebuild_adj_chunk((wx, wy - 1, wz))
        elif ly == CHUNK_SIZE - 1:
            self.rebuild_adj_chunk((wx, wy + 1, wz))

        if lz == 0:
            self.rebuild_adj_chunk((wx, wy, wz - 1))
        elif lz == CHUNK_SIZE - 1:
            self.rebuild_adj_chunk((wx, wy, wz + 1))

    def remove_voxel(self):
        if self.voxel_id:
            self.chunk.voxels[self.voxel_index] = 0
            self.chunk.mesh.rebuild()
            self.rebuild_adjacent_chunks()

    def set_voxel(self):
        if self.interaction_mode:
            self.add_voxel()
        else:
            self.remove_voxel()

    def switch_mode(self):
        self.interaction_mode = not self.interaction_mode

    def update(self):
        self.ray_cast()

    def ray_cast(self):
        # Standard DDA or Grid Traversal for ray-cast
        x1, y1, z1 = self.app.player.position
        x2, y2, z2 = self.app.player.position + self.app.player.forward * MAX_RAY_DIST

        current_voxel_pos = glm.ivec3(x1, y1, z1)
        self.voxel_id = 0
        self.voxel_normal = glm.ivec3(0)
        step_dir = -1

        dx = glm.sign(x2 - x1)
        delta_x = min(dx / (x2 - x1), 1e7) if dx != 0 else 1e7
        max_x = delta_x * (1.0 - glm.fract(x1)) if dx > 0 else delta_x * glm.fract(x1)

        dy = glm.sign(y2 - y1)
        delta_y = min(dy / (y2 - y1), 1e7) if dy != 0 else 1e7
        max_y = delta_y * (1.0 - glm.fract(y1)) if dy > 0 else delta_y * glm.fract(y1)

        dz = glm.sign(z2 - z1)
        delta_z = min(dz / (z2 - z1), 1e7) if dz != 0 else 1e7
        max_z = delta_z * (1.0 - glm.fract(z1)) if dz > 0 else delta_z * glm.fract(z1)

        while not (max_x > 1.0 and max_y > 1.0 and max_z > 1.0):
            result = self.get_voxel_id(voxel_world_pos=current_voxel_pos)
            if result[0]:
                self.voxel_id, self.voxel_index, self.voxel_local_pos, self.chunk = result
                self.voxel_world_pos = current_voxel_pos

                # Figure out the face normal from which side we stepped
                if step_dir == 0:
                    self.voxel_normal.x = -dx
                elif step_dir == 1:
                    self.voxel_normal.y = -dy
                else:
                    self.voxel_normal.z = -dz
                return True

            # Advance along whichever tMax is smallest
            if max_x < max_y:
                if max_x < max_z:
                    current_voxel_pos.x += dx
                    max_x += delta_x
                    step_dir = 0
                else:
                    current_voxel_pos.z += dz
                    max_z += delta_z
                    step_dir = 2
            else:
                if max_y < max_z:
                    current_voxel_pos.y += dy
                    max_y += delta_y
                    step_dir = 1
                else:
                    current_voxel_pos.z += dz
                    max_z += delta_z
                    step_dir = 2
        return False

    def get_voxel_id(self, voxel_world_pos):
        chunk_x = voxel_world_pos.x // CHUNK_SIZE
        chunk_y = voxel_world_pos.y // CHUNK_SIZE
        chunk_z = voxel_world_pos.z // CHUNK_SIZE

        if not (0 <= chunk_x < WORLD_W and 0 <= chunk_y < WORLD_H and 0 <= chunk_z < WORLD_D):
            return 0, 0, glm.ivec3(0), None

        chunk_index = chunk_x + WORLD_W * chunk_z + WORLD_AREA * chunk_y
        chunk = self.chunks[chunk_index]
        if chunk is None:
            return 0, 0, glm.ivec3(0), None

        local_x = voxel_world_pos.x - (chunk_x * CHUNK_SIZE)
        local_y = voxel_world_pos.y - (chunk_y * CHUNK_SIZE)
        local_z = voxel_world_pos.z - (chunk_z * CHUNK_SIZE)

        if not (0 <= local_x < CHUNK_SIZE and
                0 <= local_y < CHUNK_SIZE and
                0 <= local_z < CHUNK_SIZE):
            return 0, 0, glm.ivec3(0), None

        voxel_index = local_x + (local_z * CHUNK_SIZE) + (local_y * CHUNK_AREA)
        if not (0 <= voxel_index < len(chunk.voxels)):
            return 0, 0, glm.ivec3(0), None

        voxel_id = chunk.voxels[voxel_index]
        return voxel_id, voxel_index, glm.ivec3(local_x, local_y, local_z), chunk

    def get_floor_height(self, x, z):
        """
        Returns the highest solid voxel's top surface Y at the given (x, z).
        If no solid voxel exists, returns None.

        This naive approach loops from the top chunk (WORLD_H - 1) down
        to the bottom chunk (0), and within each chunk from top voxel down
        to bottom voxel in that chunk. If it finds a solid voxel, it returns
        that voxel's top face (world_y + 1).
        """

        # 1) Convert x, z to integer coords (floor for negative as well)
        x_int = int(glm.floor(x))
        z_int = int(glm.floor(z))

        # 2) Compute which chunk in the XZ plane
        chunk_x = x_int // CHUNK_SIZE
        chunk_z = z_int // CHUNK_SIZE

        # 3) Check horizontal world bounds
        if not (0 <= chunk_x < WORLD_W and 0 <= chunk_z < WORLD_D):
            return None

        # 4) Local x, z within the chunk
        #    (Handle negative positions too; Python's % can yield negative remainders if x_int < 0)
        local_x = x_int % CHUNK_SIZE
        local_z = z_int % CHUNK_SIZE

        # In case Python's modulo produced negative values, fix them:
        if local_x < 0:
            local_x += CHUNK_SIZE
        if local_z < 0:
            local_z += CHUNK_SIZE

        # 5) Loop from the top chunk_y down to 0
        for chunk_y in reversed(range(WORLD_H)):
            chunk_index = chunk_x + (WORLD_W * chunk_z) + (WORLD_AREA * chunk_y)
            chunk = self.chunks[chunk_index]
            if chunk is None:
                # This chunk hasn't been generated or is empty -> skip
                continue

            # 6) Loop from top of this chunk (CHUNK_SIZE - 1) down to 0
            for local_y in reversed(range(CHUNK_SIZE)):
                voxel_index = (
                    local_x
                    + (local_z * CHUNK_SIZE)
                    + (local_y * CHUNK_AREA)
                )

                # Ensure we don’t go out of bounds in the voxel array
                if not (0 <= voxel_index < len(chunk.voxels)):
                    continue

                voxel_id = chunk.voxels[voxel_index]
                # 0 typically means "air" or "empty"
                if voxel_id != 0:
                    # Found a solid voxel. Return the top surface = (world_y + 1)
                    world_y = chunk_y * CHUNK_SIZE + local_y
                    return world_y + 1

        # If we exhaust everything and find no solid block -> None
        return None
