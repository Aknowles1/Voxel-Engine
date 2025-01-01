#version 330 core
in vec2 v_texcoord;
in float v_use_texture;
out vec4 fragColor;

uniform sampler2D u_texture;
uniform vec4 u_color;      
uniform bool u_use_texture; 

void main()
{
    if (v_use_texture > 0.5) {
        fragColor = texture(u_texture, v_texcoord);
    } else {
        fragColor = u_color;
    }
}
