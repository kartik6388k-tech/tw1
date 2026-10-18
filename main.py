
import os
from pathlib import Path

import yaml
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = Path(__file__).resolve().parent

DEFAULTS = {
    "port": 8000,
    "workers": 2,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def normalize_key(key):
    key = key.strip()

    if key.startswith("APP_"):
        key = key[4:]

    key = key.lower()

    if key == "num_workers":
        key = "workers"

    return key


def parse_value(key, value):
    value = str(value).strip()

    if key in ("port", "workers"):
        try:
            return int(value)
        except (ValueError, TypeError):
            return value

    if key == "debug":
        return value.lower() in ("true", "1", "yes", "on")

    return value


def read_yaml_config():
    env_name = os.environ.get("APP_ENV", "development")
    config_path = BASE_DIR / f"config.{env_name}.yaml"

    if not config_path.exists():
        return {}

    with config_path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}

    return {
        normalize_key(key): value
        for key, value in data.items()
    }


def read_dotenv_config():
    config = {}
    env_path = BASE_DIR / ".env"

    if not env_path.exists():
        return config

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'\"")

        if key == "NUM_WORKERS":
            config["workers"] = value
        elif key.startswith("APP_"):
            config[normalize_key(key)] = value

    return config


def read_os_config():
    config = {}

    for key, value in os.environ.items():
        if key.startswith("APP_"):
            config[normalize_key(key)] = value
        elif key == "NUM_WORKERS":
            config["workers"] = value

    return config


def get_effective_config(overrides):
    config = DEFAULTS.copy()

    # Low-to-high precedence
    config.update(read_yaml_config())
    config.update(read_dotenv_config())
    config.update(read_os_config())

    for item in overrides:
        if "=" not in item:
            continue

        key, value = item.split("=", 1)
        key = normalize_key(key)
        config[key] = value

    # Apply required type conversions
    config = {
        key: parse_value(key, value)
        for key, value in config.items()
    }

    # Never expose the real API key
    config["api_key"] = "****"

    return config


@app.get("/")
def health_check():
    return {"status": "ok"}


@app.get("/effective-config")
def effective_config(
    set: list[str] = Query(default=[])
):
    return get_effective_config(set)
