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

    def is_colliding(self, position, debug=False):
        """
        Check if the given position collides with any voxel.
        :param position: A glm.vec3 (float) representing the position to check.
        :return: True if there is a collision, False otherwise.
        """
        # Convert float position to an integer world-space block position.
        voxel_world_pos = glm.ivec3(glm.floor(position.x),glm.floor(position.y),glm.floor(position.z))

        # Get the chunk index from the world-space block coords
        chunk_index = get_chunk_index(voxel_world_pos)

        
        print(f"[is_colliding] Checking: {position} -> world block {voxel_world_pos}")
        print(f"[is_colliding] Chunk index = {chunk_index}")

        # If chunk index is out of world bounds, no collision in your finite world.
        if chunk_index < 0 or chunk_index >= len(self.chunks):
            print("[is_colliding] Out of valid chunk range -> no collision")
            return False

        # If the chunk is None or not generated, treat as no collision
        chunk = self.chunks[chunk_index]
        if chunk is None:
            print("[is_colliding] Chunk is None -> no collision")
            return False

        # Convert the world block position to local chunk coords
        # chunk.position is presumably the (cx, cy, cz) of the chunk in chunk-space
        # so the actual world-space offset is chunk.position * CHUNK_SIZE
        local_pos = voxel_world_pos - glm.ivec3(chunk.position) * CHUNK_SIZE


        print(f"[is_colliding] Local pos = {local_pos}")

        # If the local pos is out of [0, CHUNK_SIZE-1], no collision in this chunk
        if not (0 <= local_pos.x < CHUNK_SIZE and
                0 <= local_pos.y < CHUNK_SIZE and
                0 <= local_pos.z < CHUNK_SIZE):
            print("[is_colliding] Local position out of chunk bounds -> no collision")
            return False

        voxel_index = local_pos.x + local_pos.y * CHUNK_SIZE + local_pos.z * CHUNK_AREA

        # If voxel_index is out of bounds, skip collision
        if voxel_index < 0 or voxel_index >= len(chunk.voxels):
            print("[is_colliding] Invalid voxel index -> no collision")
            return False

        voxel_id = chunk.voxels[voxel_index]

        # Zero typically means "air" or "empty"
        collision = (voxel_id != 0)

        print(f"[is_colliding] voxel_id={voxel_id}, collision={collision}")

        print(f"Chunk position (in chunk coords): {chunk.position}")
        print(f"World block position: {voxel_world_pos}")
        print(f"Local chunk coords: {local_pos}")

        print(f"Hit collision type: " + str(collision))
        print("chunk.voxels[{}] = {}".format(voxel_index, chunk.voxels[voxel_index]))
        # if voxel_world_pos == position & voxel_id != 0:
        return collision


    def set_voxel_type(self, type_id):
        self.new_voxel_id = type_id

    def add_voxel(self):
        if self.voxel_id:
            # check voxel id along normal
            result = self.get_voxel_id(self.voxel_world_pos + self.voxel_normal)

            # is the new place empty?
            if not result[0]:
                _, voxel_index, _, chunk = result
                chunk.voxels[voxel_index] = self.new_voxel_id
                chunk.mesh.rebuild()

                # was it an empty chunk
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
        # start point
        x1, y1, z1 = self.app.player.position
        # end point
        x2, y2, z2 = self.app.player.position + self.app.player.forward * MAX_RAY_DIST

        current_voxel_pos = glm.ivec3(x1, y1, z1)
        self.voxel_id = 0
        self.voxel_normal = glm.ivec3(0)
        step_dir = -1

        dx = glm.sign(x2 - x1)
        delta_x = min(dx / (x2 - x1), 10000000.0) if dx != 0 else 10000000.0
        max_x = delta_x * (1.0 - glm.fract(x1)) if dx > 0 else delta_x * glm.fract(x1)

        dy = glm.sign(y2 - y1)
        delta_y = min(dy / (y2 - y1), 10000000.0) if dy != 0 else 10000000.0
        max_y = delta_y * (1.0 - glm.fract(y1)) if dy > 0 else delta_y * glm.fract(y1)

        dz = glm.sign(z2 - z1)
        delta_z = min(dz / (z2 - z1), 10000000.0) if dz != 0 else 10000000.0
        max_z = delta_z * (1.0 - glm.fract(z1)) if dz > 0 else delta_z * glm.fract(z1)

        while not (max_x > 1.0 and max_y > 1.0 and max_z > 1.0):

            result = self.get_voxel_id(voxel_world_pos=current_voxel_pos)
            if result[0]:
                self.voxel_id, self.voxel_index, self.voxel_local_pos, self.chunk = result
                self.voxel_world_pos = current_voxel_pos

                if step_dir == 0:
                    self.voxel_normal.x = -dx
                elif step_dir == 1:
                    self.voxel_normal.y = -dy
                else:
                    self.voxel_normal.z = -dz
                return True

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
        If out of range or chunk is None, returns (0, 0, glm.ivec3(0), None).
        """
        # 1) Convert world block coords to chunk coords with integer division
        chunk_x = voxel_world_pos.x // CHUNK_SIZE
        chunk_y = voxel_world_pos.y // CHUNK_SIZE
        chunk_z = voxel_world_pos.z // CHUNK_SIZE

        # 2) Check if chunk coords are within world bounds
        if not (0 <= chunk_x < WORLD_W and 0 <= chunk_y < WORLD_H and 0 <= chunk_z < WORLD_D):
            return 0, 0, glm.ivec3(0), None

        # 3) Compute chunk index
        chunk_index = chunk_x + WORLD_W * chunk_z + WORLD_AREA * chunk_y
        chunk = self.chunks[chunk_index]
        if chunk is None:
            return 0, 0, glm.ivec3(0), None

        # 4) Compute local voxel coords within the chunk
        #    chunk.position is (cx, cy, cz) in chunk-space
        #    so the chunk\u2019s world-space origin is (cx * CHUNK_SIZE, ...)
        local_x = voxel_world_pos.x - (chunk_x * CHUNK_SIZE)
        local_y = voxel_world_pos.y - (chunk_y * CHUNK_SIZE)
        local_z = voxel_world_pos.z - (chunk_z * CHUNK_SIZE)

        # 5) Range check for local coords
        if not (0 <= local_x < CHUNK_SIZE and
                0 <= local_y < CHUNK_SIZE and
                0 <= local_z < CHUNK_SIZE):
            return 0, 0, glm.ivec3(0), None

        # 6) Compute the index in the chunk.voxels array
        voxel_index = local_x + (local_z * CHUNK_SIZE) + (local_y * CHUNK_AREA)
        if not (0 <= voxel_index < len(chunk.voxels)):
            return 0, 0, glm.ivec3(0), None

        voxel_id = chunk.voxels[voxel_index]
        return voxel_id, voxel_index, glm.ivec3(local_x, local_y, local_z), chunk

