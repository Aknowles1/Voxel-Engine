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
        pg.display.gl_set_attribute(pg.GL_CONTEXT_PROFILE_MASK, pg.GL_CONTEXT_PROFILE_CORE)
        pg.display.gl_set_attribute(pg.GL_DEPTH_SIZE, DEPTH_SIZE)
        pg.display.gl_set_attribute(pg.GL_MULTISAMPLESAMPLES, NUM_SAMPLES)

        pg.display.set_mode(WIN_RES, flags=pg.OPENGL | pg.DOUBLEBUF)
        self.ctx = mgl.create_context()

        self.ctx.enable(flags=mgl.DEPTH_TEST | mgl.CULL_FACE | mgl.BLEND)
        self.ctx.gc_mode = 'auto'

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
        self.gui_quad_vao, self.gui_quad_vbo = create_2d_quad(self.ctx, self.gui2d_program)

        # We'll also store a dict for icons => mgl.Textures
        self.icon_textures = {}

    def update(self):
        self.player.update()
        self.shader_program.update()
        self.scene.update()
        self.draw_hotbar_2d()

        self.delta_time = self.clock.tick()
        self.time = pg.time.get_ticks() * 0.001
        pg.display.set_caption(f'{self.clock.get_fps() :.0f}')

    def render(self):
        self.ctx.clear(color=BG_COLOR)
        self.scene.render()
        self.draw_hotbar_2d()
        pg.display.flip()

    def handle_events(self):
        for event in pg.event.get():
            if event.type == pg.QUIT or (event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE):
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
            GREEN_LEAF: "green_leaf.png"       
        }.get(block_type, "sand.png")  # default to sand if missing

        try:
            surf = pg.image.load(f"assets/icons/{file_name}").convert_alpha()
        except Exception as e:
            print("Failed to load icon:", e)
        # Flip or not, depending on your preference. 
        # Usually we do flip(True, False) if we want 0,0 at bottom-left:
        surf = pg.transform.flip(surf, True, False)

        w, h = surf.get_size()
        raw_data = pg.image.tostring(surf, 'RGBA', False)

        # Create an mgl.Texture2D
        tex = self.ctx.texture((w, h), 4, raw_data)
        tex.build_mipmaps()
        tex.filter = (mgl.LINEAR, mgl.LINEAR)

        self.icon_textures[block_type] = tex
        return tex
    
    def draw_hotbar_2d(self):
        # 1) disable depth
        self.ctx.disable(mgl.DEPTH_TEST)

        # 2) Real screen size from Pygame
        screen_w, screen_h = pg.display.get_surface().get_size()

        # We can do bottom=0, top=screen_h, so (0,0) is bottom-left
        ortho = glm.ortho(0, screen_w, 0, screen_h, -1, 1)

        prog = self.gui2d_program
        # pass the matrix as bytes
        prog['u_proj'].write(ortho.to_bytes())
        prog['u_texture'].value = 0

        icon_size = 64
        gap = 10
        block_types = [SAND, GRASS, DIRT, STONE, SNOW, LEAVES, WOOD, GREEN_LEAF]

        # Now, if (0,0) is bottom-left, let's put the bar near the bottom
        hotbar_width = len(block_types) * (icon_size + gap) + gap
        hotbar_height = icon_size + gap * 2

        # e.g., place it centered horizontally, 30 px above bottom
        hotbar_x = (screen_w - hotbar_width) // 2
        hotbar_y = 30

        selected_block = self.scene.world.voxel_handler.new_voxel_id

        x_cursor = hotbar_x + gap
        y_cursor = hotbar_y + gap

        for b_type in block_types:
            tex = self.get_icon_texture(b_type)
            tex.use(location=0)

            # offset is bottom-left corner
            prog['u_offset'].write(struct.pack('2f', x_cursor, y_cursor))
            prog['u_scale'].write(struct.pack('2f', icon_size, icon_size))

            self.gui_quad_vao.render(mode=mgl.TRIANGLE_FAN)

            # highlight if selected...
            if b_type == selected_block:
                pass

            x_cursor += icon_size + gap

        self.ctx.enable(mgl.DEPTH_TEST)
        print(f"screen_w={screen_w}, hotbar_width={hotbar_width}, hotbar_x={hotbar_x}")




if __name__ == '__main__':
    app = VoxelEngine()
    app.run()
