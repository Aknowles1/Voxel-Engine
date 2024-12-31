import pygame as pg
import glm
from camera import Camera
from settings import *

# Gravity constant. Tweak to your liking (larger => faster fall).
GRAVITY = 9.81

# Optional: define some constants for player size
PLAYER_HALF_WIDTH = 0.3  # half the width (radius)
PLAYER_HEIGHT = 1.8      # total height

class Player(Camera):
    def __init__(self, app, position=PLAYER_POS, yaw=-90, pitch=0):
        self.app = app
        self.player_voxel = 0
        super().__init__(position, yaw, pitch)

        self.velocity = glm.vec3(0, 0, 0)   # store current velocity
        self.on_ground = False             # whether the player is on the ground

    def update(self):
        self.keyboard_control()
        self.mouse_control()
        # # apply gravity
        # self.apply_gravity()
        super().update()

    # def apply_gravity(self):
    #     """
    #     Applies a simple gravity each frame, then tries to move the player down.
    #     If there's a collision, we stand on the block and reset vertical velocity.
    #     """
    #     dt = self.app.delta_time * 0.001  # if your delta_time is in milliseconds

    #     # Only apply gravity if not on the ground
    #     if not self.on_ground:
    #         self.velocity.y -= GRAVITY * dt

    #     # Attempt to move by velocity.y in Y-axis
    #     new_position = glm.vec3(self.position)
    #     new_position.y += self.velocity.y

    #     # If bounding-box collision occurs, stand on block and reset velocity
    #     if self.check_bounding_box_collision(new_position):
    #         # We hit something. Move as close to ground as possible:
    #         #   Approach #1: simpler "Minecraft snap": set on_ground, zero velocity
    #         #   Approach #2: partial move until just above collision
    #         self.on_ground = True
    #         self.velocity.y = 0.0
    #     else:
    #         self.on_ground = False
    #         self.position.y = new_position.y

    def handle_event(self, event):
        # adding and removing voxels with clicks
        if event.type == pg.MOUSEBUTTONDOWN:
            voxel_handler = self.app.scene.world.voxel_handler
            if event.button == 1:
                voxel_handler.set_voxel()
            if event.button == 3:
                voxel_handler.switch_mode()

    def move(self, direction, velocity):
        """
        Move the player using a bounding-box approach:
        1. Build a test position
        2. Check if that bounding box collides
        3. If not, actually update self.position
        """
        new_position = self.position + direction * velocity

        print("Potential new position: " + str(new_position))

        # If the bounding box at new_position is colliding, do NOT move
        if self.check_bounding_box_collision(new_position):
            return False

        self.position = new_position
        return True


    def check_bounding_box_collision(self, test_pos):
        """
        Checks collisions for all corners of a bounding box that is
        PLAYER_HEIGHT tall and 2*PLAYER_HALF_WIDTH wide.
        Returns True if any corner collides, else False.
        """
        voxel_handler = self.app.scene.world.voxel_handler

        corners = [
            glm.vec3(-PLAYER_HALF_WIDTH,    0.0,             -PLAYER_HALF_WIDTH),
            glm.vec3( PLAYER_HALF_WIDTH,    0.0,             -PLAYER_HALF_WIDTH),
            glm.vec3( PLAYER_HALF_WIDTH,    0.0,              PLAYER_HALF_WIDTH),
            glm.vec3(-PLAYER_HALF_WIDTH,    0.0,              PLAYER_HALF_WIDTH),
            glm.vec3(-PLAYER_HALF_WIDTH, PLAYER_HEIGHT,     -PLAYER_HALF_WIDTH),
            glm.vec3( PLAYER_HALF_WIDTH, PLAYER_HEIGHT,     -PLAYER_HALF_WIDTH),
            glm.vec3( PLAYER_HALF_WIDTH, PLAYER_HEIGHT,      PLAYER_HALF_WIDTH),
            glm.vec3(-PLAYER_HALF_WIDTH, PLAYER_HEIGHT,      PLAYER_HALF_WIDTH),
        ]

        for corner_offset in corners:
            corner_world_pos = test_pos + corner_offset
            if voxel_handler.is_colliding(corner_world_pos):
                return True

        return False

    def move_left(self, velocity):
        self.move(-self.right, velocity)

    def move_right(self, velocity):
        self.move(self.right, velocity)

    def move_up(self, velocity):
        self.move(self.up, velocity)

    def move_down(self, velocity):
        self.move(-self.up, velocity)

    def move_forward(self, velocity):
        self.move(self.forward, velocity)

    def move_back(self, velocity):
        self.move(-self.forward, velocity)

    def move_jump(self, velocity):
        if self.on_ground:
            self.velocity.y = 1.5  # or any jump impulse
            self.on_ground = False
            self.move(self.up, velocity)

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
            self.move_forward(vel * 2.5)
        if key_state[pg.K_s] & key_state[pg.K_LSHIFT]:
            self.move_back(vel * 2.5)
        if key_state[pg.K_d] & key_state[pg.K_LSHIFT]:
            self.move_right(vel * 2.5)
        if key_state[pg.K_a] & key_state[pg.K_LSHIFT]:
            self.move_left(vel * 2.5)
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
