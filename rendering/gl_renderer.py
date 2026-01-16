# -*- coding: utf-8 -*-
"""
OpenGL Renderer - Blender-style GPU rendering
Uses ModernGL for professional quality rendering.
"""

import os
import math
import numpy as np
from typing import Optional, Tuple, List, Dict, Any

try:
    import moderngl
    HAS_MODERNGL = True
except ImportError:
    HAS_MODERNGL = False
    moderngl = None


# Shader paths
SHADER_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'shaders')


def load_shader(filename: str) -> str:
    """Load shader source from file"""
    filepath = os.path.join(SHADER_DIR, filename)
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            return f.read()
    return ""


class ShaderProgram:
    """Wrapper for ModernGL shader program with common operations"""

    def __init__(self, ctx: 'moderngl.Context', vertex_src: str, fragment_src: str):
        self.ctx = ctx
        self.program = ctx.program(
            vertex_shader=vertex_src,
            fragment_shader=fragment_src
        )
        self._uniforms: Dict[str, Any] = {}

    def __getitem__(self, name: str):
        """Get uniform by name"""
        if name not in self._uniforms:
            try:
                self._uniforms[name] = self.program[name]
            except KeyError:
                return None
        return self._uniforms[name]

    def set_uniform(self, name: str, value):
        """Set uniform value"""
        uniform = self[name]
        if uniform:
            uniform.value = value


class BackgroundRenderer:
    """
    Renders Blender-style gradient background with gamma correction.
    """

    VERTEX_SHADER = """
    #version 330

    in vec2 in_position;
    out vec2 uv;

    void main() {
        uv = in_position * 0.5 + 0.5;
        gl_Position = vec4(in_position, 0.0, 1.0);
    }
    """

    FRAGMENT_SHADER = """
    #version 330

    uniform vec3 colorTop;
    uniform vec3 colorBottom;
    uniform float gamma;
    uniform int backgroundType;

    in vec2 uv;
    out vec4 fragColor;

    vec3 toLinear(vec3 color) {
        return pow(color, vec3(gamma));
    }

    vec3 toGamma(vec3 color) {
        return pow(color, vec3(1.0 / gamma));
    }

    float dither(vec2 coord) {
        return fract(sin(dot(coord, vec2(12.9898, 78.233))) * 43758.5453) / 255.0;
    }

    void main() {
        vec3 color;

        if (backgroundType == 0) {
            color = colorBottom;
        }
        else if (backgroundType == 1) {
            vec3 top = toLinear(colorTop);
            vec3 bottom = toLinear(colorBottom);
            color = mix(bottom, top, uv.y);
            color = toGamma(color);
        }
        else if (backgroundType == 2) {
            vec2 center = vec2(0.5, 0.5);
            float dist = length(uv - center) * 1.414;
            vec3 top = toLinear(colorTop);
            vec3 bottom = toLinear(colorBottom);
            color = mix(top, bottom, clamp(dist, 0.0, 1.0));
            color = toGamma(color);
        }
        else {
            float checkerSize = 20.0;
            vec2 checker = floor(uv * checkerSize);
            float pattern = mod(checker.x + checker.y, 2.0);
            color = mix(colorBottom, colorTop, pattern);
        }

        color += dither(gl_FragCoord.xy) - 0.5/255.0;
        fragColor = vec4(color, 1.0);
    }
    """

    def __init__(self, ctx: 'moderngl.Context'):
        self.ctx = ctx

        # Create shader program
        self.program = ctx.program(
            vertex_shader=self.VERTEX_SHADER,
            fragment_shader=self.FRAGMENT_SHADER
        )

        # Full-screen quad vertices
        vertices = np.array([
            -1.0, -1.0,
             1.0, -1.0,
             1.0,  1.0,
            -1.0, -1.0,
             1.0,  1.0,
            -1.0,  1.0,
        ], dtype='f4')

        self.vbo = ctx.buffer(vertices)
        self.vao = ctx.simple_vertex_array(self.program, self.vbo, 'in_position')

        # Default colors (Blender-like soft blue gradient)
        self.color_top = (0.392, 0.537, 0.694)      # #647A9E - soft blue
        self.color_bottom = (0.169, 0.204, 0.251)   # #2B3440 - dark blue
        self.gamma = 2.2
        self.background_type = 1  # Gradient

    def set_colors(self, top: Tuple[float, float, float], bottom: Tuple[float, float, float]):
        """Set gradient colors (RGB 0-1)"""
        self.color_top = top
        self.color_bottom = bottom

    def set_blender_style(self):
        """Set Blender default viewport colors"""
        self.color_top = (0.392, 0.537, 0.694)
        self.color_bottom = (0.169, 0.204, 0.251)
        self.background_type = 1

    def set_freecad_style(self):
        """Set FreeCAD default viewport colors"""
        self.color_top = (0.235, 0.282, 0.353)   # Dark blue-gray
        self.color_bottom = (0.655, 0.706, 0.761) # Light gray-blue
        self.background_type = 1

    def set_light_style(self):
        """Light theme for 2D drawing"""
        self.color_top = (0.96, 0.96, 0.98)
        self.color_bottom = (0.88, 0.90, 0.94)
        self.background_type = 1

    def render(self):
        """Render background"""
        self.program['colorTop'].value = self.color_top
        self.program['colorBottom'].value = self.color_bottom
        self.program['gamma'].value = self.gamma
        self.program['backgroundType'].value = self.background_type

        self.vao.render(moderngl.TRIANGLES)


class GridRenderer:
    """
    Renders multi-level LOD grid with anti-aliased lines.
    Inspired by Blender's overlay grid.
    """

    VERTEX_SHADER = """
    #version 330

    in vec2 in_position;
    out vec2 world_pos;

    uniform mat4 viewProj;

    void main() {
        world_pos = in_position;
        gl_Position = viewProj * vec4(in_position, 0.0, 1.0);
    }
    """

    FRAGMENT_SHADER = """
    #version 330

    uniform vec3 gridColor;
    uniform vec3 axisColorX;
    uniform vec3 axisColorY;
    uniform float gridOpacity;
    uniform float zoom;
    uniform float baseGridSize;
    uniform float gridSubdivisions;
    uniform float lineWidth;
    uniform float axisLineWidth;

    in vec2 world_pos;
    out vec4 fragColor;

    float gridLine(float coord, float lineWidth, float gridSize) {
        float halfWidth = lineWidth * 0.5;
        float dist = abs(mod(coord + gridSize * 0.5, gridSize) - gridSize * 0.5);
        float aa = fwidth(coord) * 1.5;
        return 1.0 - smoothstep(halfWidth - aa, halfWidth + aa, dist);
    }

    float gridLevel(vec2 pos, float gridSize, float lineW) {
        float lineX = gridLine(pos.x, lineW, gridSize);
        float lineY = gridLine(pos.y, lineW, gridSize);
        return max(lineX, lineY);
    }

    float axisLine(float coord, float lineWidth) {
        float aa = fwidth(coord) * 1.5;
        return 1.0 - smoothstep(lineWidth * 0.5 - aa, lineWidth * 0.5 + aa, abs(coord));
    }

    void main() {
        float logZoom = log2(zoom);
        float level = floor(logZoom);
        float levelFract = fract(logZoom);

        float gridSize1 = baseGridSize * pow(gridSubdivisions, -level);
        float gridSize2 = gridSize1 / gridSubdivisions;

        float adaptiveLineWidth = lineWidth / zoom;
        float adaptiveAxisWidth = axisLineWidth / zoom;

        float grid1 = gridLevel(world_pos, gridSize1, adaptiveLineWidth);
        float grid2 = gridLevel(world_pos, gridSize2, adaptiveLineWidth * 0.7);
        float gridMajor = gridLevel(world_pos, gridSize1 * gridSubdivisions, adaptiveLineWidth * 1.5);

        float grid2Fade = smoothstep(0.0, 0.6, levelFract);
        float combinedGrid = max(grid1, grid2 * grid2Fade * 0.5);
        combinedGrid = max(combinedGrid, gridMajor);

        float xAxis = axisLine(world_pos.y, adaptiveAxisWidth);
        float yAxis = axisLine(world_pos.x, adaptiveAxisWidth);

        vec3 color = gridColor;
        float alpha = combinedGrid * gridOpacity;

        if (xAxis > 0.0) {
            color = mix(color, axisColorX, xAxis);
            alpha = max(alpha, xAxis * gridOpacity * 1.5);
        }
        if (yAxis > 0.0) {
            color = mix(color, axisColorY, yAxis);
            alpha = max(alpha, yAxis * gridOpacity * 1.5);
        }

        float distFade = 1.0 - smoothstep(gridSize1 * 50.0, gridSize1 * 100.0, length(world_pos));
        alpha *= distFade;

        if (alpha < 0.001) discard;

        fragColor = vec4(color, alpha);
    }
    """

    def __init__(self, ctx: 'moderngl.Context'):
        self.ctx = ctx

        self.program = ctx.program(
            vertex_shader=self.VERTEX_SHADER,
            fragment_shader=self.FRAGMENT_SHADER
        )

        # Large ground plane for grid
        size = 10000.0  # Large enough for most views
        vertices = np.array([
            -size, -size,
             size, -size,
             size,  size,
            -size, -size,
             size,  size,
            -size,  size,
        ], dtype='f4')

        self.vbo = ctx.buffer(vertices)
        self.vao = ctx.simple_vertex_array(self.program, self.vbo, 'in_position')

        # Default settings
        self.grid_color = (0.5, 0.5, 0.5)
        self.axis_color_x = (0.8, 0.2, 0.2)  # Red for X
        self.axis_color_y = (0.2, 0.8, 0.2)  # Green for Y
        self.grid_opacity = 0.3
        self.base_grid_size = 1.0  # 1 meter
        self.grid_subdivisions = 10.0
        self.line_width = 1.0
        self.axis_line_width = 2.0

    def render(self, view_proj_matrix: np.ndarray, zoom: float):
        """Render grid"""
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA

        self.program['viewProj'].write(view_proj_matrix.astype('f4').tobytes())
        self.program['gridColor'].value = self.grid_color
        self.program['axisColorX'].value = self.axis_color_x
        self.program['axisColorY'].value = self.axis_color_y
        self.program['gridOpacity'].value = self.grid_opacity
        self.program['zoom'].value = zoom
        self.program['baseGridSize'].value = self.base_grid_size
        self.program['gridSubdivisions'].value = self.grid_subdivisions
        self.program['lineWidth'].value = self.line_width
        self.program['axisLineWidth'].value = self.axis_line_width

        self.vao.render(moderngl.TRIANGLES)

        self.ctx.disable(moderngl.BLEND)


class ElementRenderer:
    """
    Renders 2D elements (walls, slabs, etc.) with optional 3D lighting.
    """

    VERTEX_SHADER_2D = """
    #version 330

    in vec2 in_position;
    in vec3 in_color;
    in float in_selected;

    out vec3 v_color;
    out float v_selected;

    uniform mat4 viewProj;

    void main() {
        v_color = in_color;
        v_selected = in_selected;
        gl_Position = viewProj * vec4(in_position, 0.0, 1.0);
    }
    """

    FRAGMENT_SHADER_2D = """
    #version 330

    in vec3 v_color;
    in float v_selected;

    out vec4 fragColor;

    uniform vec3 selectionColor;
    uniform float selectionMix;
    uniform float opacity;

    void main() {
        vec3 color = v_color;

        if (v_selected > 0.5) {
            color = mix(color, selectionColor, selectionMix);
        }

        fragColor = vec4(color, opacity);
    }
    """

    VERTEX_SHADER_3D = """
    #version 330

    in vec3 in_position;
    in vec3 in_normal;
    in vec3 in_color;
    in float in_selected;

    out vec3 v_position;
    out vec3 v_normal;
    out vec3 v_color;
    out float v_selected;

    uniform mat4 model;
    uniform mat4 view;
    uniform mat4 projection;
    uniform mat3 normalMatrix;

    void main() {
        vec4 worldPos = model * vec4(in_position, 1.0);
        v_position = worldPos.xyz;
        v_normal = normalize(normalMatrix * in_normal);
        v_color = in_color;
        v_selected = in_selected;

        gl_Position = projection * view * worldPos;
    }
    """

    FRAGMENT_SHADER_3D = """
    #version 330

    in vec3 v_position;
    in vec3 v_normal;
    in vec3 v_color;
    in float v_selected;

    out vec4 fragColor;

    uniform vec3 lightDir;
    uniform vec3 lightColor;
    uniform vec3 ambientColor;
    uniform float ambientIntensity;
    uniform vec3 cameraPos;
    uniform float shininess;
    uniform float specularStrength;
    uniform float opacity;
    uniform vec3 selectionColor;
    uniform float selectionMix;

    void main() {
        vec3 normal = normalize(v_normal);
        vec3 viewDir = normalize(cameraPos - v_position);

        vec3 baseColor = v_color;
        if (v_selected > 0.5) {
            baseColor = mix(baseColor, selectionColor, selectionMix);
        }

        vec3 ambient = ambientColor * ambientIntensity * baseColor;

        float diff = max(dot(normal, lightDir), 0.0);
        vec3 diffuse = lightColor * diff * baseColor;

        vec3 halfDir = normalize(lightDir + viewDir);
        float spec = pow(max(dot(normal, halfDir), 0.0), shininess);
        vec3 specular = lightColor * spec * specularStrength;

        vec3 result = ambient + diffuse + specular;

        float edgeFactor = 1.0 - max(dot(normal, viewDir), 0.0);
        edgeFactor = pow(edgeFactor, 2.0);
        result = mix(result, result * 0.7, edgeFactor * 0.3);

        result = pow(result, vec3(1.0/2.2));

        fragColor = vec4(result, opacity);
    }
    """

    def __init__(self, ctx: 'moderngl.Context', mode: str = '2d'):
        self.ctx = ctx
        self.mode = mode

        if mode == '3d':
            self.program = ctx.program(
                vertex_shader=self.VERTEX_SHADER_3D,
                fragment_shader=self.FRAGMENT_SHADER_3D
            )
        else:
            self.program = ctx.program(
                vertex_shader=self.VERTEX_SHADER_2D,
                fragment_shader=self.FRAGMENT_SHADER_2D
            )

        self.vbo = None
        self.vao = None

        # Default settings
        self.selection_color = (1.0, 0.5, 0.0)  # Orange
        self.selection_mix = 0.4
        self.opacity = 1.0

        # 3D lighting
        self.light_dir = (0.5, 0.5, 1.0)
        self.light_color = (1.0, 1.0, 1.0)
        self.ambient_color = (0.3, 0.3, 0.4)
        self.ambient_intensity = 0.4
        self.shininess = 32.0
        self.specular_strength = 0.3

    def update_geometry_2d(self, vertices: np.ndarray, colors: np.ndarray, selected: np.ndarray):
        """Update 2D geometry VBO"""
        if len(vertices) == 0:
            self.vbo = None
            self.vao = None
            return

        # Interleave data: x, y, r, g, b, selected
        n_vertices = len(vertices) // 2
        data = np.zeros(n_vertices * 6, dtype='f4')
        data[0::6] = vertices[0::2]  # x
        data[1::6] = vertices[1::2]  # y
        data[2::6] = colors[0::3]    # r
        data[3::6] = colors[1::3]    # g
        data[4::6] = colors[2::3]    # b
        data[5::6] = selected        # selected

        if self.vbo:
            self.vbo.release()
        self.vbo = self.ctx.buffer(data.tobytes())

        if self.vao:
            self.vao.release()
        self.vao = self.ctx.vertex_array(
            self.program,
            [(self.vbo, '2f 3f 1f', 'in_position', 'in_color', 'in_selected')]
        )

    def update_geometry_3d(
        self,
        vertices: np.ndarray,
        normals: np.ndarray,
        colors: np.ndarray,
        selected: np.ndarray
    ):
        """Update 3D geometry VBO"""
        if len(vertices) == 0:
            self.vbo = None
            self.vao = None
            return

        # Interleave: x, y, z, nx, ny, nz, r, g, b, selected
        n_vertices = len(vertices) // 3
        data = np.zeros(n_vertices * 10, dtype='f4')
        data[0::10] = vertices[0::3]   # x
        data[1::10] = vertices[1::3]   # y
        data[2::10] = vertices[2::3]   # z
        data[3::10] = normals[0::3]    # nx
        data[4::10] = normals[1::3]    # ny
        data[5::10] = normals[2::3]    # nz
        data[6::10] = colors[0::3]     # r
        data[7::10] = colors[1::3]     # g
        data[8::10] = colors[2::3]     # b
        data[9::10] = selected         # selected

        if self.vbo:
            self.vbo.release()
        self.vbo = self.ctx.buffer(data.tobytes())

        if self.vao:
            self.vao.release()
        self.vao = self.ctx.vertex_array(
            self.program,
            [(self.vbo, '3f 3f 3f 1f', 'in_position', 'in_normal', 'in_color', 'in_selected')]
        )

    def render_2d(self, view_proj_matrix: np.ndarray):
        """Render 2D elements"""
        if not self.vao:
            return

        self.program['viewProj'].write(view_proj_matrix.astype('f4').tobytes())
        self.program['selectionColor'].value = self.selection_color
        self.program['selectionMix'].value = self.selection_mix
        self.program['opacity'].value = self.opacity

        self.vao.render(moderngl.TRIANGLES)

    def render_3d(
        self,
        model_matrix: np.ndarray,
        view_matrix: np.ndarray,
        projection_matrix: np.ndarray,
        camera_pos: Tuple[float, float, float]
    ):
        """Render 3D elements with lighting"""
        if not self.vao:
            return

        # Calculate normal matrix
        model_3x3 = model_matrix[:3, :3]
        normal_matrix = np.linalg.inv(model_3x3).T

        self.program['model'].write(model_matrix.astype('f4').tobytes())
        self.program['view'].write(view_matrix.astype('f4').tobytes())
        self.program['projection'].write(projection_matrix.astype('f4').tobytes())
        self.program['normalMatrix'].write(normal_matrix.astype('f4').tobytes())

        self.program['lightDir'].value = self.light_dir
        self.program['lightColor'].value = self.light_color
        self.program['ambientColor'].value = self.ambient_color
        self.program['ambientIntensity'].value = self.ambient_intensity
        self.program['cameraPos'].value = camera_pos
        self.program['shininess'].value = self.shininess
        self.program['specularStrength'].value = self.specular_strength
        self.program['opacity'].value = self.opacity
        self.program['selectionColor'].value = self.selection_color
        self.program['selectionMix'].value = self.selection_mix

        self.ctx.enable(moderngl.DEPTH_TEST)
        self.vao.render(moderngl.TRIANGLES)
        self.ctx.disable(moderngl.DEPTH_TEST)


class GLRenderer:
    """
    Main renderer combining background, grid, and elements.
    """

    def __init__(self, ctx: 'moderngl.Context'):
        self.ctx = ctx

        self.background = BackgroundRenderer(ctx)
        self.grid = GridRenderer(ctx)
        self.elements_2d = ElementRenderer(ctx, '2d')
        self.elements_3d = ElementRenderer(ctx, '3d')

        # View matrices
        self._view_proj_2d = np.eye(4, dtype='f4')
        self._model = np.eye(4, dtype='f4')
        self._view = np.eye(4, dtype='f4')
        self._projection = np.eye(4, dtype='f4')

    def set_viewport(self, width: int, height: int):
        """Set viewport size"""
        self.ctx.viewport = (0, 0, width, height)

    def clear(self, color: Tuple[float, float, float, float] = (0, 0, 0, 1)):
        """Clear framebuffer"""
        self.ctx.clear(*color)

    def render_background(self):
        """Render background gradient"""
        self.background.render()

    def render_grid_2d(self, scale: float, offset_x: float, offset_y: float, width: int, height: int):
        """Render 2D grid"""
        # Create orthographic view-projection matrix
        view_proj = self._create_ortho_matrix(scale, offset_x, offset_y, width, height)
        self.grid.render(view_proj, scale)

    def render_elements_2d(self, scale: float, offset_x: float, offset_y: float, width: int, height: int):
        """Render 2D elements"""
        view_proj = self._create_ortho_matrix(scale, offset_x, offset_y, width, height)
        self.elements_2d.render_2d(view_proj)

    def _create_ortho_matrix(self, scale: float, offset_x: float, offset_y: float, width: int, height: int) -> np.ndarray:
        """Create orthographic view-projection matrix"""
        # Convert from world to screen coordinates
        # World coordinate (0,0) should appear at (offset_x, offset_y)
        # Scale determines pixels per meter

        # Orthographic projection
        left = -offset_x / scale
        right = (width - offset_x) / scale
        bottom = -(height - offset_y) / scale
        top = offset_y / scale

        # Orthographic matrix
        mat = np.eye(4, dtype='f4')
        mat[0, 0] = 2.0 / (right - left)
        mat[1, 1] = 2.0 / (top - bottom)
        mat[2, 2] = -1.0
        mat[0, 3] = -(right + left) / (right - left)
        mat[1, 3] = -(top + bottom) / (top - bottom)

        return mat

    @staticmethod
    def create_perspective_matrix(fov: float, aspect: float, near: float, far: float) -> np.ndarray:
        """Create perspective projection matrix"""
        f = 1.0 / math.tan(math.radians(fov) / 2.0)
        mat = np.zeros((4, 4), dtype='f4')
        mat[0, 0] = f / aspect
        mat[1, 1] = f
        mat[2, 2] = (far + near) / (near - far)
        mat[2, 3] = (2 * far * near) / (near - far)
        mat[3, 2] = -1.0
        return mat

    @staticmethod
    def create_look_at_matrix(eye: np.ndarray, target: np.ndarray, up: np.ndarray) -> np.ndarray:
        """Create view matrix from camera position"""
        f = target - eye
        f = f / np.linalg.norm(f)

        u = up / np.linalg.norm(up)
        s = np.cross(f, u)
        s = s / np.linalg.norm(s)

        u = np.cross(s, f)

        mat = np.eye(4, dtype='f4')
        mat[0, :3] = s
        mat[1, :3] = u
        mat[2, :3] = -f
        mat[0, 3] = -np.dot(s, eye)
        mat[1, 3] = -np.dot(u, eye)
        mat[2, 3] = np.dot(f, eye)

        return mat
