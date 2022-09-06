from pathlib import Path
import matplotlib.colors
import numpy as np


class ModuleController:
    """Collector for all behaviours of application. Like Filters, Middleware, Drivers."""

    MODULES = {}

    CONFIG_TEMPLATE = {}

    def __init__(self, config):
        self.config = config

    def __init_subclass__(cls):
        if cls.__mro__[1] is ModuleController:
            cls.MODULES[cls.__name__] = []
        elif cls.__mro__[2] is ModuleController:
            cls.MODULES[cls.__mro__[1].__name__].append(cls)
        else:
            raise TypeError(("Module classes can't inherit after inherited from group class. "
            "For example with Filter: ModuleController->Filter->MyNiceFilter->MySpecificFilter "
            "where MySpecificFilter child is not allowed."))

    def get_existing_file(self, key) -> str:
        "Gets file from filesystem or backup file from package."
        value = self.config[key]
        if Path(value).exists():
            return str(value)
        else:
            fallback = Path(__file__).parent/self.CONFIG_TEMPLATE[key]
            if not fallback.exists():
                raise ValueError(f"Fallback file '{self.CONFIG_TEMPLATE[key]}' not found in package.")
            return str(fallback)

    @staticmethod
    def hex2color(color_hex: str):
        return np.asarray(np.array(matplotlib.colors.to_rgb(color_hex))*255., np.uint8)


class Filter(ModuleController):
    """Apply specific operation to camera frame."""

    def __init__(self, config, middleware, worker):
        super().__init__(config)
        self.middleware = middleware
        self.worker = worker

    def prepare(self, resolution):
        pass

    def apply(self, frame):
        raise NotImplemented

class Middleware(ModuleController):
    """ Apply resusable operation to the camera frame."""

    def __init__(self, config):
        super().__init__(config)
        self._done = False
        self._frame = None
        self._result = None

    def prepare(self, resolution):
        pass

    def apply(self, frame):
        raise NotImplemented

    def get(self):
        "Used by other classes to collect result of operation."
        if self._done:
            return self._result
        else:
            if self._frame is None:
                raise ValueError("self.frame is None. Probably set_frame() was never called.")
            self._result = self.apply(self._frame)
            self._done = True
        return self._result

    def set_frame(self, frame):
        self._frame = frame
        self._done = False

class Driver(ModuleController):
    """Implements behaviour based on state and middleware of Application."""

    def __init__(self, config, middleware, camera_worker):
        super().__init__(config)
        self.middleware = middleware
        self.worker = camera_worker

    def prepare(self):
        pass

    def resolve(self):
        raise NotImplemented