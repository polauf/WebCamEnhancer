import tkinter as tk
import tkinter.ttk as ttk

from ..config import Configuration
from ..core.base import ModuleController

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

    def __init__(self, master=None):
        self.opened = True
        self.config = Configuration.get_custom_config(self.__class__)
        self.master = master
        self._settings = {}
        self.build(master)

    def build(self, master=None):
        # build ui
        self.root = tk.Tk() if master is None else tk.Toplevel(master.root)
        self.root.configure(height=200, width=200)
        self.root.geometry(self.config["geometry"])
        self.root.title(tt("Webcam Setting"))
        self.root.protocol("WM_DELETE_WINDOW", self._exit)

        self.settings_frame = ttk.Frame(self.root)

        self._mainsetting = {}

        self.module_frame = ttk.Labelframe(self.settings_frame, text=tt("Main config"))
        self._mainsetting["input_cam"] = self._make_row(self.module_frame, 0, "input_cam", self.config["input_cam"])
        self._mainsetting["output_cam"] = self._make_row(self.module_frame, 1, "output_cam", self.config["output_cam"])
        self._mainsetting["width"] = self._make_row(self.module_frame, 2, "width", self.config["width"], tk.IntVar)
        self._mainsetting["height"] = self._make_row(self.module_frame, 3, "height", self.config["height"], tk.IntVar)
        self._mainsetting["fps"] = self._make_row(self.module_frame, 4, "fps", self.config["fps"], tk.DoubleVar)
        self._mainsetting["language"] = self._make_row(self.module_frame, 5, tt("language"), self.config["language"])
        self.module_frame.pack(side="top", fill="x", padx=10, pady=5)

        for group in ModuleController.MODULES.values():
            for mod in group:
                self._make_module(self.settings_frame, mod)

        self.settings_frame.pack(expand="true", fill="both", side="top")
        button_frame = ttk.Frame(self.root)

        self.implement_buton = ttk.Button(button_frame, text=tt("Implement"), command=self.on_implement)
        self.implement_buton.pack(side="right")

        self.revert_button = ttk.Button(button_frame, text=tt("Revert"), command=self.on_revert)
        self.revert_button.pack(side="left")
        button_frame.pack(fill="x", side="top")

    def _make_row(self, master, i, key, default_value, var_class=tk.StringVar):
        label = ttk.Label(master, text=key)
        label.grid(column=0, row=i)
        var = var_class(master)
        entry = tk.Entry(master, textvariable=var)
        entry.grid(column=1, padx=10, row=i)
        var.set(default_value or 0)
        return var

    def _make_module(self, master, module):
        self._settings[module] = {}
        config = Configuration.get_module_config(module)
        if config:
            frame = ttk.Labelframe(self.settings_frame, text=module.__name__, )
            defaults = module.CONFIG_TEMPLATE
            for i,(k, default) in enumerate(defaults.items()):
                self._settings[module][k] = self._make_row(frame, i, k, config.get(k, default), self._resolve_var(k, default))
            frame.pack(side="top", fill="x", padx=10, pady=5)

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
        except tk.TclError:
            pass
        self.root.destroy()

Configuration.CUSTOM_CLASSES.append(Setting)
