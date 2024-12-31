from settings import *
from meshes.chunk_mesh_builder import get_chunk_index

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

    def is_colliding(self, position):
        """
        Check if the given position collides with any voxel.

        :param position: A glm.vec3 (float) representing the position to check.
        :return: True if there is a collision, False otherwise.
        """
        # convert float position to integer block coords
        voxel_world_pos = glm.ivec3(position)

        # 1) Find the chunk indices (cx, cy, cz) by integer division
        chunk_x = voxel_world_pos.x // CHUNK_SIZE
        chunk_y = voxel_world_pos.y // CHUNK_SIZE
        chunk_z = voxel_world_pos.z // CHUNK_SIZE

        # 2) Check world bounds
        if not (0 <= chunk_x < WORLD_W and
                0 <= chunk_y < WORLD_H and
                0 <= chunk_z < WORLD_D):
            return False  # out of the generated world

        # 3) Compute the 1D chunk index
        chunk_index = chunk_x + (chunk_z * WORLD_W) + (chunk_y * WORLD_AREA)
        chunk = self.chunks[chunk_index]
        if chunk is None:
            return False  # chunk not loaded or is None

        # 4) Compute local voxel coords within the chunk
        #    chunk.position is (cx, cy, cz) in chunk space, so:
        world_chunk_origin = glm.ivec3(chunk.position) * CHUNK_SIZE
        local_x = voxel_world_pos.x - world_chunk_origin.x
        local_y = voxel_world_pos.y - world_chunk_origin.y
        local_z = voxel_world_pos.z - world_chunk_origin.z

        # 5) Range check (should be in [0..CHUNK_SIZE-1])
        if not (0 <= local_x < CHUNK_SIZE and
                0 <= local_y < CHUNK_SIZE and
                0 <= local_z < CHUNK_SIZE):
            return False

        # 6) Compute 1D index into chunk.voxels
        voxel_index = (local_x
                       + local_y * CHUNK_SIZE
                       + local_z * CHUNK_AREA)
        if voxel_index < 0 or voxel_index >= len(chunk.voxels):
            return False

        voxel_id = chunk.voxels[voxel_index]
        collision = (voxel_id != 0)
        return collision

    def set_voxel_type(self, type_id):
        self.new_voxel_id = type_id

    def add_voxel(self):
        """
        Places self.new_voxel_id into the block where the ray hits (plus normal offset).
        """
        if self.voxel_id:
            # Check voxel ID along normal:
            new_pos = self.voxel_world_pos + self.voxel_normal
            voxel_id, voxel_index, voxel_local_pos, chunk = self.get_voxel_id(new_pos)

            # Is the new place empty?
            if voxel_id == 0 and chunk:
                chunk.voxels[voxel_index] = self.new_voxel_id
                chunk.mesh.rebuild()

                # Was it an empty chunk?
                if chunk.is_empty:
                    chunk.is_empty = False
        print("Ray hit:", self.voxel_world_pos, "normal:", self.voxel_normal)
        print("Placing/removing at:", self.voxel_world_pos + self.voxel_normal)


    def rebuild_adj_chunk(self, adj_voxel_pos):
        chunk_x = adj_voxel_pos[0] // CHUNK_SIZE
        chunk_y = adj_voxel_pos[1] // CHUNK_SIZE
        chunk_z = adj_voxel_pos[2] // CHUNK_SIZE
        if not (0 <= chunk_x < WORLD_W and 0 <= chunk_y < WORLD_H and 0 <= chunk_z < WORLD_D):
            return
        chunk_index = chunk_x + WORLD_W * chunk_z + WORLD_AREA * chunk_y
        self.chunks[chunk_index].mesh.rebuild()

    def rebuild_adjacent_chunks(self):
        """
        If you remove a voxel on the boundary (like local_x=0),
        rebuild the neighboring chunk so you don't see a gap.
        """
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
        """
        Removes the voxel where the ray currently hits.
        """
        if self.voxel_id and self.chunk:
            self.chunk.voxels[self.voxel_index] = 0
            self.chunk.mesh.rebuild()
            self.rebuild_adjacent_chunks()

        print("Ray hit:", self.voxel_world_pos, "normal:", self.voxel_normal)
        print("Placing/removing at:", self.voxel_world_pos + self.voxel_normal)


    def set_voxel(self):
        """
        Decide if we're adding or removing based on self.interaction_mode.
        """
        if self.interaction_mode:
            self.add_voxel()
        else:
            self.remove_voxel()

    def switch_mode(self):
        self.interaction_mode = not self.interaction_mode

    def update(self):
        """
        Each frame, run the raycast to see which voxel we are targeting.
        """
        self.ray_cast()

    def ray_cast(self):
        """
        Cast a ray from the player's position along 'forward' up to MAX_RAY_DIST,
        stepping block by block, until hitting a non-air voxel.
        Stores the results in self.voxel_id, etc.
        """
        x1, y1, z1 = self.app.player.position
        x2, y2, z2 = self.app.player.position + self.app.player.forward * MAX_RAY_DIST

        current_voxel_pos = glm.ivec3(x1, y1, z1)
        self.voxel_id = 0
        self.voxel_normal = glm.ivec3(0)
        step_dir = -1

        dx = glm.sign(x2 - x1)
        delta_x = min(dx / (x2 - x1), 1e10) if dx != 0 else 1e10
        max_x = delta_x * (1.0 - glm.fract(x1)) if dx > 0 else delta_x * glm.fract(x1)

        dy = glm.sign(y2 - y1)
        delta_y = min(dy / (y2 - y1), 1e10) if dy != 0 else 1e10
        max_y = delta_y * (1.0 - glm.fract(y1)) if dy > 0 else delta_y * glm.fract(y1)

        dz = glm.sign(z2 - z1)
        delta_z = min(dz / (z2 - z1), 1e10) if dz != 0 else 1e10
        max_z = delta_z * (1.0 - glm.fract(z1)) if dz > 0 else delta_z * glm.fract(z1)

        while not (max_x > 1.0 and max_y > 1.0 and max_z > 1.0):

            # Check if this block is solid
            result = self.get_voxel_id(voxel_world_pos=current_voxel_pos)
            if result[0] != 0:  # non-air
                self.voxel_id, self.voxel_index, self.voxel_local_pos, self.chunk = result
                self.voxel_world_pos = current_voxel_pos

                # figure out which face we hit
                if step_dir == 0:
                    self.voxel_normal.x = -dx
                elif step_dir == 1:
                    self.voxel_normal.y = -dy
                elif step_dir == 2:
                    self.voxel_normal.z = -dz
                return True

            # step along the smallest t-value
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
        """
        Return (voxel_id, voxel_index, local_pos, chunk) for a given world-block position.
        If the position is out-of-bounds or the chunk is None, returns (0, 0, 0, None).
        """
        # 1) compute chunk coords from world pos
        chunk_x = voxel_world_pos.x // CHUNK_SIZE
        chunk_y = voxel_world_pos.y // CHUNK_SIZE
        chunk_z = voxel_world_pos.z // CHUNK_SIZE

        # 2) check if chunk coords are valid
        if (0 <= chunk_x < WORLD_W and
            0 <= chunk_y < WORLD_H and
            0 <= chunk_z < WORLD_D):
            chunk_index = chunk_x + WORLD_W * chunk_z + WORLD_AREA * chunk_y
            chunk = self.chunks[chunk_index]

            if not chunk:
                return (0, 0, glm.ivec3(0), None)  # chunk isn't loaded

            # 3) local coords inside chunk
            world_chunk_origin = glm.ivec3(chunk.position) * CHUNK_SIZE
            lx = voxel_world_pos.x - world_chunk_origin.x
            ly = voxel_world_pos.y - world_chunk_origin.y
            lz = voxel_world_pos.z - world_chunk_origin.z

            if not (0 <= lx < CHUNK_SIZE and 0 <= ly < CHUNK_SIZE and 0 <= lz < CHUNK_SIZE):
                return (0, 0, glm.ivec3(0), None)

            voxel_index = lx + (ly * CHUNK_SIZE) + (lz * CHUNK_AREA)
            if voxel_index < 0 or voxel_index >= len(chunk.voxels):
                return (0, 0, glm.ivec3(0), None)

            voxel_id = chunk.voxels[voxel_index]
            return (voxel_id, voxel_index, glm.ivec3(lx, ly, lz), chunk)

        return (0, 0, glm.ivec3(0), None)
