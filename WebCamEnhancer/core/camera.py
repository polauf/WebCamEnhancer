import cv2, pyvirtualcam, threading, queue, copy
import numpy as np
from typing import Optional
from pathlib import Path

from ..config import Configuration
from .base import ModuleController
from .utils import logger

class CameraError(Exception):
    pass

def start_input(input_device: str, 
                width: Optional[int], height: Optional[int], fps: Optional[float]
                ) -> tuple[cv2.VideoCapture, dict]:
    """
    Starts input_cam capture thread and processing thread.
    """
    cam = cv2.VideoCapture(input_device)
    if not cam.isOpened():
        raise CameraError(f"Unable to capture input device '{input_device}'")
    if width is not None:
        cam.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    if height is not None:
        cam.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    if fps is not None:
        cam.set(cv2.CAP_PROP_FPS, fps)

    width, height, fps = (
        int(cam.get(cv2.CAP_PROP_FRAME_WIDTH)),
        int(cam.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        cam.get(cv2.CAP_PROP_FPS)
    )
    logger.info("Acquired input camera '%s' with config %dx%dpx %dfps", input_device, width, height, fps)
    return (cam, {
        "width": width,
        "height": height,
        "fps": fps
    })

def start_output(output_device: str, width: int, height: int, fps: int,
                pixel_format: pyvirtualcam.PixelFormat = pyvirtualcam.PixelFormat.BGR,
                ) -> tuple[pyvirtualcam.camera.Camera, dict]:
    if not Path(output_device).exists():
        raise CameraError(f"Invalid output device: '{output_device}'")
    try:
        cam = pyvirtualcam.Camera(width=int(width), height=int(height), fps=fps, fmt=pixel_format, device=output_device)
    except RuntimeError as r:
        raise CameraError(f"Failed to connect to output device: '{output_device}'. {r}")
    logger.info("Acquired output stream '%s' with config %dx%dpx %dfps",output_device, cam.width, cam.height, cam.fps)
    return (cam, {
        "width": cam.width,
        "height": cam.height,
        "fps": cam.fps
    })

class CamerasWorker:

    def __init__(self, in_cam, out_cam, width=None, height=None, fps=None, preview=True, stream=True):
        self.in_cam_name = in_cam
        self.out_cam_name = out_cam
        self._setup_data = {"width": width, "height": height, "fps": fps}
        self._input = None
        self._output = None
        self._input_props = None
        self._output_props = None
        self.resolution = None
        self.preview = preview
        self.streaming = stream

        self._active_filters = tuple()

        self._middleware = {}
        self._filters = {}

        self._stop = threading.Event()
        self._error = threading.Event()
        self._image_queue = queue.Queue()
        
        self._errors = []
        self._threads = []

        self._max_error_frames = 10

    @property
    def filters(self):
        return self._active_filters

    @filters.setter
    def filters(self, filters):
        self._active_filters = tuple(filters)
        logger.info("Filters changed to: %s", self._active_filters)

    @property
    def preview(self):
        return self._preview

    @preview.setter
    def preview(self, preview):
        self._preview = bool(preview)
        logger.info("Preview is%ssend.", " " if self._preview else " not ")

    @property
    def streaming(self):
        return self._streaming

    @streaming.setter
    def streaming(self, stream):
        self._streaming = bool(stream)
        logger.info("%streaming.", "S" if self._streaming else "Not s")

    @property
    def input_cam_properties(self):
        return self._input_props

    @property
    def output_cam_properties(self):
        return self._output_props

    def prepare(self):
        self._input_cam, self._input_props = start_input(self.in_cam_name, **self._setup_data)
        self._output_cam, self._output_props = start_output(self.out_cam_name, **self._input_props)
        self.resolution = (self._input_props["width"], self._input_props["height"])

        self._middleware = {}
        configs = Configuration.get("Middleware", {})
        for m in ModuleController.MODULES["Middleware"]:
            try:
                mdl = m(configs.get(m.__name__, {}))
                mdl.prepare(self.resolution)
                self._middleware[m.__name__] = mdl
            except Exception as e:
                raise CameraError(f"Failed to prepare Middleware '{m.__name__}': {e}")
        logger.debug("Middleware: %s", self._middleware.keys())

        self._filters = {}
        configs = Configuration.get("Filter", {})
        for f in ModuleController.MODULES["Filter"]:
            try:
                flt = f(configs.get(f.__name__, {}), self._middleware, self)
                flt.prepare(self.resolution)
                self._filters[f.__name__] = flt
            except Exception as e:
                raise CameraError(f"Failed to prepare Filter '{f.__name__}': {e}")
        logger.debug("Filters: %s", self._filters.keys())

        self._drivers = {}
        configs = Configuration.get("Driver", {})
        for d in ModuleController.MODULES["Driver"]:
            try:
                drv = d(configs.get(f.__name__, {}), self._middleware, self)
                drv.prepare()
                self._drivers[d.__name__] = drv
            except Exception as e:
                raise CameraError(f"Failed to prepare Driver '{d.__name__}': {e}")
        logger.debug("Drivers: %s", self._drivers.keys())



    def stop(self):
        logger.info("Stopping aquisition.")
        self._stop.set()
        while self._threads:
            thrd = self._threads.pop()
            thrd.join()
        self._input_cam.release()
        self._output_cam.close()
        logger.info("Stoped.")

    def start(self):
        self._max_error_frames = 10
        self.prepare()
        input_queue = queue.Queue()
        self._image_queue = queue.Queue()

        def input_worker():
            error_counter = 0
            while not self._stop.is_set():
                ret, frame = self._input_cam.read()
                if not ret:
                    logger.warning("Unsuccessful aquisition of frame. %d until exit", self._max_error_frames - error_counter)
                    if error_counter > self._max_error_frames:
                        self._errors.append((CameraError, "Unable to capture frame from camera."))
                        self._error.set()
                        break
                    error_counter += 1
                input_queue.put(frame)

        input_thread = threading.Thread(target=input_worker,daemon=True)

        def processing_worker():
            error_counter = 0
            raw_frame = None
            while not self._stop.is_set():
                frame = input_queue.get()
                if frame is not None:
                    try:
                        # middleware
                        raw_frame = frame.copy()
                        for m in self._middleware.values():
                            # set actual frame for processiong if needed by filters
                            m.set_frame(raw_frame)

                        for name in self._active_filters:
                            # logger.debug("Using %s", name)
                            frame = self._filters[name].apply(frame)

                        # handle outputs
                        if self._streaming:
                            self._output_cam.send(frame)
                        if self._preview:
                            self._image_queue.put(frame)

                        # Handle drivers
                        for d in self._drivers.values():
                            d.resolve()
                    except Exception as e:
                        logger.error(e)
                        # fail if to mutch error frames
                        if error_counter > self._max_error_frames:
                            try:
                                self._errors.append((e, e.msg))
                            except Exception:
                                self._errors.append((CameraError, "Unable to process frame from camera."))
                            self._error.set()
                            break
                        break
                    error_counter += 1

        process_thread = threading.Thread(target=processing_worker,daemon=True)

        input_thread.start()
        process_thread.start()
        logger.info("Started aquisition.")

    def get_frame(self, block=True, timeout: int = 0.1)-> Optional[np.array]:
        if not self.preview:
            raise CameraError("Preview disabled.")
        try:
            frame = self._image_queue.get(block, timeout)

            # Reraise last error in threads
            if frame is None and self._error.is_set():
                try:
                    err = self.errors.pop()
                    raise CameraError(f"{err[0]}: {err[1]}")
                except IndexError:
                    raise CameraError("Unable to fetch frame.")
            return frame
        except queue.Empty:
            # return None if timeouted
            pass
