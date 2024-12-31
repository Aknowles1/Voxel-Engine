import pygame as pg
import glm
from camera import Camera
from settings import *

GRAVITY = 2
PLAYER_HALF_WIDTH = 0.3
PLAYER_HEIGHT = 3.5
HALF_HEIGHT = PLAYER_HEIGHT * 0.5
JUMP_VELOCITY = 1.5

class Player(Camera):
    def __init__(self, app, position=PLAYER_POS, yaw=-90, pitch=0):
        """
        We'll treat 'position' as the center of our bounding box.
        You can place the camera's 'eye' above center if you'd like.
        """
        self.app = app
        super().__init__(position, yaw, pitch)
        self.velocity = glm.vec3(0, 0, 0)
        self.on_ground = False

    def update(self):
        self.keyboard_control()
        self.mouse_control()
        self.apply_gravity()
        super().update()

    def apply_gravity(self):
        dt = self.app.delta_time * 0.001
        if not self.on_ground:
            self.velocity.y -= GRAVITY * dt

        new_position = glm.vec3(self.position)
        new_position.y += self.velocity.y

        # partial snap approach
        if self.check_bounding_box_collision(new_position):
            sign = glm.sign(self.velocity.y)
            step_size = 0.02
            test_y = self.position.y

            while True:
                test_y += sign * step_size
                test_pos = glm.vec3(self.position.x, test_y, self.position.z)

                if self.check_bounding_box_collision(test_pos):
                    test_y -= sign * step_size
                    break

                # if we passed new_position.y, stop
                if (sign < 0 and test_y <= new_position.y) or (sign > 0 and test_y >= new_position.y):
                    break

            self.position.y = test_y
            # landed if we were moving downward
            if sign < 0:
                self.on_ground = True
                self.velocity.y = 0.0
        else:
            self.on_ground = False
            self.position.y = new_position.y

    def handle_event(self, event):
        if event.type == pg.MOUSEBUTTONDOWN:
            voxel_handler = self.app.scene.world.voxel_handler
            if event.button == 1:
                voxel_handler.set_voxel()
            elif event.button == 3:
                voxel_handler.switch_mode()

    def move(self, direction, velocity):
        new_position = self.position + direction * velocity
        if self.check_bounding_box_collision(new_position):
            return False
        self.position = new_position
        return True

    def check_bounding_box_collision(self, test_pos):
        voxel_handler = self.app.scene.world.voxel_handler
        # bounding box corners around 'test_pos' as center
        corners = [
            glm.vec3(-PLAYER_HALF_WIDTH, -HALF_HEIGHT, -PLAYER_HALF_WIDTH),
            glm.vec3( PLAYER_HALF_WIDTH, -HALF_HEIGHT, -PLAYER_HALF_WIDTH),
            glm.vec3( PLAYER_HALF_WIDTH, -HALF_HEIGHT,  PLAYER_HALF_WIDTH),
            glm.vec3(-PLAYER_HALF_WIDTH, -HALF_HEIGHT,  PLAYER_HALF_WIDTH),

            glm.vec3(-PLAYER_HALF_WIDTH,  HALF_HEIGHT, -PLAYER_HALF_WIDTH),
            glm.vec3( PLAYER_HALF_WIDTH,  HALF_HEIGHT, -PLAYER_HALF_WIDTH),
            glm.vec3( PLAYER_HALF_WIDTH,  HALF_HEIGHT,  PLAYER_HALF_WIDTH),
            glm.vec3(-PLAYER_HALF_WIDTH,  HALF_HEIGHT,  PLAYER_HALF_WIDTH),
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
            self.velocity.y = JUMP_VELOCITY
            self.on_ground = False
            self.move(self.up, velocity)

    def mouse_control(self):
        screen_width, screen_height = pg.display.get_surface().get_size()
        center_x, center_y = screen_width // 2, screen_height // 2

        mouse_dx, mouse_dy = pg.mouse.get_rel()
        if mouse_dx:
            self.rotate_yaw(delta_x=mouse_dx * MOUSE_SENSITIVITY)
        if mouse_dy:
            self.rotate_pitch(delta_y=mouse_dy * MOUSE_SENSITIVITY)

        pg.mouse.set_pos(center_x, center_y)

    def keyboard_control(self):
        key_state = pg.key.get_pressed()
        vel = PLAYER_SPEED * self.app.delta_time
        sprint_mult = 2.5 if key_state[pg.K_LSHIFT] else 1.0

        if key_state[pg.K_w]:
            self.move_forward(vel * sprint_mult)
        if key_state[pg.K_s]:
            self.move_back(vel * sprint_mult)
        if key_state[pg.K_d]:
            self.move_right(vel * sprint_mult)
        if key_state[pg.K_a]:
            self.move_left(vel * sprint_mult)
        if key_state[pg.K_q]:
            self.move_up(vel)
        if key_state[pg.K_e]:
            self.move_down(vel)
        if key_state[pg.K_SPACE]:
            self.move_jump(vel)

        # Hotkeys for voxel types
        voxel_handler = self.app.scene.world.voxel_handler
        if key_state[pg.K_1]:
            voxel_handler.set_voxel_type(SAND)
        elif key_state[pg.K_2]:
            voxel_handler.set_voxel_type(GRASS)
        elif key_state[pg.K_3]:
            voxel_handler.set_voxel_type(DIRT)
        elif key_state[pg.K_4]:
            voxel_handler.set_voxel_type(STONE)
        elif key_state[pg.K_5]:
            voxel_handler.set_voxel_type(SNOW)
        elif key_state[pg.K_6]:
            voxel_handler.set_voxel_type(LEAVES)
        elif key_state[pg.K_7]:
            voxel_handler.set_voxel_type(WOOD)
        elif key_state[pg.K_8]:
            voxel_handler.set_voxel_type(GREEN_LEAF)


def snap_to_ground(player, step=0.1, max_iterations=256):
    """
    Utility function to ensure the player's bounding box
    is above the terrain at spawn. Moves upward until no collision.
    """
    count = 0
    while count < max_iterations:
        if not player.check_bounding_box_collision(player.position):
            break
        player.position.y += step
        count += 1
