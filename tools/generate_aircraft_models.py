from __future__ import annotations

import argparse
import json
import math
import struct
from dataclasses import dataclass
from pathlib import Path


Vec3 = tuple[float, float, float]


@dataclass
class Part:
    vertices: list[Vec3]
    triangles: list[tuple[int, int, int]]
    material: str


MATERIALS = {
    "light": ([0.78, 0.80, 0.82, 1.0], 0.42, 0.65),
    "white": ([0.90, 0.92, 0.94, 1.0], 0.28, 0.55),
    "gray": ([0.31, 0.34, 0.37, 1.0], 0.36, 0.75),
    "dark": ([0.055, 0.065, 0.08, 1.0], 0.15, 0.78),
    "blue": ([0.10, 0.25, 0.48, 1.0], 0.42, 0.70),
    "red": ([0.64, 0.08, 0.07, 1.0], 0.20, 0.68),
    "olive": ([0.29, 0.32, 0.20, 1.0], 0.08, 0.92),
    "wood": ([0.43, 0.29, 0.17, 1.0], 0.04, 0.96),
    "glass": ([0.035, 0.13, 0.20, 0.82], 0.25, 0.35),
    "prop": ([0.055, 0.055, 0.055, 0.34], 0.04, 0.86),
}


def ellipsoid(center: Vec3, radii: Vec3, material: str, lat_steps: int = 10, lon_steps: int = 24) -> Part:
    cx, cy, cz = center
    rx, ry, rz = radii
    vertices: list[Vec3] = []
    for lat in range(lat_steps + 1):
        phi = -math.pi / 2 + math.pi * lat / lat_steps
        for lon in range(lon_steps):
            theta = 2 * math.pi * lon / lon_steps
            vertices.append((
                cx + rx * math.cos(phi) * math.cos(theta),
                cy + ry * math.sin(phi),
                cz + rz * math.cos(phi) * math.sin(theta),
            ))
    triangles: list[tuple[int, int, int]] = []
    for lat in range(lat_steps):
        for lon in range(lon_steps):
            nxt = (lon + 1) % lon_steps
            a = lat * lon_steps + lon
            b = lat * lon_steps + nxt
            c = (lat + 1) * lon_steps + lon
            d = (lat + 1) * lon_steps + nxt
            triangles.extend([(a, c, b), (b, c, d)])
    return Part(vertices, triangles, material)


def cylinder_x(center: Vec3, length: float, radius: float, material: str, segments: int = 18) -> Part:
    cx, cy, cz = center
    vertices: list[Vec3] = []
    for end in (-0.5, 0.5):
        for index in range(segments):
            angle = 2 * math.pi * index / segments
            vertices.append((cx + length * end, cy + radius * math.cos(angle), cz + radius * math.sin(angle)))
    vertices.extend([(cx - length / 2, cy, cz), (cx + length / 2, cy, cz)])
    triangles: list[tuple[int, int, int]] = []
    for index in range(segments):
        nxt = (index + 1) % segments
        triangles.extend([
            (index, segments + index, nxt),
            (nxt, segments + index, segments + nxt),
            (2 * segments, nxt, index),
            (2 * segments + 1, segments + index, segments + nxt),
        ])
    return Part(vertices, triangles, material)


def top_prism(points: list[tuple[float, float]], y: float, thickness: float, material: str) -> Part:
    # points are (x, z), viewed from above.
    vertices = [(x, y - thickness / 2, z) for x, z in points] + [(x, y + thickness / 2, z) for x, z in points]
    count = len(points)
    triangles: list[tuple[int, int, int]] = []
    for index in range(1, count - 1):
        triangles.extend([(0, index + 1, index), (count, count + index, count + index + 1)])
    for index in range(count):
        nxt = (index + 1) % count
        triangles.extend([(index, nxt, count + index), (nxt, count + nxt, count + index)])
    return Part(vertices, triangles, material)


def side_prism(points: list[tuple[float, float]], z: float, thickness: float, material: str) -> Part:
    # points are (x, y), viewed from the side.
    vertices = [(x, y, z - thickness / 2) for x, y in points] + [(x, y, z + thickness / 2) for x, y in points]
    count = len(points)
    triangles: list[tuple[int, int, int]] = []
    for index in range(1, count - 1):
        triangles.extend([(0, index, index + 1), (count, count + index + 1, count + index)])
    for index in range(count):
        nxt = (index + 1) % count
        triangles.extend([(index, count + index, nxt), (nxt, count + index, count + nxt)])
    return Part(vertices, triangles, material)


def add_symmetric_engines(parts: list[Part], positions: list[float], x: float, y: float, length: float, radius: float, material: str = "gray") -> None:
    for z in positions:
        parts.append(cylinder_x((x, y, z), length, radius, material))
        parts.append(cylinder_x((x + length * 0.46, y, z), length * 0.10, radius * 0.70, "dark"))


def aircraft_parts(slug: str) -> list[Part]:
    if slug == "boeing-747":
        parts = [
            ellipsoid((0, 0, 0), (38.15, 3.25, 3.15), "white"),
            ellipsoid((20.3, 2.25, 0), (11.0, 1.45, 2.45), "white", 8, 20),
            ellipsoid((32.8, 1.05, 0), (2.1, 0.48, 2.0), "glass", 5, 16),
            top_prism([(10, 0), (0, 5), (-11, 34.2), (-18, 34.2), (-8, 4), (-15, 0), (-8, -4), (-18, -34.2), (-11, -34.2), (0, -5)], 0.6, 0.55, "light"),
            top_prism([(-25, 0), (-29, 2.2), (-34, 14.5), (-38, 14.5), (-34, 0), (-38, -14.5), (-34, -14.5), (-29, -2.2)], 0.5, 0.42, "light"),
            side_prism([(-31, 1), (-35, 12), (-38, 12), (-38, 0)], 0, 0.5, "blue"),
        ]
        add_symmetric_engines(parts, [-13.5, -25.3, 13.5, 25.3], -1.0, -2.1, 5.8, 1.42)
        return parts
    if slug == "concorde":
        parts = [
            ellipsoid((0, 0, 0), (30.83, 1.55, 1.45), "white", 10, 26),
            ellipsoid((26.0, 0.62, 0), (3.5, 0.40, 1.05), "glass", 5, 16),
            top_prism([(16, 0), (5, 2.2), (-11, 12.8), (-19, 12.8), (-13, 2.5), (-24, 0), (-13, -2.5), (-19, -12.8), (-11, -12.8), (5, -2.2)], 0.0, 0.32, "white"),
            side_prism([(-18, 0.6), (-23, 7.0), (-26, 7.0), (-27, 0.2)], 0, 0.30, "red"),
        ]
        add_symmetric_engines(parts, [-4.8, -7.7, 4.8, 7.7], -8.5, -0.85, 6.5, 0.72, "gray")
        return parts
    if slug == "de-havilland-mosquito":
        parts = [
            ellipsoid((0, 0, 0), (6.20, 0.72, 0.68), "wood", 9, 22),
            ellipsoid((2.15, 0.72, 0), (1.55, 0.62, 0.55), "glass", 6, 18),
            top_prism([(2.2, 0), (1.2, 1.1), (0.5, 8.25), (-1.4, 8.25), (-1.2, 1.0), (-2.1, 0), (-1.2, -1.0), (-1.4, -8.25), (0.5, -8.25), (1.2, -1.1)], 0.2, 0.25, "olive"),
            top_prism([(-4.3, 0), (-4.8, 0.75), (-5.35, 3.0), (-6.0, 3.0), (-5.5, 0), (-6.0, -3.0), (-5.35, -3.0), (-4.8, -0.75)], 0.2, 0.20, "olive"),
            side_prism([(-4.7, 0.4), (-5.2, 2.4), (-5.9, 2.4), (-6.0, 0.1)], 0, 0.22, "olive"),
        ]
        for z in (-3.2, 3.2):
            parts.append(ellipsoid((0.4, -0.05, z), (2.15, 0.60, 0.60), "olive", 7, 18))
            parts.append(cylinder_x((2.55, -0.05, z), 0.12, 1.55, "prop", 22))
            parts.append(cylinder_x((2.7, -0.05, z), 0.45, 0.18, "dark", 12))
        return parts
    if slug == "y-20-kunpeng":
        parts = [
            ellipsoid((0, 0, 0), (23.50, 2.75, 2.65), "gray", 10, 24),
            ellipsoid((18.2, 1.0, 0), (3.1, 0.65, 1.9), "glass", 6, 18),
            top_prism([(8, 0), (1, 4.0), (-5, 22.5), (-13, 22.5), (-7, 3.0), (-13, 0), (-7, -3.0), (-13, -22.5), (-5, -22.5), (1, -4.0)], 2.3, 0.52, "gray"),
            top_prism([(-15, 0), (-17, 2.0), (-20, 9.0), (-23, 9.0), (-21, 0), (-23, -9.0), (-20, -9.0), (-17, -2.0)], 6.1, 0.38, "gray"),
            side_prism([(-17, 1.0), (-19, 9.6), (-22, 9.6), (-23, 0.0)], 0, 0.42, "gray"),
        ]
        add_symmetric_engines(parts, [-9.0, -16.5, 9.0, 16.5], -0.3, 0.2, 4.8, 1.22, "dark")
        return parts
    raise KeyError(f"Unsupported aircraft slug: {slug}")


def face_expanded(part: Part) -> tuple[list[Vec3], list[Vec3], list[int]]:
    positions: list[Vec3] = []
    normals: list[Vec3] = []
    indices: list[int] = []
    for triangle in part.triangles:
        a, b, c = (part.vertices[index] for index in triangle)
        ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
        vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
        nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
        length = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
        normal = (nx / length, ny / length, nz / length)
        start = len(positions)
        positions.extend([a, b, c])
        normals.extend([normal, normal, normal])
        indices.extend([start, start + 1, start + 2])
    return positions, normals, indices


def align4(buffer: bytearray) -> None:
    while len(buffer) % 4:
        buffer.append(0)


def write_glb(path: Path, slug: str, title: str) -> None:
    material_names = list(MATERIALS)
    materials = []
    for name in material_names:
        color, metallic, roughness = MATERIALS[name]
        material = {
            "name": name,
            "pbrMetallicRoughness": {
                "baseColorFactor": color,
                "metallicFactor": metallic,
                "roughnessFactor": roughness,
            },
            "doubleSided": True,
        }
        if color[3] < 1:
            material["alphaMode"] = "BLEND"
        materials.append(material)

    binary = bytearray()
    buffer_views: list[dict] = []
    accessors: list[dict] = []
    primitives: list[dict] = []
    for part in aircraft_parts(slug):
        positions, normals, indices = face_expanded(part)
        position_offset = len(binary)
        for value in positions:
            binary.extend(struct.pack("<3f", *value))
        align4(binary)
        position_view = len(buffer_views)
        buffer_views.append({"buffer": 0, "byteOffset": position_offset, "byteLength": len(positions) * 12, "target": 34962})
        position_accessor = len(accessors)
        mins = [min(value[index] for value in positions) for index in range(3)]
        maxs = [max(value[index] for value in positions) for index in range(3)]
        accessors.append({"bufferView": position_view, "componentType": 5126, "count": len(positions), "type": "VEC3", "min": mins, "max": maxs})

        normal_offset = len(binary)
        for value in normals:
            binary.extend(struct.pack("<3f", *value))
        align4(binary)
        normal_view = len(buffer_views)
        buffer_views.append({"buffer": 0, "byteOffset": normal_offset, "byteLength": len(normals) * 12, "target": 34962})
        normal_accessor = len(accessors)
        accessors.append({"bufferView": normal_view, "componentType": 5126, "count": len(normals), "type": "VEC3"})

        index_offset = len(binary)
        component_type = 5123 if max(indices) <= 65535 else 5125
        index_format = "<H" if component_type == 5123 else "<I"
        for index in indices:
            binary.extend(struct.pack(index_format, index))
        align4(binary)
        index_size = 2 if component_type == 5123 else 4
        index_view = len(buffer_views)
        buffer_views.append({"buffer": 0, "byteOffset": index_offset, "byteLength": len(indices) * index_size, "target": 34963})
        index_accessor = len(accessors)
        accessors.append({"bufferView": index_view, "componentType": component_type, "count": len(indices), "type": "SCALAR", "min": [0], "max": [max(indices)]})
        primitives.append({
            "attributes": {"POSITION": position_accessor, "NORMAL": normal_accessor},
            "indices": index_accessor,
            "material": material_names.index(part.material),
        })

    document = {
        "asset": {
            "version": "2.0",
            "generator": "Qzl aircraft low-poly generator",
            "copyright": "Qzl's Blog; generated from public overall dimensions for educational visualization",
            "extras": {"title": title, "slug": slug, "accuracy": "visual reference only; not engineering geometry"},
        },
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": title}],
        "meshes": [{"name": f"{title} low-poly reference", "primitives": primitives}],
        "materials": materials,
        "buffers": [{"byteLength": len(binary)}],
        "bufferViews": buffer_views,
        "accessors": accessors,
    }
    json_chunk = json.dumps(document, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    while len(json_chunk) % 4:
        json_chunk += b" "
    total_length = 12 + 8 + len(json_chunk) + 8 + len(binary)
    payload = (
        struct.pack("<4sII", b"glTF", 2, total_length)
        + struct.pack("<I4s", len(json_chunk), b"JSON")
        + json_chunk
        + struct.pack("<I4s", len(binary), b"BIN\x00")
        + bytes(binary)
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate light-weight public-dimension aircraft reference GLBs.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.root.resolve()
    profiles = json.loads((root / "data" / "aircraft_posts.json").read_text(encoding="utf-8"))
    for profile in profiles:
        model = profile.get("model")
        if not model or model.get("kind") != "generated-low-poly":
            continue
        target = root / model["src"].lstrip("/")
        write_glb(target, profile["slug"], profile["nameZh"])
        print(f"{profile['slug']}: {target.relative_to(root)} ({target.stat().st_size / 1024:.1f} KiB)")


if __name__ == "__main__":
    main()
