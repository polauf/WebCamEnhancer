import logging
import os
import select
import sys
import time
from typing import Optional

import cv2
import numpy as np
import pyvirtualcam

from utils import setup_logger, Colors
from config import Config

def zoom_at(img, zoom, coord=None, method=cv2.INTER_CUBIC):
    """
    Simple image zooming without boundary checking.
    Centered at "coord", if given, else the image center.

    img: numpy.ndarray of shape (h,w,:)
    zoom: float
    coord: (float, float)
    """
    # Translate to zoomed coordinates
    h, w, _ = [ zoom * i for i in img.shape ]
    
    if coord is None: cx, cy = w/2, h/2
    else: cx, cy = [ zoom*c for c in coord ]
    
    img = cv2.resize( img, (0, 0), fx=zoom, fy=zoom, interpolation=method)
    return img[ int(round(cy - h/zoom * .5)) : int(round(cy + h/zoom * .5)),
               int(round(cx - w/zoom * .5)) : int(round(cx + w/zoom * .5)),
               : ]
    


class CameraModifier:
    """Camera stream modification class."""
    def __init__(
        self,
        input_camera: str,
        output_camera: str,
        filters: dict,
        pref_width:  Optional[int] = None,
        pref_height: Optional[int] = None,
        pref_fps: bool = None,
        initial_filter: str = Config.PRESENT_FILTER,
        logger: logging.Logger = setup_logger('CameraModifier')
    ):
        self.logger = logger
        self.input_camera = input_camera
        self.output_camera = output_camera
        self.pref_fps = pref_fps

        self.pref_width = pref_width
        self.pref_height = pref_height
        self.width = None
        self.height = None
        self.fps = None

        self.zoom = Config.ZOOM

        self.filters = filters
        self.filter_keys = {k.lower():k for k in self.filters.keys()}
        self._filter = initial_filter

        self.in_cam = None
        self.out_cam = None

        self.flip_cam = False
        self.show_filter_name = False
        self.show_stats = False
        self.last_time = None

    def print_help(self) -> None:
        """Print command help to logger."""
        self.logger.warning(f"Filters:")
        length = 15
        for filter_key in sorted(self.filters.keys()):
            self.logger.warning(f"\t{filter_key:<{length}} {self.filters[filter_key]}")
        self.logger.warning(f"\nOptions:")
        self.logger.warning(f"\t{'f, flip':<{length}} Flip the camera.")
        self.logger.warning(f"\t{'s, stats':<{length}} Display information about stream.")
        self.logger.warning(f"\t{'z+, z-':<{length}} Zoom picture.")
        self.logger.warning(f"\t{'a, p':<{length}} Fast switch between default filters: Away ({Config.AWAY_FILTER}) or Present ({Config.PRESENT_FILTER}).")
        self.logger.warning(f"\t{'h, help':<{length}} Get this help.")
        self.logger.warning(f"\t{'q, quit':<{length}} Exits the application.")
        

    def handle_user_input(self, key: str) -> None:
        """Process user commands. Primarily by updating self_.filter.

        Args:
            key: User-provided command for processing.
        """
        if key is not None:
            key = key.lower()
            if key in {'q', 'quit'}:
                self.logger.info('Exiting...')
                sys.exit()
            elif key in {'h', 'help'}:
                self.print_help()
            elif key in {'f', 'flip'}:
                self.flip_cam = not self.flip_cam
            elif key in {'s', 'stats'}:
                self.show_stats = not self.show_stats
            elif key in {'a', 'away'}:
                self._filter = Config.AWAY_FILTER
                self.logger.info("User away")
            elif key in {'p', 'present'}:
                self._filter = Config.PRESENT_FILTER
                self.logger.info("User present")
            elif key == 'z+':
                self.zoom += 0.1
                self.logger.info(f"Zoom {self.zoom:.1f}x")
            elif key == 'z-':
                if self.zoom > 1:
                    self.zoom -= 0.1
                self.logger.info(f"Zoom {self.zoom:.1f}x")
            elif key := self.filter_keys.get(key, None):
                self._filter = key
                self.logger.info(self.filters[self._filter].switch_log)
            else:
                self.logger.error(f"Key '{key}' not recognised.")
                self.logger.debug(f"Valid keys: {self.filters.keys()}")
                self.print_help()
        else:
            self._filter = "none"

    def apply_filter(self, frame: np.array) -> np.array:
        """Apply the currently selected filter to the provided frame.

        Args:
            frame (np.array): Single frame provided by input camera feed.

        Returns:
            numpy array with the same shape as frame and the current filter effect applied.
        """
        frame = self.filters[self._filter].apply(self, frame)
        return frame

    def start_input_camera(self, input_device: str) -> cv2.VideoCapture:
        """Create and return a cv2.VideoCapture object for the provided input device path.

        Args:
            input_device (str): Path to input device

        Returns:
            cv2.VideoCapture
        """

        in_cam = cv2.VideoCapture(input_device)

        if not in_cam.isOpened():
            self.logger.critical(f"Unable to capture input device '{input_device}'")
            self.logger.critical(f'Is your webcam currently in use?')
            sys.exit()
        if self.pref_width is not None:
            self.logger.debug(f"Setting input camera width to {self.pref_width}")
            in_cam.set(cv2.CAP_PROP_FRAME_WIDTH, int(self.pref_width))
        if self.pref_height is not None:
            self.logger.debug(f"Setting input camera height to {self.pref_height}")
            in_cam.set(cv2.CAP_PROP_FRAME_HEIGHT, int(self.pref_height))
        if self.pref_fps is not None:
            self.logger.debug(f"Setting input camera fps to {self.pref_fps}")
            in_cam.set(cv2.CAP_PROP_FPS, self.pref_fps)

        return in_cam

    def start_output_camera(self, output_device: str, width: int, height: int, fps_out: int,
                            fmt: pyvirtualcam.PixelFormat = pyvirtualcam.PixelFormat.BGR,
                            show_fps: bool = False) -> pyvirtualcam.camera.Camera:
        """Create and return a pyvirtualcam.camera.Camera object for the provided output device path.

        Args:
            output_device (str): Path to virtual output camera.
            width (int): Width of output device.
            height (int): Height of output device.
            fps_out (int): FPS of output device.
            fmt (pyvirtualcam.PixelFormat): pyvirtualcam PixelFormat for output device.
            show_fps (bool): Whether to print fps to stdout.

        Returns:
            pyvirtualcam.camera.Camera
        """
        if not os.path.exists(output_device):
            self.logger.critical(f"Invalid output device: '{output_device}'")
            self.logger.critical(f"Have you created a virtual output camera?")
            sys.exit()

        try:
            out_cam = pyvirtualcam.Camera(width, height, fps_out, fmt=fmt, print_fps=show_fps, device=output_device)
        except RuntimeError:
            self.logger.critical(f"Failed to connect to output device: '{output_device}' - "
                                 f"have you created a virtual camera with 'sudo modprobe v4l2loopback devices=1'?")
            sys.exit()

        return out_cam

    def build_stats(self) -> str:
        """Construct on-screen statistics string.

        Returns:
            str
        """
        text = f"FPS: {int(1 / (time.perf_counter() - self.last_time))}\n"
        text += f"Filter: {self._filter}\n"
        text += f"Resolution: {self.out_cam.width}x{self.out_cam.height}\n"
        self.last_time = time.perf_counter()

        return text

    def run(self) -> None:
        """Launch input & output cameras and enter primary filter loop."""

        # Set input feed
        self.in_cam = self.start_input_camera(self.input_camera)

        self.width = int(self.in_cam.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.in_cam.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.fps = self.in_cam.get(cv2.CAP_PROP_FPS)
        self.logger.info(f"Input camera '{self.input_camera}' started: ({self.width}x{self.height} @ {self.fps}fps)")

        # Set output feed
        self.out_cam = self.start_output_camera(self.output_camera, self.width, self.height, self.fps,
                                                fmt=pyvirtualcam.PixelFormat.BGR)

        self.logger.info(f"Output camera '{self.out_cam.device}' started: "
                    f"({self.out_cam.width}x{self.out_cam.height} @ {self.out_cam.fps}fps)")

        self.logger.info(f"{Colors.GREEN}All set! Type 'h' or 'help' for commands.{Colors.RESET}")

        self.last_time = time.perf_counter()

        # lookup table for gamma correction
        lookUpTable = np.empty((1,256), np.uint8)
        for i in range(256):
            lookUpTable[0,i] = np.clip(pow(i / 255., Config.GAMMA) * 255., 0, 255)

        while True:
            # Read frame from webcam.
            ret, frame = self.in_cam.read()

            if not ret:
                self.logger.critical('Unable to fetch frame')
                sys.exit()
            
            if Config.SHARPEN:
                frame = cv2.filter2D(frame, -1, np.array([[0,-1,0], [-1,5,-1], [0,-1,0]]))

            frame = zoom_at(frame, self.zoom)

            frame = cv2.LUT(frame, lookUpTable)

            if Config.HUE != 1. or Config.SATURATION != 1. or Config.VALUE != 1:
                (h, s, v) = cv2.split(cv2.cvtColor(frame, cv2.COLOR_BGR2HSV).astype("float32"))

                if Config.HUE != 1.:
                    h = np.clip(h*Config.HUE,0,255)
                if Config.SATURATION != 1.:
                    s = np.clip(s*Config.SATURATION,0,255)
                if Config.VALUE != 1.:
                    v = np.clip(v*Config.VALUE,0,255)

                frame = cv2.cvtColor(cv2.merge([h,s,v]).astype("uint8"), cv2.COLOR_HSV2BGR)

            if Config.RED != 1. or Config.GREEN != 1. or Config.BLUE != 1:
                (b, g, r) = cv2.split(frame.astype("float32"))
                
                if Config.RED != 1.:
                    r = np.clip(r*Config.RED,0,255)
                if Config.GREEN != 1.:
                    g = np.clip(g*Config.GREEN,0,255)
                if Config.BLUE != 1.:
                    b = np.clip(b*Config.BLUE,0,255)

                frame = cv2.merge([b,g,r]).astype("uint8")

            frame = self.apply_filter(frame)

            # Adds info
            if self.show_stats:
                stats_text = self.build_stats()
                y0, dy = 50, 30
                for i, line in enumerate(stats_text.split('\n')):
                    y = y0 + i*dy
                    cv2.putText(frame, line, (5, y), cv2.FONT_HERSHEY_PLAIN, 1, (0, 255, 255), 2)

            # Flip frame
            if self.flip_cam:
                frame = np.fliplr(frame)

            self.out_cam.send(frame)

            # Handle user input
            i, _, _ = select.select([sys.stdin], [], [], 0.001)
            key = sys.stdin.readline().strip() if i else None
            if key is not None:
                self.handle_user_input(key)
