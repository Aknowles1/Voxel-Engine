from settings import *
import moderngl as mgl
import pygame as pg
import sys
import struct
from shader_program import ShaderProgram
from scene import Scene
from player import Player
from textures import Textures
from gui_quad import create_2d_quad


class VoxelEngine:
    def __init__(self):
        pg.init()
        pg.display.gl_set_attribute(pg.GL_CONTEXT_MAJOR_VERSION, MAJOR_VER)
        pg.display.gl_set_attribute(pg.GL_CONTEXT_MINOR_VERSION, MINOR_VER)
        pg.display.gl_set_attribute(
            pg.GL_CONTEXT_PROFILE_MASK, pg.GL_CONTEXT_PROFILE_CORE
        )
        pg.display.gl_set_attribute(pg.GL_DEPTH_SIZE, DEPTH_SIZE)
        pg.display.gl_set_attribute(pg.GL_MULTISAMPLESAMPLES, NUM_SAMPLES)

        pg.display.set_mode(WIN_RES, flags=pg.OPENGL | pg.DOUBLEBUF)
        self.ctx = mgl.create_context()

        self.ctx.enable(flags=mgl.DEPTH_TEST | mgl.CULL_FACE | mgl.BLEND)
        self.ctx.gc_mode = "auto"

        self.clock = pg.time.Clock()
        self.delta_time = 0
        self.time = 0

        pg.event.set_grab(True)
        pg.mouse.set_visible(False)

        self.is_running = True
        self.on_init()

    def on_init(self):
        self.textures = Textures(self)
        self.player = Player(self)
        self.shader_program = ShaderProgram(self)
        self.scene = Scene(self)
        self.gui2d_program = self.shader_program.gui2d
        self.gui_quad_vao, self.gui_quad_vbo = create_2d_quad(
            self.ctx, self.gui2d_program
        )

        # We'll also store a dict for icons => mgl.Textures
        self.icon_textures = {}

    def update(self):
        self.player.update()
        self.shader_program.update()
        self.scene.update()
        self.draw_hotbar_2d()

        self.delta_time = self.clock.tick()
        self.time = pg.time.get_ticks() * 0.001
        pg.display.set_caption(f"{self.clock.get_fps() :.0f}")

    def render(self):
        self.ctx.clear(color=BG_COLOR)
        self.scene.render()
        self.draw_hotbar_2d()
        pg.display.flip()

    def handle_events(self):
        for event in pg.event.get():
            if event.type == pg.QUIT or (
                event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE
            ):
                self.is_running = False
            self.player.handle_event(event=event)

    def run(self):
        while self.is_running:
            self.handle_events()
            self.update()
            self.render()
        pg.quit()
        sys.exit()

    def get_icon_texture(self, block_type):
        """
        Convert a Pygame surface (e.g. 'assets/icons/foo.png') to an mgl.Texture
        on first use, then cache it in self.icon_textures.
        """
        if block_type in self.icon_textures:
            return self.icon_textures[block_type]

        # Suppose we have a dict mapping block type -> file path:
        file_name = {
            SAND: "sand.png",
            GRASS: "grass.png",
            DIRT: "dirt.png",
            STONE: "stone.png",
            SNOW: "snow.png",
            LEAVES: "leaves.png",
            WOOD: "wood.png",
            GREEN_LEAF: "green_leaf.png",
        }.get(
            block_type, "sand.png"
        )  # default to sand if missing

        try:
            surf = pg.image.load(f"assets/icons/{file_name}").convert_alpha()
        except Exception as e:
            print("Failed to load icon:", e)
        # Flip or not, depending on your preference.
        # Usually we do flip(True, False) if we want 0,0 at bottom-left:
        surf = pg.transform.flip(surf, True, False)

        w, h = surf.get_size()
        raw_data = pg.image.tostring(surf, "RGBA", False)

        # Create an mgl.Texture2D
        tex = self.ctx.texture((w, h), 4, raw_data)
        tex.build_mipmaps()
        tex.filter = (mgl.LINEAR, mgl.LINEAR)

        self.icon_textures[block_type] = tex
        return tex

    def draw_hotbar_2d(self):
        self.ctx.disable(mgl.DEPTH_TEST)

        screen_w, screen_h = pg.display.get_surface().get_size()
        ortho = glm.ortho(0, screen_w, 0, screen_h, -1, 1)

        prog = self.gui2d_program
        prog["u_proj"].write(ortho.to_bytes())
        prog["u_texture"].value = 0

        icon_size = 64 * 1.5
        gap = 10
        block_types = [SAND, GRASS, DIRT, STONE, SNOW, LEAVES, WOOD, GREEN_LEAF]

        # Figure out the hotbar dimensions
        hotbar_width = len(block_types) * (icon_size + gap) + gap
        hotbar_x = (screen_w - hotbar_width) // 2
        hotbar_y = 30
        hotbar_height = icon_size + gap * 2

        # ---------------------------
        # 1) Dark Grey Outer Border
        # ---------------------------
        border_color = (0.3, 0.3, 0.3, 1.0)  # RGBA
        border_thickness = 12.0
        outer_pad = 5.0

        outer_offset = struct.pack(
            "2f",
            hotbar_x - outer_pad - border_thickness,
            hotbar_y - outer_pad - border_thickness,
        )
        outer_scale = struct.pack(
            "2f",
            hotbar_width + (outer_pad + border_thickness) * 2,
            hotbar_height + (outer_pad + border_thickness) * 2,
        )

        prog["u_use_texture"].value = False
        prog["u_color"].write(struct.pack("4f", *border_color))
        prog["u_offset"].write(outer_offset)
        prog["u_scale"].write(outer_scale)
        self.gui_quad_vao.render(mode=mgl.TRIANGLE_FAN)

        # ---------------------------
        # 2) Lighter Grey Background
        # ---------------------------
        bg_color = (0.5, 0.5, 0.5, 1.0)
        bg_offset = struct.pack("2f", hotbar_x - outer_pad, hotbar_y - outer_pad)
        bg_scale = struct.pack(
            "2f", hotbar_width + outer_pad * 2, hotbar_height + outer_pad * 2
        )

        prog["u_color"].write(struct.pack("4f", *bg_color))
        prog["u_offset"].write(bg_offset)
        prog["u_scale"].write(bg_scale)
        self.gui_quad_vao.render(mode=mgl.TRIANGLE_FAN)

        # --------------------------------
        # 3) Draw icons (plus highlight and per-icon border)
        # --------------------------------
        selected_block = self.scene.world.voxel_handler.new_voxel_id
        x_cursor = hotbar_x + gap
        y_cursor = hotbar_y + gap

        for b_type in block_types:
            # Optional highlight if selected
            is_selected = b_type == selected_block
            if is_selected:
                prog["u_use_texture"].value = False
                prog["u_color"].write(
                    struct.pack("4f", 1.0, 1.0, 1.0, 0.3)
                )  # White, 30% alpha
                pad = 5.0
                offset = struct.pack("2f", x_cursor - pad, y_cursor - pad)
                scale = struct.pack("2f", icon_size + pad * 2, icon_size + pad * 2)
                prog["u_offset"].write(offset)
                prog["u_scale"].write(scale)
                self.gui_quad_vao.render(mode=mgl.TRIANGLE_FAN)

            # 3a) Draw a thin dark-grey border around the icon
            #     You can do this *before* or *after* the highlight—whichever you prefer
            icon_border_color = (0.2, 0.2, 0.2, 1.0)
            icon_border_thickness = 2.0  # thickness of the per-icon border

            prog["u_use_texture"].value = False
            prog["u_color"].write(struct.pack("4f", *icon_border_color))

            border_offset = struct.pack(
                "2f", x_cursor - icon_border_thickness, y_cursor - icon_border_thickness
            )
            border_scale = struct.pack(
                "2f",
                icon_size + icon_border_thickness * 2,
                icon_size + icon_border_thickness * 2,
            )

            prog["u_offset"].write(border_offset)
            prog["u_scale"].write(border_scale)
            self.gui_quad_vao.render(mode=mgl.TRIANGLE_FAN)

            # 3b) Draw the actual icon
            tex = self.get_icon_texture(b_type)
            tex.use(location=0)

            prog["u_use_texture"].value = True
            prog["u_color"].write(struct.pack("4f", 1.0, 1.0, 1.0, 1.0))
            prog["u_offset"].write(struct.pack("2f", x_cursor, y_cursor))
            prog["u_scale"].write(struct.pack("2f", icon_size, icon_size))
            self.gui_quad_vao.render(mode=mgl.TRIANGLE_FAN)

            x_cursor += icon_size + gap

        self.ctx.enable(mgl.DEPTH_TEST)


if __name__ == "__main__":
    app = VoxelEngine()
    app.run()
