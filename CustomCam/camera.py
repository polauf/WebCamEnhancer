#!/usr/bin/env python3

"""Implements the CameraModifier class, which sets up and maintains the primary command loop."""

import logging
import os
import select
import sys
import time
from typing import Union

import cv2
import numpy as np
import pyvirtualcam

import CustomCam.utils as utils


class CameraModifier:
    """Camera stream modification class."""
    def __init__(self, input_camera: str, output_camera: str, filters: dict, show_fps: bool = False,
                 pref_width: Union[None, int] = None, pref_height: Union[None, int] = None, pref_fps: bool = None,
                 initial_filter: str = "NoFilter", logger: logging.Logger = utils.setup_logger('CameraModifier')):
        self.logger = logger
        self.input_camera = input_camera
        self.output_camera = output_camera
        self.show_fps = show_fps
        self.pref_fps = pref_fps

        self.pref_width = pref_width
        self.pref_height = pref_height
        self.width = None
        self.height = None
        self.fps = None

        self.filters = filters
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
        for filter_key in sorted(self.filters.keys()):
            self.logger.warning(f"• '{filter_key}': {self.filters[filter_key]}")
        self.logger.warning(f"\nOptions:")
        self.logger.warning(f"• 'f', 'flip': Flip camera")
        self.logger.warning(f"• 's', stats': Display statistics")
        self.logger.warning(f"• 'h', 'help': Get this help")
        self.logger.warning(f"• 'q', 'quit': Exit CustomCam")

    def handle_user_input(self, key: str) -> None:
        """Process user commands. Primarily by updating self_.filter.

        Args:
            key: User-provided command for processing.
        """
        if key is not None:
            if key.lower() in {'q', 'quit'}:
                self.logger.info('Exiting...')
                sys.exit()
            elif key.lower() in {'h', 'help'}:
                self.print_help()
            elif key in self.filters.keys():
                self._filter = key
                self.logger.info(self.filters[self._filter].switch_log)
            elif key.lower() in {'f', 'flip'}:
                self.flip_cam = not self.flip_cam
            elif key.lower() in {'s', 'stats'}:
                self.show_stats = not self.show_stats
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
        frame = self.filters[self._filter].apply(frame)
        return frame

    def start_input_camera(self, input_device: str) -> cv2.VideoCapture:
        """Create and return a cv2.VideoCapture object for the provided input device path.

        Args:
            input_device (str): Path to input device

        Returns:
            cv2.VideoCapture
        """

        # Set up webcam capture.
        in_cam = cv2.VideoCapture(input_device)

        # Verify input device
        if not in_cam.isOpened():
            self.logger.critical(f"Unable to capture input device '{input_device}'")
            self.logger.critical(f'Is your webcam currently in use?')
            sys.exit()

        # Incoming config
        if self.pref_width is not None:
            self.logger.debug(f"Setting input camera width to {self.pref_width}")
            in_cam.set(cv2.CAP_PROP_FRAME_WIDTH, self.pref_width)
        if self.pref_height is not None:
            self.logger.debug(f"Setting input camera height to {self.pref_height}")
            in_cam.set(cv2.CAP_PROP_FRAME_HEIGHT, self.pref_height)
        if self.pref_fps is not None:
            self.logger.debug(f"Setting input camera fps to {self.pref_fps}")
            in_cam.set(cv2.CAP_PROP_FPS, self.pref_fps)

        # Outgoing config
        self.width = int(in_cam.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(in_cam.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.fps = in_cam.get(cv2.CAP_PROP_FPS)
        self.logger.info(f"Input camera '{input_device}' started: ({self.width}x{self.height} @ {self.fps}fps)")

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
        self.logger.info(f"Output camera '{out_cam.device}' started: "
                         f"({out_cam.width}x{out_cam.height} @ {out_cam.fps}fps)")

        return out_cam

    def build_stats(self) -> str:
        """Construct on-screen statistics string.

        Returns:
            str
        """
        if self.show_stats:
            text = f"FPS: {int(1 / (time.time() - self.last_time))}\n"
            text += f"Filter: {self._filter}\n"
            text += f"Resolution: {self.out_cam.width}x{self.out_cam.height}\n"
        else:
            text = ''
        self.last_time = time.time()

        return text

    def run(self) -> None:
        """Launch input & output cameras and enter primary filter loop."""

        # Set up feeds
        self.in_cam = self.start_input_camera(self.input_camera)
        self.out_cam = self.start_output_camera(self.output_camera, self.width, self.height, self.fps,
                                                show_fps=self.show_fps, fmt=pyvirtualcam.PixelFormat.BGR)

        self.logger.info(f"{utils.Colors.GREEN}All set! Type 'h' or 'help' for commands.{utils.Colors.RESET}")

        self.last_time = time.time()

        while True:
            # Read frame from webcam.
            ret, frame = self.in_cam.read()
            if not ret:
                self.logger.critical('Unable to fetch frame')
                sys.exit()

            # Create functions for each of these
            frame = self.apply_filter(frame)

            # Add text overlap
            stats_text = self.build_stats()
            y0, dy = 50, 30
            for i, line in enumerate(stats_text.split('\n')):
                y = y0 + i*dy
                cv2.putText(frame, line, (10, y), cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 0), 2)

            # Flip frame
            if self.flip_cam:
                frame = np.fliplr(frame)

            # Send modified frame to virtual cam
            self.out_cam.send(frame)

            # Capture for user input
            i, o, e = select.select([sys.stdin], [], [], 0.001)
            key = sys.stdin.readline().strip() if i else None

            # Change filter
            if key is not None:
                self.handle_user_input(key)
