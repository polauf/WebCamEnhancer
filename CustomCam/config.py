import cv2
import pathlib
import numpy as np


class Config:

    # Webcam image corrections
    HUE = 1.
    SATURATION = 1.1
    VALUE = 1.15

    RED = 1.25
    GREEN = .95
    BLUE = .85

    GAMMA = 1.68

    # initial zoom
    ZOOM = 1.6
    # sharpen
    SHARPEN = False

    # LMan How fast it will rotate
    ROTATION_RATE = -2.5
    # LMan Where is face picture. 
    FACE_IMAGE_PATH = "img/face.png"
    # LMan Where is rolling background picture.
    TEXT_IMAGE_PATH = "img/plate.png"
    # LMan Upscale RAAL rectangle. (Cover face)
    SCALE = 1.65
    # LMan Stop blocking after n frames. -1 is don't stop.
    LIFETIME = -1
    # Background path or RGB color tuple
    #TODO: Add gif support.
    BACKGROUND = "img/interview.png"
    # Background fallback color
    BACKGROUND_FALLBACK = (0,200,0)
    # Pixelate size
    PIXELATE_SIZE = (45, 45)
    # Away overlay
    AWAY_IMG = "img/away.png"

    # Away switch treshold
    AWAY_TRESHOLD = 0.2
    # Away after frames
    AWAY_FRAMES = 30
    PRESET_FRAMES = 80

    # Present default filter (also default start filter)
    PRESENT_FILTER = "Background"
    # Away default filter
    AWAY_FILTER = "Away"
    # prints state change in N seconds. 
    WARNING_SECS=4


def get_background(background_img=[]):
    """Evaluate if color shoud be returned or picture
      Default argument is storage. 
    """
    if not len(background_img):
        if Config.BACKGROUND is not None and len(Config.BACKGROUND) == 3: # color
            background_img.append(np.array([[list(Config.BACKGROUND)]],dtype='uint8'))
        elif isinstance(Config.BACKGROUND, str) and pathlib.Path(Config.BACKGROUND).is_file(): # path
            background_img.append(cv2.imread(Config.BACKGROUND))
        else:
            background_img.append(np.array([[list(Config.BACKGROUND_FALLBACK)]],dtype='uint8'))
    return background_img[0]