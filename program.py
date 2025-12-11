import moderngl
import moderngl_window as mglw
from pyrr import Matrix44, Vector3
from PIL import Image
import numpy as np
import math


class RotatingPlanet(mglw.WindowConfig):
    gl_version = (3, 3)
    title = "3D Rotating Planet with Orbit"
    window_size = (800, 600)
    resource_dir = "."

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ctx.enable(moderngl.DEPTH_TEST)

        # --- Load Sphere Mesh ---
        self.sphere = mglw.geometry.sphere(radius=1.0, sectors=64, rings=32)

        # --- Load Textures (planet & sun) ---
        from pathlib import Path

        def find_and_load(names, fallback_type="earth"):
            # Try resource_dir/assets, script dir/assets, then other locations
            candidates = []
            for n in names:
                candidates.append(Path(self.resource_dir) / "assets" / n)
            for n in names:
                candidates.append(Path(__file__).parent / "assets" / n)
            for n in names:
                candidates.append(Path(self.resource_dir) / n)
            for n in names:
                candidates.append(Path(__file__).parent / n)
            for n in names:
                candidates.append(Path(n))

            for p in candidates:
                try:
                    if p.exists():
                        return Image.open(str(p)).transpose(Image.FLIP_TOP_BOTTOM), str(
                            p
                        )
                except Exception:
                    continue

            # fallback generated image
            if fallback_type == "sun":
                w, h = 1024, 1024
                img = Image.new("RGB", (w, h))
                # radial gradient (yellow -> orange)
                cx, cy = w // 2, h // 2
                for y in range(h):
                    for x in range(w):
                        dx = x - cx
                        dy = y - cy
                        d = math.sqrt(dx * dx + dy * dy) / (math.hypot(cx, cy))
                        d = min(max(d, 0.0), 1.0)
                        # interpolate between yellow and deep orange
                        r = int(255 * (1.0 - 0.6 * d))
                        g = int(200 * (1.0 - 0.7 * d))
                        b = int(30 * (1.0 - 0.9 * d))
                        img.putpixel((x, y), (r, g, b))
                return img, "generated(sun)"
            else:
                w, h = 1024, 512
                img = Image.new("RGB", (w, h))
                for y in range(h):
                    for x in range(w):
                        if ((x // 64) + (y // 64)) % 2 == 0:
                            img.putpixel((x, y), (24, 64, 160))
                        else:
                            img.putpixel((x, y), (34, 139, 34))
                return img, "generated(earth)"

        # Planet (earth) texture candidates
        earth_names = ["earthmap1k2.jpg", "Earthmap1k2.jpg", "earth.jpg"]
        earth_img, earth_src = find_and_load(earth_names, fallback_type="earth")

        # Sun texture candidates (user-provided `2ksun.jpg` expected)
        sun_names = ["2ksun.jpg", "2k_sun.jpg", "sun.jpg"]
        sun_img, sun_src = find_and_load(sun_names, fallback_type="sun")

        # Create GPU textures
        self.planet_texture = self.ctx.texture(
            earth_img.size, 3, earth_img.convert("RGB").tobytes()
        )
        self.planet_texture.build_mipmaps()

        self.sun_texture = self.ctx.texture(
            sun_img.size, 3, sun_img.convert("RGB").tobytes()
        )
        self.sun_texture.build_mipmaps()

        # Small informational print
        print(f"Planet texture: {earth_src} | Sun texture: {sun_src}")

        # --- Simple Shader Program ---
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

        # Time accumulator for animations
        self.time = 0.0

        # Define planets using more proportional radii and sizes.
        # orbit_radius chosen for visual spacing; real diameter ratios are used
        # to compute visual size with a controlled scale factor.
        # Entries: (name, orbit_radius, orbit_speed, real_diameter_ratio_to_earth, rotation_speed, color)
        planet_defs = [
            ("Mercury", 2.5, 4.0, 0.383, 1.6, [120, 120, 120]),
            ("Venus", 3.5, 2.5, 0.949, 0.6, [205, 170, 120]),
            ("Earth", 5.0, 1.6, 1.0, 1.2, None),
            ("Mars", 6.0, 1.2, 0.532, 1.0, [180, 80, 60]),
            ("Jupiter", 8.8, 0.6, 4.21, 0.5, [200, 140, 80]),
            ("Saturn", 11.0, 0.45, 3.45, 0.4, [220, 200, 160]),
            ("Uranus", 14.0, 0.3, 4.01, 0.3, [160, 200, 220]),
            ("Neptune", 16.0, 0.22, 3.88, 0.25, [70, 110, 200]),
        ]

        self.planets = []

        # Helper to try finding planet-specific textures, otherwise generate color texture
        def load_or_generate_planet_texture(
            base_names, color_rgb=None, size=(512, 256)
        ):
            img, src = find_and_load(base_names, fallback_type="earth")
            if src.startswith("generated") and color_rgb is not None:
                # generate a single-color texture for the planet
                w, h = size
                img = Image.new("RGB", (w, h), tuple(color_rgb))
                src = f"generated({base_names[0]})"
            return img, src

        # control how large planets appear relative to Earth in the scene
        size_scale = 0.28  # earth will be ~0.28 units; large planets scaled but capped

        for name, orbit_r, orbit_s, real_diam, rot_s, color in planet_defs:
            # try several filename variants including common 2k textures you provided
            nl = name.lower()
            candidates = [
                f"2k{nl}.jpg",
                f"2k_{nl}.jpg",
                f"2k{nl}.png",
                f"2k_{nl}.png",
                f"2k{nl}.jpeg",
                f"{nl}.jpg",
                f"{name}.jpg",
                f"{nl}.png",
                f"{nl}.jpeg",
            ]
            img, src = load_or_generate_planet_texture(candidates, color_rgb=color)
            tex = self.ctx.texture(img.size, 3, img.convert("RGB").tobytes())
            tex.build_mipmaps()

            # compute visual size from real diameter ratio; apply caps so very large
            # gas giants don't dominate the view
            raw_size = real_diam * size_scale
            size_capped = min(raw_size, 3.2)  # cap maximum visual radius

            self.planets.append(
                {
                    "name": name,
                    "orbit_radius": orbit_r,
                    "orbit_speed": orbit_s,
                    "size": size_capped,
                    "rotation_speed": rot_s,
                    "texture": tex,
                    "src": src,
                }
            )

        # Print summary of loaded planet textures
        print("Loaded planets:")
        for p in self.planets:
            print(f"  {p['name']}: texture={p['src']}, orbit_r={p['orbit_radius']}")

        # --- Orbit rings: create simple line program and ring VAOs per planet ---
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

        # create ring vertex arrays and store on planets
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

        # --- Camera control state (spherical coords) ---
        # radius, azimuth (theta), polar angle (phi)
        self.cam_r = 28.0
        self.cam_theta = math.radians(45.0)
        self.cam_phi = math.radians(50.0)
        self.dragging = False
        self.last_mouse = (0, 0)
        self.rotate_sensitivity = 0.005
        self.zoom_sensitivity = 1.0

    def on_render(self, time, frame_time):
        """Called each frame by moderngl-window (WindowConfig expects on_render)."""
        self.ctx.clear(0.0, 0.0, 0.05)

        # Update global time
        self.time += frame_time

        # Camera setup (compute from spherical coords)
        # convert spherical (r, theta, phi) to cartesian
        st = math.sin(self.cam_phi)
        eye_x = self.cam_r * st * math.cos(self.cam_theta)
        eye_y = self.cam_r * math.cos(self.cam_phi)
        eye_z = self.cam_r * st * math.sin(self.cam_theta)
        camera = Matrix44.look_at(
            eye=(eye_x, eye_y, eye_z), target=(0.0, 0.0, 0.0), up=(0.0, 1.0, 0.0)
        )

        # Projection matrix
        projection = Matrix44.perspective_projection(
            45.0, self.wnd.aspect_ratio, 0.1, 400.0
        )

        # --- Render Sun (central) ---
        # use sun texture
        self.sun_texture.use(location=0)
        sun_model = Matrix44.from_scale((2.5, 2.5, 2.5))
        sun_mvp = projection * camera * sun_model
        self.mvp.write(sun_mvp.astype("f4").tobytes())
        self.ctx.front_face = "ccw"
        self.sphere.render(self.program)

        # --- Draw orbit rings (subtle grey) ---
        ring_color = (0.6, 0.6, 0.6)
        self.ring_prog["color"].value = tuple(ring_color)
        ring_mvp = (projection * camera).astype("f4").tobytes()
        self.ring_prog["mvp"].write(ring_mvp)
        for p in self.planets:
            # render the stored ring VAO as line loop
            p["ring_vao"].render(mode=moderngl.LINE_LOOP)

        # --- Render all planets ---
        for p in self.planets:
            angle = self.time * p["orbit_speed"]
            orbit_x = math.cos(angle) * p["orbit_radius"]
            orbit_z = math.sin(angle) * p["orbit_radius"]

            # planet model: translate -> rotate on Y -> scale
            planet_model = (
                Matrix44.from_translation((orbit_x, 0.0, orbit_z))
                * Matrix44.from_y_rotation(self.time * p["rotation_speed"])
                * Matrix44.from_scale((p["size"], p["size"], p["size"]))
            )

            mvp = projection * camera * planet_model
            self.mvp.write(mvp.astype("f4").tobytes())

            # bind planet texture and render
            p["texture"].use(location=0)
            self.sphere.render(self.program)

    def key_event(self, key, action, modifiers):
        if action == self.wnd.keys.ACTION_PRESS:
            if key == self.wnd.keys.ESCAPE:
                self.wnd.close()

    def mouse_drag_event(self, x, y, dx, dy, buttons):
        """Rotate camera when left mouse button is dragged."""
        # left button is usually 1
        try:
            left = self.wnd.mouse_states.left
        except Exception:
            left = True if buttons & 1 else False
        if left:
            self.cam_theta += -dx * self.rotate_sensitivity
            self.cam_phi += -dy * self.rotate_sensitivity
            # clamp phi so camera doesn't flip
            eps = 0.05
            self.cam_phi = max(eps, min(math.pi - eps, self.cam_phi))

    def scroll_event(self, x, y, dx, dy):
        """Zoom camera with mouse wheel (dy)."""
        self.cam_r -= dy * self.zoom_sensitivity
        self.cam_r = max(6.0, min(120.0, self.cam_r))


if __name__ == "__main__":
    mglw.run_window_config(RotatingPlanet)
