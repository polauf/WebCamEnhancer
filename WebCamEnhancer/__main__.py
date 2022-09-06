from WebCamEnhancer.core.utils import configure_logging
import logging
from WebCamEnhancer.constants import LOGGING_FILE

configure_logging(LOGGING_FILE, logging.INFO)

import WebCamEnhancer.modules.middleware
import WebCamEnhancer.modules.filters
from WebCamEnhancer.core.camera import CamerasWorker
from WebCamEnhancer.gui.preview import WebcamPreview
from WebCamEnhancer.gui.controler import Controler
from WebCamEnhancer.config import Configuration


Configuration.load_config()
control = Controler()
control.run()
Configuration.save_config()