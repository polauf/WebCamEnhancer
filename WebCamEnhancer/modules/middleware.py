import cv2
import mediapipe as mp

from ..core.base import Middleware


CASCADE_FACE = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
SELFIE_SEGMENTATION = mp.solutions.selfie_segmentation.SelfieSegmentation(model_selection=1)

class Cascade(Middleware):

    CONFIG_TEMPLATE = {
        "scale_factor": 1.1,
        "min_neighbors": 7,
        "min_size_x": 100,
        "min_size_y": 100
    }

    def apply(self, frame):
        return CASCADE_FACE.detectMultiScale(
            cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY),
            scaleFactor=self.config['scale_factor'],
            minNeighbors=self.config['min_neighbors'],
            minSize=(self.config['min_size_x'], self.config['min_size_y']),
            flags=cv2.CASCADE_SCALE_IMAGE
        )

class Selfie(Middleware):

    def apply(self, frame):
        # To improve performance, optionally mark the image as not writeable
        frame.flags.writeable = False
        mask = SELFIE_SEGMENTATION.process(frame).segmentation_mask
        frame.flags.writeable = True
        return mask