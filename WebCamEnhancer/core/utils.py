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


def resolve_xy_center(top_shape, bottom_shape, xy=None, center=None):
    x1, y1 = 0,0
    h1, w1 = top_shape
    h, w = bottom_shape
    if xy is not None:
        x, y = xy
    elif center is not None:
        cx, cy = center
        x = int(cx - w1/2.)
        if 0>x:
            x1 = -x
            w = w1 + x
            x = 0  
        else:
            if (cx + w1/2) >= w:
                w1 = w - x
            w = w1 

        y = int(cy - h1/2.)
        if 0 > y:
            y1 = -y
            h = h1 + y
            y = 0
        else:
            if (cy + h1/2) >= h:
                h1 = h - y
            h = h1

    else:
        raise ValueError("Need 'xy' or 'center' keyword argument.")
    return (x, y, w,h),(x1,y1,w1,h1)

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

def draw_on_image(bottom: np.array, top: np.array, xy=None, center=None,transparency=0):
    ((x, y, w, h), (bx, by, bw, bh)) = resolve_xy_center(top.shape[:2],bottom.shape[:2], xy, center)
    alpha_top = top[by:by+bh, bx:bx+bw, 3] / 255.0
    alpha_bottom = 1.0 - alpha_top
    for c in range(3):
        # cv2.rectangle(bottom,(x,y), (x+w, y+h), (0,255,0),2)
        bottom[y:y+h, x:x+w, c] = (
            alpha_top * top[by:by+bh, bx:bx+bw, c] +
            alpha_bottom * bottom[y:y+h, x:x+w, c]
            )
    if bottom.shape[2] == 4:
        bottom[y:y+h, x:x+w, 3] = np.maximum(top[by:by+bh, bx:bx+bw, 3], bottom[y:y+h, x:x+w, 3])*(1.-transparency/255.)