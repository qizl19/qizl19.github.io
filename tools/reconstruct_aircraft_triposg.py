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
    parser.add_argument("--smoke-only", action="store_true")
    args = parser.parse_args()

    triposg_root = args.triposg_root.resolve()
    input_path = args.input.resolve()
    output_path = args.output.resolve()
    work_dir = args.work_dir.resolve()
    work_dir.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)

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
            "extents": [round(float(value), 6) for value in mesh.extents],
        },
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
