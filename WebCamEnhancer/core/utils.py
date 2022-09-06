import cv2, sys, gettext
import numpy as np
import logging
import logging.handlers
from ..constants import APP_NAME, TRANSLATIONS_DIR

gettext.bindtextdomain(APP_NAME, TRANSLATIONS_DIR)
gettext.textdomain(APP_NAME)

def init_gettext(lang=None):
    import builtins
    if not lang:
        builtins.__dict__['tt'] = gettext.gettext
    else:
        try:
            builtins.__dict__['tt'] = gettext.translation(
                'base',
                localedir=TRANSLATIONS_DIR,
                languages=[lang]
                ).gettext
        except FileNotFoundError:
            pass



class LoggingFormater(logging.Formatter):
    def formatException(self, exc_info):
        """
        Format an exception so that it prints on a single line.
        """
        result = super().formatException(exc_info)
        return repr(result)  # or format into one line however you want to

    def format(self, record):
        s = super().format(record)
        if record.exc_text:
            s = s.replace('\n', '')
        return s

def configure_logging(log_file, level):
    # force loggers of other packages (If this set to debug)
    logging.getLogger('numba').setLevel(logging.WARNING)
    logging.getLogger('matplotlib').setLevel(logging.WARNING)
    
    filehandler = logging.handlers.RotatingFileHandler(log_file, mode='a', maxBytes=5*1024*1024, 
                                 backupCount=2)
    streamHandler = logging.StreamHandler(sys.stdout)

    filehandler.setFormatter(LoggingFormater('%(asctime)s|%(levelname)s|%(message)s|',
                                  '%d/%m/%Y %H:%M:%S'))
    root = logging.getLogger(APP_NAME)
    root.setLevel(level)
    root.addHandler(filehandler)
    root.addHandler(streamHandler) 

logger = logging.getLogger(APP_NAME)


def rotate_image(image: np.array, angle: float) -> np.array:
  return cv2.warpAffine(
      image,
      cv2.getRotationMatrix2D(
          tuple(np.array(image.shape[1::-1]) / 2),
          angle,
          1.0
          ),
        image.shape[1::-1],
        flags=cv2.INTER_LINEAR
        )

def draw_on_image(bottom: np.array, top: np.array, x=0, y=0):
    (h, w) = top.shape[:2]
    y1, y2 = y, y + h
    x1, x2 = x, x + w
    
    x_lim = 0
    y_lim = 0
    if x2 >= bottom.shape[1]:
        x_lim = x2 - bottom.shape[1] + 1
        w -= x_lim
        x2 -= x_lim
    if y2 >= bottom.shape[0]:
        y_lim = y2 - bottom.shape[0] + 1
        h -= y_lim
        y2 -= y_lim

    alpha_top = top[:h, :w, 3] / 255.0
    alpha_bottom = 1.0 - alpha_top
    for c in range(0, 3):
        bottom[y1:y2, x1:x2, c] = (alpha_top * top[:h, :w, c] +
                                   alpha_bottom * bottom[y1:y2, x1:x2, c])
    if bottom.shape[2] == 4:
        bottom[y1:y2, x1:x2, 3] = np.maximum(top[:h, :w, 3], bottom[y1:y2, x1:x2, 3])