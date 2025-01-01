import numpy as np
import moderngl as mgl


def create_2d_quad(ctx, gui2d_program):
    """
    Creates a simple VBO + VAO for drawing a quad from (0,0) to (1,1).
    We'll stretch/translate it via (u_offset, u_scale) in the shader.
    Returns (vao, vbo).
    """
    # 4 corners, plus UV coords: (x, y, u, v)
    vertices = np.array(
        [
            #    x,    y,    u,    v
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

    # We draw as TRIANGLE_FAN (4 verts = 2 triangles)
    vao_content = [(vbo, "2f 2f", "in_pos", "in_tex")]
    # Make sure the 'gui2d' program is the one with 'in_pos' and 'in_tex'
    vao = ctx.vertex_array(gui2d_program, vao_content)
    return vao, vbo
