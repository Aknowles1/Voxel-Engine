import pygame as pg
import glm
from camera import Camera
from settings import *

GRAVITY = 0.1
PLAYER_HALF_WIDTH = 0.2
PLAYER_HEIGHT = 1.8
HALF_HEIGHT = PLAYER_HEIGHT * 0.5
JUMP_VELOCITY = 0.05
EYE_OFFSET = glm.vec3(0, HALF_HEIGHT * 0.9, 0)


# Let’s reduce the step height to half a block
STEP_OFFSET = 1


class Player(Camera):
    def __init__(self, app, position=PLAYER_POS, yaw=-90, pitch=0):
        self.app = app
        super().__init__(position, yaw, pitch)

        self.velocity = glm.vec3(0, 0, 0)
        self.on_ground = False
        self.gravity = True

    def get_camera_position(self):
        return self.position + EYE_OFFSET

    def update(self):
        self.keyboard_control()
        self.mouse_control()
        if self.gravity:
            self.apply_gravity()
        super().update()

    def apply_gravity(self):
        dt = self.app.delta_time * 0.001
        if not self.on_ground:
            self.velocity.y -= GRAVITY * dt

        new_position = glm.vec3(self.position)
        new_position.y += self.velocity.y

        if self.check_bounding_box_collision(new_position):
            # partial snap
            sign = glm.sign(self.velocity.y)
            step_size = 0.02
            test_y = self.position.y

            while True:
                test_y += sign * step_size
                test_pos = glm.vec3(self.position.x, test_y, self.position.z)
                if self.check_bounding_box_collision(test_pos):
                    # revert
                    test_y -= sign * step_size
                    break
                # break if we've reached or passed the intended new_position.y
                if (sign < 0 and test_y <= new_position.y) or (
                    sign > 0 and test_y >= new_position.y
                ):
                    break

            self.position.y = test_y
            if sign < 0:  # landed
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
                voxel_handler.set_voxel()
                voxel_handler.switch_mode()

    def move_and_slide(self, direction, velocity):
        """
        Moves the player horizontally in separate passes for X and Z,
        allowing 'sliding' around obstacles.
        Returns True if any movement happened, False if fully blocked.
        """
        old_position = glm.vec3(self.position)

        # 1) Move along X
        self.position.x += direction.x * velocity
        if self.check_bounding_box_collision(self.position):
            self.position.x = old_position.x  # revert if collision

        # 2) Move along Z
        self.position.z += direction.z * velocity
        if self.check_bounding_box_collision(self.position):
            self.position.z = old_position.z  # revert if collision

        # Check if we moved at all
        moved_dist = glm.distance(old_position, self.position)
        return moved_dist > 0.0001

    def move(self, direction, velocity):
        """
        Attempts movement in 'direction' * velocity, with step-up logic
        if the forward path is blocked.
        """

        # 1) First, try a normal move & slide
        if self.move_and_slide(direction, velocity):
            # we successfully moved at least some of the distance
            return True

        # 2) If we get here, movement is fully blocked. Attempt step-up if on ground
        if not self.on_ground:
            return False

        # 3) (Same logic as before) -> check if there's actually a block in front
        if not self.is_block_in_front(direction, velocity):
            return False

        current_foot_y = self.position.y - HALF_HEIGHT
        front_floor_y = self.get_front_floor_height(direction, velocity)
        slope = front_floor_y - current_foot_y

        if 0 < slope <= STEP_OFFSET:
            # Try stepping
            step_pos = glm.vec3(self.position)
            step_pos.y += slope

            # Check overhead collision
            if self.check_bounding_box_collision(step_pos):
                return False

            # Move horizontally from stepped position, again with move_and_slide
            old_y = self.position.y
            self.position.y += slope
            if not self.move_and_slide(direction, velocity):
                # revert to old Y
                self.position.y = old_y
                return False

            return True

        # 4) If slope <= 0 or slope > STEP_OFFSET -> blocked
        return False

    def is_block_in_front(self, direction, velocity):
        """
        Checks if there's a solid block at foot level directly in front.
        This helps confirm the collision is from an actual block in front
        rather than an angled corner or diagonal brush.
        """
        voxel_handler = self.app.scene.world.voxel_handler

        # For robustness, check multiple corners at foot level in front
        foot_level_y = self.position.y - HALF_HEIGHT
        foot_corners = [
            glm.vec3(-PLAYER_HALF_WIDTH, 0, -PLAYER_HALF_WIDTH),
            glm.vec3(PLAYER_HALF_WIDTH, 0, -PLAYER_HALF_WIDTH),
            glm.vec3(PLAYER_HALF_WIDTH, 0, PLAYER_HALF_WIDTH),
            glm.vec3(-PLAYER_HALF_WIDTH, 0, PLAYER_HALF_WIDTH),
        ]

        for corner in foot_corners:
            corner_world = (
                glm.vec3(self.position.x, foot_level_y, self.position.z) + corner
            )
            corner_in_front = corner_world + direction * velocity
            if voxel_handler.is_colliding(corner_in_front):
                # Return True if we find a collision in front at foot level
                return True

        return False

    def get_front_floor_height(self, direction, velocity):
        """
        Returns the Y coordinate of the floor (block top) in front of the player,
        at foot-level XZ + direction * velocity. If no block is found,
        returns the player's current foot level (meaning it's flat/downhill).

        This requires a function like 'voxel_handler.get_floor_height(x, z)'
        which you would implement to look up or raycast the top surface.
        """
        voxel_handler = self.app.scene.world.voxel_handler

        # XZ in front
        foot_level_pos = glm.vec3(
            self.position.x, self.position.y - HALF_HEIGHT, self.position.z
        )
        front_xz = foot_level_pos + direction * velocity
        x, z = front_xz.x, front_xz.z

        # Hypothetical function: get the terrain's top Y at (x, z)
        # If your voxel system doesn't have such a function,
        # you'll need to implement a raycast or block lookup yourself.
        floor_y = voxel_handler.get_floor_height(x, z)

        # If we fail to find a block (e.g. air), return current foot level
        if floor_y is None:
            return foot_level_pos.y

        return floor_y

    def check_bounding_box_collision(self, test_pos):
        voxel_handler = self.app.scene.world.voxel_handler

        corners = [
            glm.vec3(-PLAYER_HALF_WIDTH, -HALF_HEIGHT, -PLAYER_HALF_WIDTH),
            glm.vec3(PLAYER_HALF_WIDTH, -HALF_HEIGHT, -PLAYER_HALF_WIDTH),
            glm.vec3(PLAYER_HALF_WIDTH, -HALF_HEIGHT, PLAYER_HALF_WIDTH),
            glm.vec3(-PLAYER_HALF_WIDTH, -HALF_HEIGHT, PLAYER_HALF_WIDTH),
            glm.vec3(-PLAYER_HALF_WIDTH, HALF_HEIGHT, -PLAYER_HALF_WIDTH),
            glm.vec3(PLAYER_HALF_WIDTH, HALF_HEIGHT, -PLAYER_HALF_WIDTH),
            glm.vec3(PLAYER_HALF_WIDTH, HALF_HEIGHT, PLAYER_HALF_WIDTH),
            glm.vec3(-PLAYER_HALF_WIDTH, HALF_HEIGHT, PLAYER_HALF_WIDTH),
        ]

        for corner_offset in corners:
            corner_world_pos = test_pos + corner_offset
            if voxel_handler.is_colliding(corner_world_pos):
                return True
        return False

    # Movement helpers
    def move_left(self, velocity):
        self.move(-self.right, velocity)

    def move_right(self, velocity):
        self.move(self.right, velocity)

    def move_up(self, velocity):
        if not self.gravity:
            self.position += self.up * velocity

    def move_down(self, velocity):
        if not self.gravity:
            self.position -= self.up * velocity

    def move_forward(self, velocity):
        self.move(self.forward, velocity)

    def move_back(self, velocity):
        self.move(-self.forward, velocity)

    def move_jump(self, velocity):
        if self.on_ground:
            self.velocity.y = JUMP_VELOCITY
            self.on_ground = False
            # small upward nudge
            self.move(self.up, velocity)

    def mouse_control(self):
        screen_w, screen_h = pg.display.get_surface().get_size()
        center_x, center_y = screen_w // 2, screen_h // 2

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

        # Toggle gravity
        if key_state[pg.K_g]:
            self.gravity = not self.gravity


def snap_to_ground(player, step=0.1, max_iterations=256):
    """
    Utility function to ensure the player's bounding box
    is above terrain at spawn. Moves up until no collision.
    """
    count = 0
    while count < max_iterations:
        if not player.check_bounding_box_collision(player.position):
            break
        player.position.y += step
        count += 1
