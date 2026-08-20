from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import types
from pathlib import Path

import numpy as np
import torch
import trimesh
from PIL import Image, ImageDraw, ImageFont


ENGINE_URL = "https://github.com/VAST-AI-Research/TripoSG"


def install_optional_diso_stub() -> None:
    """Use TripoSG's portable hierarchical decoder on Windows."""
    module = types.ModuleType("diso")

    class DiffDMC:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("DiffDMC is unavailable; use the non-flash decoder")

    module.DiffDMC = DiffDMC
    sys.modules["diso"] = module


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_label(path: Path) -> str:
    """Keep manifests portable and free of local absolute paths."""
    return path.name


def simplify_mesh(mesh: trimesh.Trimesh, target_faces: int) -> trimesh.Trimesh:
    if target_faces <= 0 or len(mesh.faces) <= target_faces:
        return mesh
    import pymeshlab

    source = pymeshlab.Mesh(vertex_matrix=mesh.vertices, face_matrix=mesh.faces)
    mesh_set = pymeshlab.MeshSet()
    mesh_set.add_mesh(source)
    mesh_set.meshing_merge_close_vertices()
    mesh_set.meshing_decimation_quadric_edge_collapse(
        targetfacenum=target_faces,
        preservenormal=True,
        preservetopology=True,
        autoclean=True,
    )
    reduced = mesh_set.current_mesh()
    return trimesh.Trimesh(
        vertices=reduced.vertex_matrix(),
        faces=reduced.face_matrix(),
        process=True,
    )


def render_qa_views(mesh: trimesh.Trimesh, work_dir: Path) -> list[str]:
    """Render deterministic orthographic QA views without an OpenGL dependency."""
    views = [
        ("front", (1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
        ("front-quarter", (1.0, -1.0, 0.45), (0.0, 0.0, 1.0)),
        ("side", (0.0, -1.0, 0.0), (0.0, 0.0, 1.0)),
        ("rear-quarter", (-1.0, -1.0, 0.45), (0.0, 0.0, 1.0)),
        ("rear", (-1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
        ("top", (0.0, 0.0, 1.0), (1.0, 0.0, 0.0)),
        ("bottom", (0.0, 0.0, -1.0), (1.0, 0.0, 0.0)),
        ("top-quarter", (1.0, -1.0, 1.0), (0.0, 0.0, 1.0)),
    ]
    preview_mesh = simplify_mesh(mesh.copy(), 16000)
    vertices = np.asarray(preview_mesh.vertices, dtype=np.float64)
    faces = np.asarray(preview_mesh.faces, dtype=np.int64)
    face_vertices = vertices[faces]
    size = 720
    margin = 48
    rendered: list[str] = []
    sheets: list[Image.Image] = []

    for label, eye, up_hint in views:
        forward = np.asarray(eye, dtype=np.float64)
        forward /= np.linalg.norm(forward)
        up = np.asarray(up_hint, dtype=np.float64)
        up -= forward * np.dot(up, forward)
        if np.linalg.norm(up) < 1e-8:
            up = np.array([0.0, 1.0, 0.0], dtype=np.float64)
            up -= forward * np.dot(up, forward)
        up /= np.linalg.norm(up)
        right = np.cross(up, forward)
        right /= np.linalg.norm(right)

        projected = np.stack(
            (
                np.einsum("fvi,i->fv", face_vertices, right),
                np.einsum("fvi,i->fv", face_vertices, up),
            ),
            axis=-1,
        )
        depth = np.einsum("fvi,i->fv", face_vertices, forward).mean(axis=1)
        extent = np.ptp(projected.reshape(-1, 2), axis=0)
        scale = (size - 2 * margin) / max(float(extent.max()), 1e-9)
        center = projected.reshape(-1, 2).mean(axis=0)
        pixels = (projected - center) * scale + size / 2
        pixels[..., 1] = size - pixels[..., 1]

        normals = np.cross(
            face_vertices[:, 1] - face_vertices[:, 0],
            face_vertices[:, 2] - face_vertices[:, 0],
        )
        normal_lengths = np.linalg.norm(normals, axis=1)
        normal_lengths[normal_lengths == 0] = 1
        normals /= normal_lengths[:, None]
        light = np.array([0.35, -0.45, 0.82], dtype=np.float64)
        light /= np.linalg.norm(light)
        shade = 0.32 + 0.68 * np.abs(normals @ light)

        canvas = Image.new("RGB", (size, size), "#eef3f7")
        draw = ImageDraw.Draw(canvas)
        for face_index in np.argsort(depth):
            value = int(58 + 150 * float(shade[face_index]))
            color = (value - 8, value, min(255, value + 12))
            polygon = [tuple(point) for point in pixels[face_index]]
            draw.polygon(polygon, fill=color)
        draw.rectangle((0, 0, size - 1, size - 1), outline="#9aa9b5", width=2)
        draw.text((18, 16), label, fill="#17212b", font=ImageFont.load_default())
        filename = f"qa-{label}.png"
        canvas.save(work_dir / filename)
        rendered.append(filename)
        sheets.append(canvas.resize((360, 360), Image.Resampling.LANCZOS))

    contact = Image.new("RGB", (1440, 720), "#dfe7ed")
    for index, view in enumerate(sheets):
        contact.paste(view, ((index % 4) * 360, (index // 4) * 360))
    contact.save(work_dir / "qa-contact-sheet.png")
    rendered.append("qa-contact-sheet.png")
    return rendered


def require_weights(root: Path) -> tuple[Path, Path]:
    triposg_weights = root / "pretrained_weights" / "TripoSG"
    rmbg_weights = root / "pretrained_weights" / "RMBG-1.4"
    required = [
        triposg_weights / "image_encoder_dinov2" / "model.safetensors",
        triposg_weights / "transformer" / "diffusion_pytorch_model.safetensors",
        triposg_weights / "vae" / "diffusion_pytorch_model.safetensors",
        rmbg_weights / "model.safetensors",
    ]
    missing = [path for path in required if not path.is_file()]
    if missing:
        names = ", ".join(path.name for path in missing)
        raise FileNotFoundError(
            f"Local TripoSG weights are incomplete ({names}). "
            "This tool intentionally does not download weights."
        )
    return triposg_weights, rmbg_weights


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Offline TripoSG aircraft reconstruction for the blog"
    )
    parser.add_argument("--triposg-root", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--input-credit", required=True)
    parser.add_argument("--input-source-url", required=True)
    parser.add_argument("--input-license", required=True)
    parser.add_argument("--faces", type=int, default=80000)
    parser.add_argument("--steps", type=int, default=40)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--dense-depth", type=int, default=8)
    parser.add_argument("--hierarchical-depth", type=int, default=9)
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Require the already-installed local official weights; this wrapper never downloads weights.",
    )
    parser.add_argument("--smoke-only", action="store_true")
    parser.add_argument("--audit-existing", action="store_true")
    args = parser.parse_args()

    triposg_root = args.triposg_root.resolve()
    input_path = args.input.resolve()
    output_path = args.output.resolve()
    work_dir = args.work_dir.resolve()
    work_dir.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if args.audit_existing:
        loaded = trimesh.load(output_path, force="mesh")
        if not isinstance(loaded, trimesh.Trimesh) or not len(loaded.faces):
            raise RuntimeError("Existing GLB is empty or not a mesh")
        print(json.dumps({"qa": render_qa_views(loaded, work_dir)}, indent=2))
        return

    install_optional_diso_stub()
    sys.path.insert(0, str(triposg_root))
    sys.path.insert(0, str(triposg_root / "scripts"))

    from briarmbg import BriaRMBG
    from image_process import prepare_image
    from triposg.pipelines.pipeline_triposg import TripoSGPipeline

    if args.smoke_only:
        require_weights(triposg_root)
        print("TRIPOSG_OFFLINE_SMOKE_OK")
        return
    if not input_path.is_file():
        raise FileNotFoundError(input_path)
    if not torch.cuda.is_available():
        raise RuntimeError("A CUDA-capable GPU is required")

    triposg_weights, rmbg_weights = require_weights(triposg_root)
    device = torch.device("cuda:0")
    started = time.perf_counter()

    rmbg_net = BriaRMBG.from_pretrained(rmbg_weights).to(device)
    rmbg_net.eval()
    prepared = prepare_image(
        str(input_path),
        bg_color=np.array([1.0, 1.0, 1.0]),
        rmbg_net=rmbg_net,
    )
    prepared.save(work_dir / "input-prepared.png")

    pipe = TripoSGPipeline.from_pretrained(triposg_weights).to(device, torch.float16)
    generator = torch.Generator(device=device).manual_seed(args.seed)
    with torch.inference_mode():
        result = pipe(
            image=prepared,
            generator=generator,
            num_inference_steps=args.steps,
            guidance_scale=7.0,
            use_flash_decoder=False,
            dense_octree_depth=args.dense_depth,
            hierarchical_octree_depth=args.hierarchical_depth,
        )

    mesh = result.meshes[0]
    if not isinstance(mesh, trimesh.Trimesh) or not len(mesh.faces):
        raise RuntimeError("TripoSG returned an empty mesh")
    mesh.remove_infinite_values()
    mesh.remove_unreferenced_vertices()
    mesh = simplify_mesh(mesh, args.faces)
    mesh.vertices -= mesh.bounding_box.centroid
    extent = float(mesh.extents.max())
    if extent > 0:
        mesh.vertices /= extent
    mesh.export(output_path, file_type="glb")
    qa_files = render_qa_views(mesh, work_dir)

    report = {
        "generator": "TripoSG official hierarchical decoder",
        "engine": {"source": ENGINE_URL, "license": "MIT"},
        "input": {
            "path": safe_label(input_path),
            "sha256": sha256(input_path),
            "credit": args.input_credit,
            "sourceUrl": args.input_source_url,
            "license": args.input_license,
        },
        "output": {
            "path": safe_label(output_path),
            "sha256": sha256(output_path),
            "bytes": output_path.stat().st_size,
            "vertices": int(len(mesh.vertices)),
            "faces": int(len(mesh.faces)),
            "components": int(len(mesh.split(only_watertight=False))),
            "watertight": bool(mesh.is_watertight),
            "windingConsistent": bool(mesh.is_winding_consistent),
            "eulerNumber": int(mesh.euler_number),
            "surfaceArea": round(float(mesh.area), 6),
            "boundsFinite": bool(np.isfinite(mesh.bounds).all()),
            "extents": [round(float(value), 6) for value in mesh.extents],
        },
        "qa": qa_files,
        "settings": {
            "steps": args.steps,
            "seed": args.seed,
            "guidanceScale": 7.0,
            "denseDepth": args.dense_depth,
            "hierarchicalDepth": args.hierarchical_depth,
            "targetFaces": args.faces,
            "flashDecoder": False,
        },
        "runtime": {
            "torch": torch.__version__,
            "gpu": torch.cuda.get_device_name(device),
            "peakVramMiB": round(torch.cuda.max_memory_allocated() / 1024 / 1024, 1),
            "elapsedSeconds": round(time.perf_counter() - started, 2),
        },
        "warning": "Visual-reference reconstruction only; not engineering geometry.",
    }
    manifest = output_path.with_suffix(".json")
    manifest.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
