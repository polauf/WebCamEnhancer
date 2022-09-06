from typing import Optional

import cv2, json
from pathlib import Path
from collections import UserDict
from copy import deepcopy
from threading import Lock
from mergedeep import  merge
import distutils.dir_util

from .constants import CONFIG_DIR, BASE_CONFIG, PICTURES_DIR, FALLBACK_PICTURES_DIR
from .core.base import ModuleController

class ConfigEncoder(json.JSONEncoder):
    "Encodes ConfigGroups and Paths to JSON."

    def default(self, item):
        if isinstance(item, ConfigGroup):
            return item.data
        elif isinstance(item, Path):
            try:
                return str(item.relative_to(CONFIG_DIR))
            except ValueError:
                return str(item)
        else:
            raise TypeError(f"Unexpected type {item.__class__.__name__}")

class ConfigGroup(UserDict):
    "Dict with lock and unability to make new keys. Used for Config."
    def __init__(self, data: Optional[dict] = None):
        self.data = data or {}
        self._lock = Lock()

    def __getitem__(self, key):
        with self._lock:
            value = self.data[key]
        return value

    def __setitem__(self, key, value) -> None:
        try:
            item = self.data[key]
        except KeyError:
            raise KeyError("Config keys are frozen.")
        with self._lock:
            self.data[key] = value

def config_decoder(obj: dict) -> ConfigGroup:
    "Cast ConfigGroups and relative Paths sets absolute from config directory."
    for key, value in obj.items():
        if isinstance(value, str) and key.endswith("_path"):
            path = Path(value)
            if not path.is_absolute():
                path = CONFIG_DIR / path
            obj[key] = path
    return ConfigGroup(obj)


class Config(ConfigGroup):
    "Main config. Handles loading and default values."

    CUSTOM_CLASSES = []

    def generate_default(self) -> dict:
        template = {}
        for group_name, modules in ModuleController.MODULES.items():
            template[group_name] = {}
            for module in modules:
                if module.CONFIG_TEMPLATE:
                    template[group_name][module.__name__] = config_decoder(deepcopy(module.CONFIG_TEMPLATE))
        for klass in Configuration.CUSTOM_CLASSES:
            if hasattr(klass, "CONFIG_TEMPLATE"):
                template[klass.__name__] = config_decoder(deepcopy(klass.CONFIG_TEMPLATE))
        return template

    def get_custom_config(self, klass) -> dict:
        return self.get(klass.__name__, {})

    def get_module_config(self, klass) -> dict: 
        group = self[klass.__mro__[1].__name__]
        return group.get(klass.__name__, {})

    def _make_user_setting(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        distutils.dir_util.copy_tree(str(FALLBACK_PICTURES_DIR), str(PICTURES_DIR))

    def load_config(self, path: Optional[Path] = None) -> None:
        defaults = self.generate_default()
        if path is None and not BASE_CONFIG.exists():
            self._make_user_setting()
            self.data = defaults
        else:
            try:
                with open(path or BASE_CONFIG) as fh:
                    data = json.JSONDecoder(object_hook=config_decoder).decode(fh.read())
                    try:
                        merge(defaults, dict(data)) # Develop merge config with new items
                        with self._lock:
                            self.data = defaults
                    except TypeError:
                        with self._lock:
                            self.data = data
            except json.JSONDecodeError:
                self._make_user_setting()
                raise ValueError("Corrupted config file. Re-run the applicattion.")

    def save_config(self, path: Optional[Path] = None) -> None:
        with open(path or BASE_CONFIG,'w') as fh:
            with self._lock:
                data = dict(self.data)
            json.dump(data, fh, indent=4, cls=ConfigEncoder)


# one global
Configuration = Config()

