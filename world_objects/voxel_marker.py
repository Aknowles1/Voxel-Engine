from settings import *
from meshes.cube_mesh import CubeMesh

class VoxelMarker:
    def __init__(self, voxel_handler):
        self.app = voxel_handler.app
        self.handler = voxel_handler
        self.position = glm.vec3(0)
        self.m_model = self.get_model_matrix()
        self.mesh = CubeMesh(self.app)

    def update(self):
        """
        Place the marker at the currently targeted block (if removing)
        or at the adjacent block along the normal (if adding).
        """
        if self.handler.voxel_id:
            if self.handler.interaction_mode:
                # "Add" mode: show marker on the outside face
                target_pos = self.handler.voxel_world_pos + self.handler.voxel_normal
            else:
                # "Remove" mode: show marker on the exact block you’re removing
                target_pos = self.handler.voxel_world_pos

            # Ensure it’s a float vec3 but has integer alignment
            self.position = glm.vec3(int(target_pos.x), int(target_pos.y), int(target_pos.z))

    def set_uniform(self):
        self.mesh.program['mode_id'] = self.handler.interaction_mode
        self.mesh.program['m_model'].write(self.get_model_matrix())

    def get_model_matrix(self):
        return glm.translate(glm.mat4(), self.position)

    def render(self):
        if self.handler.voxel_id:
            self.set_uniform()
            self.mesh.render()
