from WebCamEnhancer.core.utils import configure_logging, init_gettext
import logging
from WebCamEnhancer.constants import LOGGING_FILE

init_gettext()
configure_logging(LOGGING_FILE, logging.INFO)

from WebCamEnhancer.config import Configuration
import WebCamEnhancer.modules.middleware
import WebCamEnhancer.modules.filters

from WebCamEnhancer.core.camera import CamerasWorker
from WebCamEnhancer.gui.preview import WebcamPreview
from WebCamEnhancer.gui.controler import Controler
from WebCamEnhancer.gui.settings import Setting


Configuration.load_config()
init_gettext(Configuration.get_custom_config(Setting)["language"])
control = Controler()
control.run()
Configuration.save_config()