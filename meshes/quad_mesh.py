from settings import *
from meshes.base_mesh import BaseMesh


class QuadMesh(BaseMesh):
    def __init__(self, app):
        super().__init__()
        self.app = app

        self.ctx = self.app.ctx
        self.program = self.app.shader_program.water
        self.vbo_format = "2u1 3u1"
        self.attrs = ("in_tex_coord", "in_position")
        self.vao = self.get_vao()

    def get_vertex_data(self):
        vertices = np.array(
            [(0, 0, 0), (1, 0, 1), (1, 0, 0), (0, 0, 0), (0, 0, 1), (1, 0, 1)],
            dtype="uint8",
        )

        tex_coords = np.array(
            [(0, 0), (1, 1), (1, 0), (0, 0), (0, 1), (1, 1)], dtype="uint8"
        )

        vertex_data = np.hstack([tex_coords, vertices])
        return vertex_data

    def create_2d_quad(ctx):
        """
        Creates a simple VBO + VAO for drawing a quad from (0,0) to (1,1).
        We'll stretch/translate it in the vertex shader via u_offset, u_scale.
        Returns (vao, vbo).
        """

        # 4 corners of a rectangle, plus UV coords
        # (x, y, u, v)
        vertices = np.array(
            [
                #  x,   y,   u,   v
                0.0,
                0.0,
                0.0,
                1.0,  # bottom-left
                1.0,
                0.0,
                1.0,
                1.0,  # bottom-right
                1.0,
                1.0,
                1.0,
                0.0,  # top-right
                0.0,
                1.0,
                0.0,
                0.0,  # top-left
            ],
            dtype="f4",
        )

        vbo = ctx.buffer(vertices.tobytes())

        # We draw as TRIANGLE_FAN: 4 vertices = 2 triangles
        vao_content = [(vbo, "2f 2f", "in_pos", "in_tex")]
        vao = ctx.vertex_array(ctx.programs["gui2d"], vao_content)

        return vao, vbo
