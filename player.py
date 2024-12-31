import pygame as pg
from camera import Camera
from settings import *


class Player(Camera):
    def __init__(self, app, position=PLAYER_POS, yaw=-90, pitch=0):
        self.app = app
        self.player_voxel = 0
        super().__init__(position, yaw, pitch)

    def update(self):
        self.keyboard_control()
        self.mouse_control()
        super().update()

    def handle_event(self, event):
        # adding and removing voxels with clicks
        if event.type == pg.MOUSEBUTTONDOWN:
            voxel_handler = self.app.scene.world.voxel_handler
            if event.button == 1:
                voxel_handler.set_voxel()
            if event.button == 3:
                voxel_handler.switch_mode()

    def mouse_control(self):
        # Get the screen dimensions
        screen_width, screen_height = pg.display.get_surface().get_size()
        center_x, center_y = screen_width // 2, screen_height // 2
        mouse_dx, mouse_dy = pg.mouse.get_rel()
        if mouse_dx:
            self.rotate_yaw(delta_x=mouse_dx * MOUSE_SENSITIVITY)
        if mouse_dy:
            self.rotate_pitch(delta_y=mouse_dy * MOUSE_SENSITIVITY)
        # Reset the mouse position to the center of the screen
        pg.mouse.set_pos(center_x, center_y)

    def keyboard_control(self):
        key_state = pg.key.get_pressed()
        vel = PLAYER_SPEED * self.app.delta_time
        if key_state[pg.K_w] & key_state[pg.K_LSHIFT]:
            self.move_forward(vel*2.5)
        if key_state[pg.K_s] & key_state[pg.K_LSHIFT]:
            self.move_back(vel*2.5)
        if key_state[pg.K_d] & key_state[pg.K_LSHIFT]:
            self.move_right(vel*2.5)
        if key_state[pg.K_a] & key_state[pg.K_LSHIFT]:
            self.move_left(vel*2.5)
        if key_state[pg.K_w]:
            self.move_forward(vel)
        if key_state[pg.K_s]:
            self.move_back(vel)
        if key_state[pg.K_d]:
            self.move_right(vel)
        if key_state[pg.K_a]:
            self.move_left(vel)
        if key_state[pg.K_q]:
            self.move_up(vel)
        if key_state[pg.K_e]:
            self.move_down(vel)
        if key_state[pg.K_SPACE]:
            self.move_jump(vel)
        if key_state[pg.K_1]:
            voxel_handler = self.app.scene.world.voxel_handler
            voxel_handler.set_voxel_type(SAND)
        if key_state[pg.K_2]:
            voxel_handler = self.app.scene.world.voxel_handler
            voxel_handler.set_voxel_type(GRASS)
        if key_state[pg.K_3]:
            voxel_handler = self.app.scene.world.voxel_handler
            voxel_handler.set_voxel_type(DIRT)
        if key_state[pg.K_4]:
            voxel_handler = self.app.scene.world.voxel_handler
            voxel_handler.set_voxel_type(STONE)
        if key_state[pg.K_5]:
            voxel_handler = self.app.scene.world.voxel_handler
            voxel_handler.set_voxel_type(SNOW)
        if key_state[pg.K_6]:
            voxel_handler = self.app.scene.world.voxel_handler
            voxel_handler.set_voxel_type(LEAVES)
        if key_state[pg.K_7]:
            voxel_handler = self.app.scene.world.voxel_handler
            voxel_handler.set_voxel_type(WOOD)
        if key_state[pg.K_8]:
            voxel_handler = self.app.scene.world.voxel_handler
            voxel_handler.set_voxel_type(GREEN_LEAF)