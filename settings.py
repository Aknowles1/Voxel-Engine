from numba import njit
import numpy as np
import math
import glm

# Game Resolution
WIN_RES = glm.vec2(1600,900)

# Camera
ASPECT_RATIO = WIN_RES.x / WIN_RES.y
FOV_DEG = 50
V_FOV = glm.radians(FOV_DEG)
H_FOV = 2 * math.atan(math.tan(V_FOV * 0.5)* ASPECT_RATIO)
NEAR = 0.1
FAR = 2000.0
PITCH_MAX = glm.radians(89)

#Player
PLAYER_SPEED = 0.005
PLAYER_ROT_SPEED = 0.003
PLAYER_POS = glm.vec3(0,0,1)
MOUSE_SENSITIVTY = 0.002

#Colours
BG_COLOUR = glm.vec3(0.1,0.16,0.25)