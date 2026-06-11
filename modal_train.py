"""Modal deployment entrypoint for FREEDOM-RT student distillation."""

from pathlib import Path, PurePosixPath
import subprocess

import modal


APP_NAME = "freedom-rt-student-mlp"
REMOTE_APP_DIR = PurePosixPath("/root/freedom-rt")
REMOTE_DATA_DIR = PurePosixPath("/data/hm")
REMOTE_ARTIFACT_DIR = PurePosixPath("/artifacts")

app = modal.App(APP_NAME)

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("torch", "numpy", "scikit-learn", "matplotlib")
    .add_local_dir("ml", remote_path=str(REMOTE_APP_DIR / "ml"))
)

data_volume = modal.Volume.from_name("freedom-rt-hm-data", create_if_missing=True)
artifact_volume = modal.Volume.from_name("freedom-rt-artifacts", create_if_missing=True)


def _resolve_local_teacher_path(local_data_dir: Path) -> Path:
    root_teacher_path = local_data_dir / "teacher_item_128.npy"
    saved_teacher_path = local_data_dir / "saved" / "teacher_item_128.npy"
    if root_teacher_path.exists():
        return root_teacher_path
    if saved_teacher_path.exists():
        return saved_teacher_path
    raise FileNotFoundError(
        f"Could not find teacher_item_128.npy in {local_data_dir} or {local_data_dir / 'saved'}."
    )


def upload_training_data(local_data_dir: Path) -> None:
    """Upload required .npy files into the Modal data volume."""
    required_files = {
        "image_feat.npy": local_data_dir / "image_feat.npy",
        "text_feat.npy": local_data_dir / "text_feat.npy",
        "teacher_item_128.npy": _resolve_local_teacher_path(local_data_dir),
    }
    missing_files = [str(path) for path in required_files.values() if not path.exists()]
    if missing_files:
        raise FileNotFoundError(f"Missing required training files: {missing_files}")

    with data_volume.batch_upload(force=True) as batch:
        for remote_name, local_path in required_files.items():
            batch.put_file(str(local_path), f"/{remote_name}")


@app.function(
    image=image,
    gpu="A10G",
    timeout=60 * 60 * 6,
    volumes={
        str(REMOTE_DATA_DIR): data_volume,
        str(REMOTE_ARTIFACT_DIR): artifact_volume,
    },
)
def train_student(
    epochs: int = 30,
    batch_size: int = 1024,
    learning_rate: float = 1e-3,
) -> str:
    """Run ml/train.py on a Modal GPU and persist the checkpoint."""
    checkpoint_path = REMOTE_ARTIFACT_DIR / "student_mlp.pth"
    command = [
        "python",
        str(REMOTE_APP_DIR / "ml" / "train.py"),
        "--data-dir",
        str(REMOTE_DATA_DIR),
        "--teacher-target",
        str(REMOTE_DATA_DIR / "teacher_item_128.npy"),
        "--checkpoint",
        str(checkpoint_path),
        "--epochs",
        str(epochs),
        "--batch-size",
        str(batch_size),
        "--learning-rate",
        str(learning_rate),
    ]
    subprocess.run(command, cwd=str(REMOTE_APP_DIR), check=True)
    artifact_volume.commit()
    return str(checkpoint_path)


@app.local_entrypoint()
def main(
    epochs: int = 30,
    batch_size: int = 1024,
    learning_rate: float = 1e-3,
    local_data_dir: str = "dataset",
) -> None:
    """Launch remote training from the local machine."""
    upload_training_data(Path(local_data_dir))
    checkpoint_path = train_student.remote(
        epochs=epochs,
        batch_size=batch_size,
        learning_rate=learning_rate,
    )
    print(f"Saved checkpoint to Modal volume at {checkpoint_path}")
