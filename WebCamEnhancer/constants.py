from pathlib import Path
from appdirs import user_data_dir 
import tkinter as tk



APP_NAME = "WebCam Enhancer"
APP_AUTHOR = "Matouš Polauf"
APP_AUTHOR_SHORT = "MPStuff"
APP_VERSION = "0.5.1"

CONFIG_DIR = Path(user_data_dir(APP_NAME, APP_AUTHOR_SHORT))
BASE_CONFIG = CONFIG_DIR / "config.json"
LOGGING_FILE = CONFIG_DIR / "log.log"
PICTURES_DIR = CONFIG_DIR / "img"
FALLBACK_PICTURES_DIR = Path(__file__).parent / "img"
TRANSLATIONS_DIR = Path(__file__).parent / "locales"

ICON = str(Path(__file__).parent / "icons/48x48.png")