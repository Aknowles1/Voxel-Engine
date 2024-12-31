import pygame as pg
import glm
from camera import Camera
from settings import *

# Optional: define some constants for player size
PLAYER_HALF_WIDTH = 0.3  # half the width (radius)
PLAYER_HEIGHT = 1.8      # total height

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

    def move(self, direction, velocity):
        """
        Attempts to move the player in the given direction.
        We use a bounding-box approach for collisions: we build a 'test position'
        and check if that bounding box collides with voxels.
        """
        new_position = self.position + direction * velocity
        if not self.check_bounding_box_collision(new_position):
            self.position = new_position
        self.check_ground_collision()  # optional snapping logic

    def check_bounding_box_collision(self, test_pos):
        """
        Checks collisions for all corners of a bounding box that is
        PLAYER_HEIGHT tall and 2 * PLAYER_HALF_WIDTH wide.
        Returns True if *any* corner collides, else False.
        """
        voxel_handler = self.app.scene.world.voxel_handler

        # The bounding box's "bottom" is at test_pos.y (feet),
        # and the "top" is at test_pos.y + PLAYER_HEIGHT (head).
        # The left/right and front/back edges are offset by PLAYER_HALF_WIDTH.

        # Collect corners of the bounding box (bottom + top).
        corners = [
            # Bottom corners (y = 0)
            glm.vec3(-PLAYER_HALF_WIDTH, 0.0, -PLAYER_HALF_WIDTH),
            glm.vec3( PLAYER_HALF_WIDTH, 0.0, -PLAYER_HALF_WIDTH),
            glm.vec3( PLAYER_HALF_WIDTH, 0.0,  PLAYER_HALF_WIDTH),
            glm.vec3(-PLAYER_HALF_WIDTH, 0.0,  PLAYER_HALF_WIDTH),

            # Top corners (y = PLAYER_HEIGHT)
            glm.vec3(-PLAYER_HALF_WIDTH, PLAYER_HEIGHT, -PLAYER_HALF_WIDTH),
            glm.vec3( PLAYER_HALF_WIDTH, PLAYER_HEIGHT, -PLAYER_HALF_WIDTH),
            glm.vec3( PLAYER_HALF_WIDTH, PLAYER_HEIGHT,  PLAYER_HALF_WIDTH),
            glm.vec3(-PLAYER_HALF_WIDTH, PLAYER_HEIGHT,  PLAYER_HALF_WIDTH),
        ]

        # Test each corner in voxel space.
        for corner_offset in corners:
            corner_world_pos = test_pos + corner_offset
            if voxel_handler.is_colliding(corner_world_pos):
                return True  # collide if ANY corner hits a filled voxel

        return False  # no collision if all corners are free

    def check_ground_collision(self):
        """
        Simple snap-to-ground example. We move 1 block down from the player's
        current position and see if that collisions. If so, we round the player's y.
        """
        voxel_handler = self.app.scene.world.voxel_handler
        # We'll check the bottom corners of the bounding box
        # but offset downward by 0.5 or 1.0 to see if there's ground below.
        bottom_corners = [
            glm.vec3(-PLAYER_HALF_WIDTH, -0.9, -PLAYER_HALF_WIDTH),
            glm.vec3( PLAYER_HALF_WIDTH, -0.9, -PLAYER_HALF_WIDTH),
            glm.vec3( PLAYER_HALF_WIDTH, -0.9,  PLAYER_HALF_WIDTH),
            glm.vec3(-PLAYER_HALF_WIDTH, -0.9,  PLAYER_HALF_WIDTH),
        ]
        collision_below = False
        for corner_offset in bottom_corners:
            corner_world_pos = self.position + corner_offset
            if voxel_handler.is_colliding(corner_world_pos):
                collision_below = True
                break

        if collision_below:
            # Snap the player's Y to an integer. This is an artificial "Minecraft-like" snap.
            self.position.y = round(self.position.y)

    def move(self, direction, velocity):
        displacement = direction * velocity

        # Move along X
        old_x = self.position.x
        self.position.x += displacement.x
        if self.check_bounding_box_collision(self.position):
            self.position.x = old_x

        # Move along Z
        old_z = self.position.z
        self.position.z += displacement.z
        if self.check_bounding_box_collision(self.position):
            self.position.z = old_z

        # Move along Y
        old_y = self.position.y
        self.position.y += displacement.y
        if self.check_bounding_box_collision(self.position):
            self.position.y = old_y



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
