from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
import time
import types
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageDraw
from skimage import measure


LOGGER = logging.getLogger("aircraft-triposr")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_manifest_path(path: Path) -> str:
    """Avoid publishing machine-specific absolute paths in QA manifests."""
    try:
        return path.relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.name


def install_torchmcubes_compatibility_shim() -> None:
    """Provide the small API surface TripoSR needs without a CUDA build step.

    TripoSR inference and density evaluation still run on CUDA. Only marching
    cubes is evaluated on the CPU with scikit-image, which is reliable on
    Windows and avoids a fragile local C++/CUDA extension build.
    """

    module = types.ModuleType("torchmcubes")

    def marching_cubes(volume: torch.Tensor, threshold: float):
        array = volume.detach().cpu().numpy().astype(np.float32, copy=False)
        vertices, faces, _, _ = measure.marching_cubes(
            array,
            level=float(threshold),
            allow_degenerate=False,
        )
        # MarchingCubeHelper swaps axes after the backend call. Pre-swap the
        # scikit-image result so the two swaps cancel and grid axes are kept.
        vertices = vertices[:, [2, 1, 0]].copy()
        faces = faces.astype(np.int64, copy=False).copy()
        return torch.from_numpy(vertices), torch.from_numpy(faces)

    module.marching_cubes = marching_cubes
    sys.modules["torchmcubes"] = module


def prepare_image(
    input_path: Path,
    work_dir: Path,
    foreground_ratio: float,
    rembg_model: str,
):
    import rembg
    from tsr.utils import remove_background, resize_foreground

    LOGGER.info("Removing background with rembg/%s", rembg_model)
    session = rembg.new_session(rembg_model)
    rgba = remove_background(Image.open(input_path), session, force=True)
    rgba = resize_foreground(rgba, foreground_ratio)
    rgba.save(work_dir / "input-rgba.png")

    values = np.asarray(rgba).astype(np.float32) / 255.0
    rgb = values[:, :, :3] * values[:, :, 3:4] + (1.0 - values[:, :, 3:4]) * 0.5
    prepared = Image.fromarray(np.clip(rgb * 255.0, 0, 255).astype(np.uint8))
    prepared.save(work_dir / "input-prepared.png")
    return prepared


def write_contact_sheet(images: list[Image.Image], output: Path) -> None:
    if not images:
        return
    tile = 256
    columns = 4
    rows = (len(images) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * tile, rows * (tile + 28)), "#e7edf4")
    draw = ImageDraw.Draw(sheet)
    for index, image in enumerate(images):
        x = (index % columns) * tile
        y = (index // columns) * (tile + 28)
        sheet.paste(image.convert("RGB").resize((tile, tile)), (x, y))
        draw.text((x + 9, y + tile + 6), f"view {index + 1}", fill="#172235")
    sheet.save(output, quality=92)


def clean_mesh(mesh):
    mesh.remove_infinite_values()
    mesh.remove_unreferenced_vertices()
    if mesh.vertices.size:
        mesh.vertices -= mesh.bounding_box.centroid
        extent = float(mesh.extents.max())
        if extent > 0:
            mesh.vertices /= extent
    return mesh


def reconstruct(args: argparse.Namespace) -> dict:
    triposr_root = args.triposr_root.resolve()
    if not (triposr_root / "tsr" / "system.py").is_file():
        raise FileNotFoundError(f"Not a TripoSR source tree: {triposr_root}")
    sys.path.insert(0, str(triposr_root))
    install_torchmcubes_compatibility_shim()

    import trimesh
    from tsr.system import TSR

    input_path = args.input.resolve()
    output_path = args.output.resolve()
    work_dir = args.work_dir.resolve()
    work_dir.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if args.device.startswith("cuda") and not torch.cuda.is_available():
        LOGGER.warning("CUDA is unavailable; falling back to CPU")
        device = "cpu"
    else:
        device = args.device

    started = time.perf_counter()
    prepared = prepare_image(
        input_path,
        work_dir,
        args.foreground_ratio,
        args.rembg_model,
    )

    LOGGER.info("Loading %s", args.pretrained_model)
    model = TSR.from_pretrained(
        args.pretrained_model,
        config_name="config.yaml",
        weight_name="model.ckpt",
    )
    model.renderer.set_chunk_size(args.chunk_size)
    model.to(device)
    model.eval()

    LOGGER.info("Inferring a scene code on %s", device)
    with torch.inference_mode():
        scene_codes = model([prepared], device=device)

    LOGGER.info("Rendering %d QA views", args.qa_views)
    qa_images = model.render(
        scene_codes,
        n_views=args.qa_views,
        elevation_deg=args.qa_elevation,
        height=256,
        width=256,
        return_type="pil",
    )
    write_contact_sheet(qa_images[0], work_dir / "qa-contact-sheet.jpg")

    LOGGER.info("Extracting a %d^3 mesh", args.mc_resolution)
    meshes = model.extract_mesh(
        scene_codes,
        has_vertex_color=True,
        resolution=args.mc_resolution,
        threshold=args.density_threshold,
    )
    mesh = clean_mesh(meshes[0])
    if not isinstance(mesh, trimesh.Trimesh) or len(mesh.vertices) == 0 or len(mesh.faces) == 0:
        raise RuntimeError("TripoSR returned an empty mesh")
    mesh.export(output_path, file_type="glb")

    elapsed = time.perf_counter() - started
    manifest = {
        "schemaVersion": 1,
        "generator": "TripoSR with scikit-image marching-cubes compatibility shim",
        "engine": {
            "name": "TripoSR",
            "model": args.pretrained_model,
            "source": "https://github.com/VAST-AI-Research/TripoSR",
            "license": "MIT",
        },
        "input": {
            "path": safe_manifest_path(input_path),
            "sha256": sha256(input_path),
            "sourceUrl": args.input_source_url,
            "credit": args.input_credit,
            "license": args.input_license,
            "licenseUrl": args.input_license_url,
        },
        "output": {
            "path": safe_manifest_path(output_path),
            "sha256": sha256(output_path),
            "bytes": output_path.stat().st_size,
            "vertices": int(len(mesh.vertices)),
            "faces": int(len(mesh.faces)),
        },
        "settings": {
            "device": device,
            "mcResolution": args.mc_resolution,
            "densityThreshold": args.density_threshold,
            "foregroundRatio": args.foreground_ratio,
            "rembgModel": args.rembg_model,
            "qaViews": args.qa_views,
        },
        "elapsedSeconds": round(elapsed, 2),
        "warning": "Single-image AI reconstruction for visual reference only; not an engineering-accurate aircraft model.",
    }
    manifest_path = args.manifest.resolve() if args.manifest else output_path.with_suffix(".json")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    LOGGER.info(
        "Done: %s (%d vertices, %d faces, %.2f MiB, %.1f s)",
        output_path,
        len(mesh.vertices),
        len(mesh.faces),
        output_path.stat().st_size / 1024 / 1024,
        elapsed,
    )
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reconstruct a lightweight aircraft GLB from one licensed photograph using TripoSR."
    )
    parser.add_argument("--triposr-root", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--pretrained-model", default="stabilityai/TripoSR")
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--chunk-size", type=int, default=8192)
    parser.add_argument("--mc-resolution", type=int, default=192)
    parser.add_argument("--density-threshold", type=float, default=25.0)
    parser.add_argument("--foreground-ratio", type=float, default=0.82)
    parser.add_argument("--rembg-model", default="u2netp")
    parser.add_argument("--qa-views", type=int, default=8)
    parser.add_argument("--qa-elevation", type=float, default=12.0)
    parser.add_argument("--input-source-url", default="")
    parser.add_argument("--input-credit", default="")
    parser.add_argument("--input-license", default="")
    parser.add_argument("--input-license-url", default="")
    return parser.parse_args()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    reconstruct(parse_args())
