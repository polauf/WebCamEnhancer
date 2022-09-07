import tkinter as tk
import tkinter.ttk as ttk

from .utils import make_simple_setting_row
from ..config import Configuration
from ..core.base import ModuleController

class ScrollableFrame(ttk.Frame):
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        canvas = tk.Canvas(self)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

class Setting:

    CONFIG_TEMPLATE = {
        "geometry": "700x300",
        "input_cam": "0",
        "output_cam": '/dev/video2',
        "width": 1024,
        "height": 726,
        "fps": None,
        "language": "en"
    }

    def __init__(self, master):
        self.opened = True
        self.config = Configuration.get_custom_config(self.__class__)
        self.master = master
        self._settings = {}
        self.build(master)

    def build(self, master):
        # build ui
        self.root = tk.Toplevel(master.root)
        self.root.configure(height=200, width=200)
        self.root.geometry(self.config["geometry"])
        self.root.title(tt("Webcam Setting"))
        self.root.minsize(425, 400)
        self.root.protocol("WM_DELETE_WINDOW", self._exit)

        settings_frame = ScrollableFrame(self.root)
        scroll_frame = settings_frame.scrollable_frame
        self._mainsetting = {}

        self.module_frame = ttk.Labelframe(scroll_frame, text=tt("Main config"))
        self._mainsetting["input_cam"] = make_simple_setting_row(self.module_frame, 0, tt("Input Camera device"), self.config["input_cam"])
        self._mainsetting["output_cam"] = make_simple_setting_row(self.module_frame, 1, tt("Output Stream device"), self.config["output_cam"])
        self._mainsetting["width"] = make_simple_setting_row(self.module_frame, 2, tt("Prefered width"), self.config["width"], tk.IntVar)
        self._mainsetting["height"] = make_simple_setting_row(self.module_frame, 3, tt("Prefered height"), self.config["height"], tk.IntVar)
        self._mainsetting["fps"] = make_simple_setting_row(self.module_frame, 4, tt("Prefered FPS"), self.config["fps"], tk.DoubleVar)
        self._mainsetting["language"] = make_simple_setting_row(self.module_frame, 5, tt("Language"), self.config["language"])
        self.module_frame.columnconfigure(0, minsize=200)
        self.module_frame.pack(side="top", fill="x", padx=10, pady=5)

        for group in ModuleController.MODULES.values():
            for mod in sorted(group, key=lambda x: x.__name__):
                self._make_module(scroll_frame, mod)

        settings_frame.pack(expand="true", fill="both", side="top")
        button_frame = ttk.Frame(self.root)

        self.implement_buton = ttk.Button(button_frame, text=tt("Implement"), command=self.on_implement)
        self.implement_buton.pack(side="right")

        self.revert_button = ttk.Button(button_frame, text=tt("Revert"), command=self.on_revert)
        self.revert_button.pack(side="left")
        button_frame.pack(fill="x", side="top", padx=5, pady=5)

    def _make_module(self, master, module):
        self._settings[module] = {}
        config = Configuration.get_module_config(module)
        if config:
            frame = ttk.Labelframe(master, text=f"{module.__mro__[1].__name__} - {module.__name__}", )
            frame.columnconfigure(0, minsize=200)
            defaults = module.CONFIG_TEMPLATE
            for i,(k, default) in enumerate(defaults.items()):
                self._settings[module][k] = make_simple_setting_row(
                    frame, i, " ".join(k.split("_")).capitalize(), 
                    config.get(k, default), self._resolve_var(k, default)
                    )
            frame.pack(side="top", fill="x", padx=10, pady=5, ipady=3)

    @staticmethod
    def _resolve_var(key, default):
        if isinstance(default, float):
            return tk.DoubleVar
        elif isinstance(default, int):
            return tk.IntVar
        else:
            return tk.StringVar

    def on_implement(self):
        for k, var in self._mainsetting.items():
            self.config[k] = var.get()
        
        for mod, group in  self._settings.items():
            config = Configuration.get_module_config(mod)
            for k, var in group.items():
                config[k] = var.get()

        self.master.settings_changed()

    def on_revert(self):
        for k, var in self._mainsetting.items():
            defaults = self.CONFIG_TEMPLATE
            if isinstance(var, (tk.DoubleVar, tk.IntVar)):
                var.set(self.config.get(k, defaults[k]) or 0)
            else:
                var.set(self.config.get(k, defaults[k]))

        for mod, group in  self._settings.items():
            config = Configuration.get_module_config(mod)
            defaults = mod.CONFIG_TEMPLATE
            for k, var in group.items():
                if isinstance(var, (tk.DoubleVar, tk.IntVar)):
                    var.set(config.get(k, defaults[k]) or 0)
                else:
                    var.set(config.get(k, defaults[k]))

    def run(self):
        self.root.mainloop()

    def _exit(self, *_):
        self.opened = False
        try:
            self.config["geometry"] = self.root.geometry()
            self.root.destroy()
        except tk.TclError:
            pass

Configuration.CUSTOM_CLASSES.append(Setting)
