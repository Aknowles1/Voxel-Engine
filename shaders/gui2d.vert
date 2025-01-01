#version 330 core

layout (location = 0) in vec2 in_pos;  // (x,y) in "normalized" quad space
layout (location = 1) in vec2 in_tex;  // (u,v) for the texture

uniform mat4 u_proj;        // Orthographic projection
uniform vec2 u_offset;      // Where we place this quad in screen coords
uniform vec2 u_scale;       // Size (width, height) in screen coords

out vec2 v_texcoord;

void main() {
    // Scale + translate the quad from [0..1] into actual screen coords
    vec2 pos = in_pos * u_scale + u_offset;

    // Convert to clip space via the orthographic matrix
    gl_Position = u_proj * vec4(pos, 0.0, 1.0);
    v_texcoord = in_tex;
}
