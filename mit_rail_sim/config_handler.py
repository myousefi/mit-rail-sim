from omegaconf import DictConfig

cfg = None


def set_config(config: DictConfig) -> None:
    global cfg
    cfg = config


def get_config() -> DictConfig:
    global cfg
    return cfg
