#version 330 core
layout (location = 0) in vec2 in_pos;
layout (location = 1) in vec2 in_tex;

uniform mat4 u_proj;
uniform vec2 u_offset;
uniform vec2 u_scale;

uniform bool u_use_texture = true;

out vec2 v_texcoord;
out float v_use_texture; 

void main()
{
    vec2 pos = in_pos * u_scale + u_offset;
    gl_Position = u_proj * vec4(pos, 0.0, 1.0);
    v_texcoord = in_tex;
    v_use_texture = u_use_texture ? 1.0 : 0.0;
}
