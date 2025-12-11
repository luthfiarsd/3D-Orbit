import moderngl
import moderngl_window as mglw
from pyrr import Matrix44
from PIL import Image
from pathlib import Path
import numpy as np
import math


class RotatingPlanet(mglw.WindowConfig):
    """
    Kelas utama untuk menampilkan simulasi tata surya 3D dengan planet-planet yang berputar.
    Mendukung kontrol kamera dengan mouse drag dan zoom dengan scroll.
    """

    gl_version = (3, 3)
    title = "3D Rotating Planet with Orbit"
    window_size = (800, 600)
    resource_dir = "."

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ctx.enable(moderngl.DEPTH_TEST)

        self.sphere = mglw.geometry.sphere(radius=1.0, sectors=64, rings=32)

        # Load Sun texture
        sun_path = Path(self.resource_dir) / "assets" / "2ksun.jpg"
        sun_img = Image.open(str(sun_path)).transpose(Image.FLIP_TOP_BOTTOM)
        self.sun_texture = self.ctx.texture(
            sun_img.size, 3, sun_img.convert("RGB").tobytes()
        )
        self.sun_texture.build_mipmaps()

        self.program = self.ctx.program(
            vertex_shader="""
                #version 330
                uniform mat4 mvp;
                in vec3 in_position;
                in vec2 in_texcoord_0;
                out vec2 uv;
                void main() {
                    gl_Position = mvp * vec4(in_position, 1.0);
                    uv = in_texcoord_0;
                }
            """,
            fragment_shader="""
                #version 330
                uniform sampler2D texture0;
                in vec2 uv;
                out vec4 fragColor;
                void main() {
                    fragColor = texture(texture0, uv);
                }
            """,
        )

        self.mvp = self.program["mvp"]
        self.program["texture0"] = 0
        self.time = 0.0

        planet_defs = [
            ("Mercury", "2kmercury.jpg", 2.5, 4.0, 0.383, 1.6),
            ("Venus", "2kvenus.jpg", 3.5, 2.5, 0.949, 0.6),
            ("Earth", "2kearth.jpg", 5.0, 1.6, 1.0, 1.2),
            ("Mars", "2kmars.jpg", 6.0, 1.2, 0.532, 1.0),
            ("Jupiter", "2kjupiter.jpg", 8.8, 0.6, 4.21, 0.5),
            ("Saturn", "2ksaturn.jpg", 11.0, 0.45, 3.45, 0.4),
            ("Uranus", "2kuranus.jpg", 14.0, 0.3, 4.01, 0.3),
            ("Neptune", "2kneptune.jpg", 16.0, 0.22, 3.88, 0.25),
        ]

        self.planets = []
        size_scale = 0.28

        for name, texture_file, orbit_r, orbit_s, real_diam, rot_s in planet_defs:
            # Load texture directly from assets folder
            tex_path = Path(self.resource_dir) / "assets" / texture_file
            img = Image.open(str(tex_path)).transpose(Image.FLIP_TOP_BOTTOM)
            tex = self.ctx.texture(img.size, 3, img.convert("RGB").tobytes())
            tex.build_mipmaps()

            raw_size = real_diam * size_scale
            size_capped = min(raw_size, 3.2)

            self.planets.append(
                {
                    "name": name,
                    "orbit_radius": orbit_r,
                    "orbit_speed": orbit_s,
                    "size": size_capped,
                    "rotation_speed": rot_s,
                    "texture": tex,
                }
            )

        print(f"Loaded {len(self.planets)} planets from assets folder")

        self.ring_prog = self.ctx.program(
            vertex_shader="""
                #version 330
                uniform mat4 mvp;
                in vec3 in_position;
                void main() {
                    gl_Position = mvp * vec4(in_position, 1.0);
                }
            """,
            fragment_shader="""
                #version 330
                uniform vec3 color;
                out vec4 fragColor;
                void main() {
                    fragColor = vec4(color, 1.0);
                }
            """,
        )

        for p in self.planets:
            r = p["orbit_radius"]
            segments = 128
            verts = []
            for i in range(segments):
                a = 2.0 * math.pi * i / segments
                x = math.cos(a) * r
                z = math.sin(a) * r
                verts.extend([x, 0.0, z])
            vbo = self.ctx.buffer(np.array(verts, dtype="f4").tobytes())
            vao = self.ctx.vertex_array(self.ring_prog, [(vbo, "3f", "in_position")])
            p["ring_vao"] = vao

        self.cam_r = 28.0
        self.cam_theta = math.radians(45.0)
        self.cam_phi = math.radians(50.0)
        self.dragging = False
        self.last_mouse = (0, 0)
        self.rotate_sensitivity = 0.005
        self.zoom_sensitivity = 1.0

    def on_render(self, time, frame_time):
        """
        Render setiap frame: update animasi, setup kamera, render matahari, orbit, dan planet.
        """
        self.ctx.clear(0.0, 0.0, 0.05)
        self.time += frame_time

        st = math.sin(self.cam_phi)
        eye = (
            self.cam_r * st * math.cos(self.cam_theta),
            self.cam_r * math.cos(self.cam_phi),
            self.cam_r * st * math.sin(self.cam_theta),
        )
        camera = Matrix44.look_at(eye=eye, target=(0.0, 0.0, 0.0), up=(0.0, 1.0, 0.0))
        projection = Matrix44.perspective_projection(
            45.0, self.wnd.aspect_ratio, 0.1, 400.0
        )

        self.sun_texture.use(location=0)
        sun_mvp = projection * camera * Matrix44.from_scale((2.5, 2.5, 2.5))
        self.mvp.write(sun_mvp.astype("f4").tobytes())
        self.ctx.front_face = "ccw"
        self.sphere.render(self.program)

        self.ring_prog["color"].value = (0.6, 0.6, 0.6)
        self.ring_prog["mvp"].write((projection * camera).astype("f4").tobytes())
        for p in self.planets:
            p["ring_vao"].render(mode=moderngl.LINE_LOOP)

        for p in self.planets:
            angle = self.time * p["orbit_speed"]
            orbit_pos = (
                math.cos(angle) * p["orbit_radius"],
                0.0,
                math.sin(angle) * p["orbit_radius"],
            )

            planet_model = (
                Matrix44.from_translation(orbit_pos)
                * Matrix44.from_y_rotation(self.time * p["rotation_speed"])
                * Matrix44.from_scale((p["size"], p["size"], p["size"]))
            )

            self.mvp.write((projection * camera * planet_model).astype("f4").tobytes())
            p["texture"].use(location=0)
            self.sphere.render(self.program)

    def key_event(self, key, action, modifiers):
        """Handle keyboard input (ESC untuk keluar)."""
        if action == self.wnd.keys.ACTION_PRESS and key == self.wnd.keys.ESCAPE:
            self.wnd.close()

    def mouse_drag_event(self, x, y, dx, dy, buttons):
        """Rotasi kamera dengan drag mouse kiri."""
        try:
            left = self.wnd.mouse_states.left
        except Exception:
            left = bool(buttons & 1)
        if left:
            self.cam_theta -= dx * self.rotate_sensitivity
            self.cam_phi -= dy * self.rotate_sensitivity
            self.cam_phi = max(0.05, min(math.pi - 0.05, self.cam_phi))

    def scroll_event(self, x, y, dx, dy):
        """Zoom kamera dengan scroll mouse."""
        self.cam_r = max(6.0, min(120.0, self.cam_r - dy * self.zoom_sensitivity))


if __name__ == "__main__":
    mglw.run_window_config(RotatingPlanet)
