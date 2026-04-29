from pathlib import Path
import yaml

ROOT = Path(__file__).parent.parent


def load_config() -> dict:
    with open(ROOT / "config.yaml") as f:
        return yaml.safe_load(f)


def load_interest_profile() -> dict:
    with open(Path(__file__).parent / "interest_profile.yaml") as f:
        return yaml.safe_load(f)
