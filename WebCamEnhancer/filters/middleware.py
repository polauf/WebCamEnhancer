"""
Implementation of Filter and subclasses witch should not be used in the end.
"""
import logging

import cv2
import mediapipe as mp


CASCADE_FACE = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
SELFIE_SEGMENTATION = mp.solutions.selfie_segmentation.SelfieSegmentation(model_selection=1)

class Filter:
    """Camera filter class. Takes in frame, modifies and returns frame."""
    def __init__(self, *args, **kwargs):
        self.switch_log = f"Switching to {self.__class__.__name__} filter."

    def __str__(self):
        """String representation."""
        return self.__class__.__doc__ or "<No description>"

    def apply(self, changer, frame):
        """Filter function, to be applied in descendant classes."""
        raise NotImplementedError


class Cascade(Filter):

    def apply(self, changer, frame):
        return CASCADE_FACE.detectMultiScale(
            cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY),
            scaleFactor=1.1,
            minNeighbors=7,
            minSize=(100, 100),
            flags=cv2.CASCADE_SCALE_IMAGE
        )

class Selfie(Filter):

    def apply(self, changer, frame):
        # To improve performance, optionally mark the image as not writeable
        frame.flags.writeable = False
        mask = SELFIE_SEGMENTATION.process(frame).segmentation_mask
        frame.flags.writeable = True
        return mask

class SelfieCascade(Filter):

    def apply(self, changer, frame):
        # To improve performance, optionally mark the image as not writeable
        frame.flags.writeable = False
        mask = SELFIE_SEGMENTATION.process(frame).segmentation_mask
        frame.flags.writeable = True
        return mask, CASCADE_FACE.detectMultiScale(
            cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY),
            scaleFactor=1.1,
            minNeighbors=7,
            minSize=(100, 100),
            flags=cv2.CASCADE_SCALE_IMAGE
        )
