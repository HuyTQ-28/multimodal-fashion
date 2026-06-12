from pathlib import Path
import shutil

import modal


APP_NAME = "freedom-hm-training"
REMOTE_ROOT = "/workspace/FREEDOM"
REMOTE_SRC = f"{REMOTE_ROOT}/src"
REMOTE_DATA = f"{REMOTE_ROOT}/data"
REMOTE_OUT = "/outputs"

data_volume = modal.Volume.from_name("freedom-hm-data", create_if_missing=True)
out_volume = modal.Volume.from_name("freedom-hm-outputs", create_if_missing=True)

image = (
    modal.Image.from_registry(
        "nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04",
        add_python="3.10",
    )
    .apt_install("git", "gcc", "g++")
    .run_commands(
        "pip install --upgrade pip",
        "pip install torch==2.0.1 torchvision==0.15.2 "
        "--index-url https://download.pytorch.org/whl/cu118",
    )
    .pip_install(
        "numpy==1.24.4",
        "pandas==1.5.3",
        "scipy==1.10.1",
        "PyYAML==6.0.1",
        "lmdb==1.4.1",
        "matplotlib==3.7.3",
        "tqdm==4.66.4",
    )
    .add_local_dir("src", remote_path=REMOTE_SRC, copy=True)
)

app = modal.App(APP_NAME)


def _ensure_hm_config():
    cfg_dir = Path(REMOTE_SRC) / "configs" / "dataset"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    cfg_path = cfg_dir / "hm.yaml"

    cfg_path.write_text(
        "\n".join(
            [
                "USER_ID_FIELD: userID:token",
                "ITEM_ID_FIELD: itemID:token",
                "TIME_FIELD: timestamp:float",
                "inter_splitting_label: x_label:float",
                "filter_out_cod_start_users: True",
                "inter_file_name: 'hm.inter'",
                "vision_feature_file: 'image_feat.npy'",
                "text_feature_file: 'text_feat.npy'",
                'field_separator: "\\t"',
                "",
            ]
        ),
        encoding="utf-8",
    )


def _validate_data():
    hm_dir = Path(REMOTE_DATA) / "hm"
    required = [
        "hm.inter",
        "image_feat.npy",
        "text_feat.npy",
        "edge_timestamps.npy",
        "id_map_user.csv",
        "id_map_item.csv",
    ]

    missing = [name for name in required if not (hm_dir / name).exists()]
    if missing:
        raise FileNotFoundError(
            "Missing files in Modal volume /workspace/FREEDOM/data/hm: "
            + ", ".join(missing)
        )


@app.function(
    image=image,
    gpu="A100-40GB",
    timeout=60 * 60 * 12,
    volumes={
        REMOTE_DATA: data_volume,
        REMOTE_OUT: out_volume,
    },
)
def train(
    epochs: int = 1000,
    seed: int = 2024,
    smoke: bool = False,
    run_name: str = "",
    pruning_lambda: float = 0.01,
    pruning_keep_ratio: float = 0.8,
    mm_image_weight: float = 0.3,
    reg_weight: float = 1e-4,
    dropout: float = 0.8,
    knn_k: int = 10,
    n_ui_layers: int = 2,
    n_mm_layers: int = 1,
    embedding_size: int = 64,
    learning_rate: float = 1e-3,
    train_batch_size: int = 2048,
    eval_batch_size: int = 4096,
    stopping_step: int = 20,
):
    import os
    import sys

    _ensure_hm_config()
    _validate_data()

    os.chdir(REMOTE_SRC)
    sys.path.insert(0, REMOTE_SRC)

    from utils.quick_start import quick_start

    run_epochs = 5 if smoke else epochs
    run_id = run_name or (
        f"{'smoke' if smoke else 'train'}"
        f"-pl{pruning_lambda}"
        f"-pk{pruning_keep_ratio}"
        f"-miw{mm_image_weight}"
        f"-rw{reg_weight}"
        f"-k{knn_k}"
        f"-seed{seed}"
    )
    run_out = Path(REMOTE_OUT) / "runs" / run_id

    config_dict = {
        "gpu_id": 0,
        "use_gpu": True,
        "epochs": run_epochs,
        "stopping_step": stopping_step,
        "seed": [seed],
        "hyper_parameters": ["seed"],
        "pruning_lambda": pruning_lambda,
        "pruning_keep_ratio": pruning_keep_ratio,
        "mm_image_weight": mm_image_weight,
        "reg_weight": reg_weight,
        "dropout": dropout,
        "knn_k": knn_k,
        "n_ui_layers": n_ui_layers,
        "n_mm_layers": n_mm_layers,
        "embedding_size": embedding_size,
        "feat_embed_dim": embedding_size,
        "learning_rate": learning_rate,
        "train_batch_size": train_batch_size,
        "eval_batch_size": eval_batch_size,
        "checkpoint_dir": str(run_out / "saved"),
        "recommend_topk": str(run_out / "recommend_topk"),
    }

    quick_start(
        model="FREEDOM",
        dataset="hm",
        config_dict=config_dict,
        save_model=True,
    )

    run_out.mkdir(parents=True, exist_ok=True)
    for name in ["log"]:
        src = Path(REMOTE_SRC) / name
        dst = run_out / name
        if src.exists():
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)

    out_volume.commit()
    data_volume.commit()
    return {"status": "complete", "epochs": run_epochs, "outputs": str(run_out)}


@app.local_entrypoint()
def main(
    smoke: str = "false",
    epochs: int = 1000,
    seed: int = 2024,
    run_name: str = "",
    pruning_lambda: float = 0.01,
    pruning_keep_ratio: float = 0.8,
    mm_image_weight: float = 0.3,
    reg_weight: float = 1e-4,
    knn_k: int = 10,
    n_ui_layers: int = 2,
    n_mm_layers: int = 1,
    embedding_size: int = 64,
    learning_rate: float = 1e-3,
    train_batch_size: int = 2048,
    eval_batch_size: int = 4096,
    stopping_step: int = 20,
):
    smoke_run = smoke.lower() in {"1", "true", "yes", "y"}
    result = train.remote(
        epochs=epochs,
        seed=seed,
        smoke=smoke_run,
        run_name=run_name,
        pruning_lambda=pruning_lambda,
        pruning_keep_ratio=pruning_keep_ratio,
        mm_image_weight=mm_image_weight,
        reg_weight=reg_weight,
        knn_k=knn_k,
        n_ui_layers=n_ui_layers,
        n_mm_layers=n_mm_layers,
        embedding_size=embedding_size,
        learning_rate=learning_rate,
        train_batch_size=train_batch_size,
        eval_batch_size=eval_batch_size,
        stopping_step=stopping_step,
    )
    print(result)
