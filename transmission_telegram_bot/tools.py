import logging
from pathlib import Path
from typing import Any, Literal, TypeAlias

import yaml

Permission: TypeAlias = Literal["all", "personal"]


def humanize_bytes(speed: float, suffix: str = "B"):
    for unit in ("", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"):
        if abs(speed) < 1024.0:
            return f"{speed:3.2f} {unit}{suffix}"
        speed /= 1024.0
    return f"{speed:.1f}Yi{suffix}"


def init_log(debug: bool = False):
    if debug:
        consolelog_level = logging.DEBUG
    else:
        consolelog_level = logging.INFO

    logger = logging.getLogger("transmission-telegram-bot")
    logger.setLevel(logging.DEBUG)

    # create console handler with a higher log level
    consolelog = logging.StreamHandler()
    consolelog.setLevel(consolelog_level)

    # create formatter and add it to the handlers
    formatter = logging.Formatter("%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s")
    consolelog.setFormatter(formatter)

    # add the handlers to logger
    logger.addHandler(consolelog)

    return logger


def get_config(path: str):
    with Path(path).open("r") as ymlfile:
        cfg = yaml.safe_load(ymlfile)
    return cfg


def get_torrent_permission(config: Any, chat_id: str) -> Permission | None:
    if "allow_chat" in config["telegram"]:
        if config["telegram"]["allow_chat"]:
            torrent_permission = None
            for entry in config["telegram"]["allow_chat"]:
                if entry["telegram_id"] == chat_id:
                    torrent_permission = entry["torrent_permission"]
            return torrent_permission
        else:
            return None
    else:
        return None


def get_torrent_category(config: Any, chat_id: str):
    if "allow_chat" in config["telegram"]:
        if config["telegram"]["allow_chat"]:
            torrent_category = None
            for entry in config["telegram"]["allow_chat"]:
                if entry["telegram_id"] == chat_id:
                    if "allow_category" in entry:
                        torrent_category = entry["allow_category"]
            return torrent_category
        else:
            return None
    else:
        return None
