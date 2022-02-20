#!/usr/bin/env python3

"""Camera filter classes, for applying various per-frame effects.

Each class defines a specific frame manipulation and all classes are discovered upon launch.
Therefore, additional filters can be added here by simply creating a new class that:
- Inherits from `filters.Filter`
- Implements a `__str__` method that return string containing a short description of the filter.
- Implements an `apply` method which takes a frame (as a `np.array`), applies filter logic and returns that a `np.array`.
- Does not share a name with any existing class or input command.
"""

import logging
from typing import Union

import cv2
import mediapipe as mp
import numpy as np


CASCADE_FACE = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
SELFIE_SEGMENTATION = mp.solutions.selfie_segmentation.SelfieSegmentation(model_selection=1)


class Filter:
    """Camera filter class. Takes in frame, modifies and returns frame."""
    def __init__(self, logger: Union[None, logging.Logger] = None, *args, **kwargs):
        super(Filter, self).__init__(*args, **kwargs)
        self.logger = logger
        self.switch_log = f"Switching to {self.__class__.__name__} filter."

    def __str__(self):
        """String representation, to be applied in descendant classes."""
        raise NotImplementedError

    def apply(self, frame: np.array) -> np.array:
        """Filter function, to be applied in descendant classes."""
        raise NotImplementedError


class NoFilter(Filter):
    """Apply no filter effect."""
    def __init__(self, *args, **kwargs):
        super(NoFilter, self).__init__(*args, **kwargs)

    def __str__(self):
        return f"Applies no filters."

    def apply(self, frame: np.array) -> np.array:
        """Return frame without any alteration.

        Args:
            frame (np.array): Frame from input camera.

        Returns:
            frame
        """
        return frame
        

class Shake(Filter):
    """Shake two channels horizontally every frame."""
    def __init__(self, *args, **kwargs):
        super(Shake, self).__init__(*args, **kwargs)
        self._frame_count = 0

    def __str__(self):
        return f"Shake two channels horizontally."

    def apply(self, frame: np.array) -> np.array:
        """Apply shake effect to provided frame.

        Args:
            frame (np.array): Frame from input camera.

        Returns:
            'Filtered' frame
        """
        # Shake two channels horizontally each frame.
        channels = [[0, 1], [0, 2], [1, 2]]

        dx = 15 - self._frame_count % 5
        c1, c2 = channels[self._frame_count % 3]
        frame[:, :-dx, c1] = frame[:,  dx:, c1]
        frame[:,  dx:, c2] = frame[:, :-dx, c2]

        self._frame_count += 1

        return frame


class BlurSat(Filter):
    """Blur background according to saturation.

    Based on:
        https://www.learnpythonwithrune.org/opencv-python-a-simple-approach-to-blur-the-background-from-webcam/
    """
    def __init__(self, *args, **kwargs):
        super(BlurSat, self).__init__(*args, **kwargs)

    def __str__(self):
        return f"Blur background via saturation detection."
    
    def apply(self, frame: np.array) -> np.array:
        """Apply saturation-based blur effect to provided frame.

        Args:
            frame (np.array): Frame from input camera.

        Returns:
            'Filtered' frame
        """
        # TODO: Fix, doesn't seem to work properly
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, (0, 75, 40), (180, 255, 255))
        mask_3d = np.repeat(mask[:, :, np.newaxis], 3, axis=2)
        blurred_frame = cv2.blur(frame, (25, 25), 0)
        frame = np.where(mask_3d == (255, 255, 255), frame, blurred_frame)

        return frame


class BlurBox(Filter):
    """Detect face with cascade, blur everything else.

    Based on:
        https://www.data-stats.com/blurring-background-and-foreground-in-images-using-opencv/
    """
    def __init__(self, *args, **kwargs):
        super(BlurBox, self).__init__(*args, **kwargs)
        self._frame_count = 0
        self.faces = []

    def __str__(self):
        return f"Blur background via single face detection."
    
    def apply(self, frame: np.array) -> np.array:
        """Apply facial recognition-based blur effect to provided frame.

        Args:
            frame (np.array): Frame from input camera.

        Returns:
            'Filtered' frame
        """
        # Detects face, as square based on cascade_face xml, and rewrites over pixelated
        self._frame_count += 1

        grayscale = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) 

        # Improve performance by update face identification every X frames
        if self._frame_count % 30 == 0 or len(self.faces) == 0:
            self.faces = CASCADE_FACE.detectMultiScale(grayscale, 1.3, 5)

        # Save faces
        roi_faces = [frame[y:y+h, x:x+w].copy() for x, y, w, h in self.faces]

        # Pixelate frame
        px_w, px_h = (128, 128)
        height, width, n_channels = frame.shape
        temp = cv2.resize(frame, (px_w, px_h), interpolation=cv2.INTER_LINEAR)
        frame = cv2.resize(temp, (width, height), interpolation=cv2.INTER_NEAREST)

        # Restore faces
        for i, (x, y, w, h) in enumerate(self.faces):
            frame[y:y+h, x:x+w] = roi_faces[i]

        return frame


class Segment(Filter):
    """Blur background with mediapipe selfie segmentation.

    Based on:
        # Docs: https://google.github.io/mediapipe/solutions/selfie_segmentation.html
    """
    def __init__(self, *args, **kwargs):
        super(Segment, self).__init__(*args, **kwargs)

    def __str__(self):
        return f"Blur background using SelfieSegmentation by mediapipe."
    
    def apply(self, frame: np.array) -> np.array:
        """Apply segmentation-based background blurring to provided frame.

        Args:
            frame (np.array): Frame from input camera.

        Returns:
            'Filtered' frame
        """
        # To improve performance, optionally mark the image as not writeable
        frame.flags.writeable = False
        segment = SELFIE_SEGMENTATION.process(frame)
        frame.flags.writeable = True

        # Identify foreground segment
        foreground = np.stack((segment.segmentation_mask,) * 3, axis=-1) > 0.1

        # Pixelate for background
        px_w, px_h = (128, 128)
        height, width, n_channels = frame.shape
        temp = cv2.resize(frame, (px_w, px_h), interpolation=cv2.INTER_LINEAR)
        pixelated = cv2.resize(temp, (width, height), interpolation=cv2.INTER_NEAREST)

        # Fill segments as required
        frame = np.where(foreground, frame, pixelated)

        return frame


class Pixel(Filter):
    """Blur foreground with mediapipe selfie segmentation.

    Based on:
        # Docs: https://google.github.io/mediapipe/solutions/selfie_segmentation.html
    """
    def __init__(self, *args, **kwargs):
        super(Pixel, self).__init__(*args, **kwargs)

    def __str__(self):
        return f"Pixelate individuals in the foreground."

    def apply(self, frame: np.array) -> np.array:
        """Apply segmentation-based foreground blurring to provided frame.

        Args:
            frame (np.array): Frame from input camera.

        Returns:
            'Filtered' frame
        """
        # To improve performance, optionally mark the image as not writeable
        frame.flags.writeable = False
        segment = SELFIE_SEGMENTATION.process(frame)
        frame.flags.writeable = True

        # Identify foreground segment
        foreground = np.stack((segment.segmentation_mask,) * 3, axis=-1) > 0.1

        # Pixelate for background
        px_w, px_h = (128, 128)
        height, width, n_channels = frame.shape
        temp = cv2.resize(frame, (px_w, px_h), interpolation=cv2.INTER_LINEAR)
        pixelated = cv2.resize(temp, (width, height), interpolation=cv2.INTER_NEAREST)

        # Fill segments as required
        frame = np.where(foreground, pixelated, frame)

        return frame


class Gray(Filter):
    """Convert frame to grayscale."""
    def __init__(self, *args, **kwargs):
        super(Gray, self).__init__(*args, **kwargs)

    def __str__(self):
        return f"Apply grayscale."

    def apply(self, frame: np.array) -> np.array:
        """Apply simple grayscale effect to provided frame.

        Args:
            frame (np.array): Frame from input camera.

        Returns:
            'Filtered' frame
        """
        grayscale = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        frame = np.repeat(grayscale, 3).reshape(frame.shape)
        return frame


class Sepia(Filter):
    """Apply classic sepia filter.

    Based on:
        https://gist.github.com/FilipeChagasDev/bb63f46278ecb4ffe5429a84926ff812
    """
    def __init__(self, *args, **kwargs):
        super(Sepia, self).__init__(*args, **kwargs)

    def __str__(self):
        return f"Apply sepia effect."
    
    def apply(self, frame: np.array) -> np.array:
        """Apply sepia effect to provided frame.

        Args:
            frame (np.array): Frame from input camera.

        Returns:
            'Filtered' frame
        """
        grayscale = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        grayscale_norm = np.array(grayscale, np.float32)/255

        # Solid color
        sepia = np.ones(frame.shape)
        sepia[:, :, 0] *= 153  # Blue channel
        sepia[:, :, 1] *= 204  # Green channel
        sepia[:, :, 2] *= 255  # Red channel

        # Hadamard
        sepia[:, :, 0] *= grayscale_norm  # Blue channel
        sepia[:, :, 1] *= grayscale_norm  # Green channel
        sepia[:, :, 2] *= grayscale_norm  # Red channel

        sepia = np.array(sepia, np.uint8)
        return sepia
