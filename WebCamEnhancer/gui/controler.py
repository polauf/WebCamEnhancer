import tkinter as tk
import tkinter.ttk as ttk

from .preview import WebcamPreview
from ..core.camera import CamerasWorker, CameraError
from ..core.base import ModuleController
from ..config import Configuration
from .settings import Setting


class Controler:
    """
    Central control window.
    """

    CONFIG_TEMPLATE = {
        "geometry": "600x300",
        "colection_at_start": False,
        "stream_at_start": False,
        "show_preview_at_start": False,
        "show_setting_at_start": False,
        "active_filters": []
    }

    def __init__(self, master=None):
        self._worker = None
        self.config = Configuration.get_custom_config(self.__class__)
        self.previewer = None
        self.settings = None
        self.active_filters = self.config["active_filters"]
        self.build(master)

    def build(self, master=None):
        self.root = tk.Tk() if master is None else tk.Toplevel(master.root)
        self.root.configure(height=400, width=600)
        self.root.geometry(self.config["geometry"])
        self.root.maxsize(800, 600)
        self.root.minsize(400, 300)
        self.root.resizable(True, True)
        self.root.title(tt("Webcam Enhancer"))
        self.root.protocol("WM_DELETE_WINDOW", self._exit)
        m_frame = ttk.Frame(self.root)

        buttom_frame = ttk.Frame(m_frame)

        self.start_button = ttk.Button(buttom_frame, text=tt("Start"), width=15, command=self.toggle_worker)
        self.start_button.pack(anchor="center", padx=20, pady=2, side="top")

        self.stream_button = ttk.Button(buttom_frame, state="disabled", text=tt("Stream"), width=15, command=self.toggle_stream)
        self.stream_button.pack(pady=2, side="top")

        self.preview_button = ttk.Button(buttom_frame, text=tt("Preview"), width=15, command=self.toggle_preview)
        self.preview_button.pack(pady=2, side="top")

        self.config_button = ttk.Button(buttom_frame, text=tt("Configuration"), width=15, command=self.toggle_setting)
        self.config_button.pack(pady=2, side="top")

        status_frame = ttk.Frame(buttom_frame)

        status_frame.configure(borderwidth=1, height=1, padding=2, relief="sunken", width=1)

        i_label = ttk.Label(status_frame, text=f"{tt('Input')}:")
        i_label.grid(column=0, row=0, sticky="w")

        self.label_input = ttk.Label(status_frame, state="disabled", text=tt("None"))
        self.label_input.grid(column=1, row=0)

        o_label = ttk.Label(status_frame, text=f"{tt('Output')}:")
        o_label.grid(column=0, row=1, sticky="w")

        self.label_output = ttk.Label(status_frame, state="disabled", text=tt("None"))
        self.label_output.grid(column=1, row=1)

        self.label_resolution = ttk.Label(status_frame, state="disabled", text="? x ? px")
        self.label_resolution.grid(column=0, columnspan=2, row=2)

        self.label_fps = ttk.Label(status_frame, state="disabled", text=f"{tt('FPS')}: ?")
        self.label_fps.grid(column=0, columnspan=2, row=3)

        status_frame.pack(anchor="center", expand="false", fill="x", padx=10, side="bottom")
        status_frame.grid_anchor("center")
        status_frame.columnconfigure(0, minsize=60)

        buttom_frame.pack(anchor="n", expand="false", fill="y", padx=2, pady=10, side="left")

        filters_frame = ttk.Labelframe(m_frame, labelanchor="n", relief="ridge", text=tt("Filters"))

        self.filters_view = ttk.Treeview(filters_frame)
        self.filters_view.configure(selectmode="browse", show="headings")
        filters_view_cols = ["names_column", "order_column"]
        self.filters_view.configure(columns=filters_view_cols, displaycolumns=filters_view_cols)
        self.filters_view.column(
            "names_column", anchor="w", stretch="true", width=200, minwidth=20
        )
        self.filters_view.column(
            "order_column", anchor="w", stretch="false", width=60, minwidth=60
        )
        self.filters_view.heading("names_column", anchor="w", text=tt("name"))
        self.filters_view.heading("order_column", anchor="center", text=tt("order"))
        self.filters_view.pack(expand="true", fill="both", side="top")

        self.filters_view.bind('<Double-1>', self.double_filter)
        self.filters_view.bind('<Button-2>', self.middle_filter) 
        self.filters_view.bind('<Button-3>', self.right_filter) 

        self.load_filters()
        self._update_filters()

        # self.apply_buttom = ttk.Button(filters_frame, text="Apply")
        # self.apply_buttom.pack(side="right")

        filters_frame.pack(expand="true", fill="both", side="bottom")

        m_frame.pack(anchor="n", expand="true", fill="both", side="top")

        bottom_view = ttk.Frame(self.root, borderwidth=1, height=18, padding=3, relief="sunken")

        self.left_status = ttk.Label(bottom_view, text=f"{tt('Status')}: {tt('loading')}")
        self.left_status.pack(side="left")
        
        self.right_status = ttk.Label(bottom_view, text=tt("Stoped"))
        self.right_status.pack(side="right")
        
        bottom_view.pack(anchor="s", fill="x", side="bottom")

    def run(self):
        self.resolve_state()
        self.left_status["text"] = tt("Ready")
        if self.config["colection_at_start"]:
            self.toggle_worker()
        if self.config["show_preview_at_start"]:
            self.toggle_preview()
        if self.config["show_setting_at_start"]:
            self.toggle_setting()

        self.root.mainloop()

    def _exit(self):
        if self._worker is not None:
            self._worker.stop()
        self.config["geometry"] = self.root.geometry()
        self.config["colection_at_start"] = self._worker is not None
        self.config["stream_at_start"] = self._worker is not None and self._worker.streaming
        self.config["show_preview_at_start"] = self.previewer is not None and self.previewer.opened
        self.config["show_setting_at_start"] = self.settings is not None and self.settings.opened
        self.root.destroy()  


    def _update_filters(self):
        for iid in self.filters_view.get_children():
            item = self.filters_view.item(iid)["values"]
            name = item[0]
            item[1] = self.active_filters.index(name) + 1 if name in self.active_filters else '-'
            self.filters_view.item(iid, values = item)
        if self._worker is not None:
            self._worker.filters = tuple(self.active_filters)

    def _move_filter(self, i):
        try:
            name, val = self.filters_view.item(self.filters_view.focus())["values"]
        except ValueError:
            return
        index = self.active_filters.index(name) if name in self.active_filters else None
        ii = 1 if i == -1 else 0
        if index is not None and index < (len(self.active_filters) - ii):
            self.active_filters.insert(index + i, self.active_filters.pop(index))
            self._update_filters()
        elif index is None:
            self.active_filters.insert(0, name)
            self._update_filters()

    def double_filter(self, _):
        self._move_filter(1)
    
    def right_filter(self, _):
        self._move_filter(-1)

    def middle_filter(self, _):
        try:
            name, val = self.filters_view.item(self.filters_view.focus())["values"]
        except ValueError:
            return
        if name in self.active_filters:
            self.active_filters.remove(name)
            self._update_filters()

    def load_filters(self):
        i = 0
        for mod in sorted(ModuleController.MODULES["Filter"], key=lambda m: m.__name__):
            iid = f"{mod.__name__}_{i}"
            self.filters_view.insert('',
                iid=iid,
                index=i,
                text=f"filter_{i}",
                values=[mod.__name__, tt('None')]
                )
            i += 1

    def resolve_state(self):
        if self._worker is not None:
            self.stream_button["state"] = "normal"

            if self._worker.input_cam_properties:
                self.label_input["state"] = "normal"
                self.label_input["text"] = self._worker.in_cam_name
            if self._worker.output_cam_properties:
                self.label_output["state"] = "normal"
                self.label_output["text"] = self._worker.out_cam_name
                self.label_resolution["state"] = "normal"
                res = self._worker.output_cam_properties
                self.label_resolution["text"] = f"{res['width']}x{res['height']}px"
                self.label_fps["state"] = "normal"
                self.label_fps["text"] = f"{res['fps']} FPS"


        else:
            self.stream_button["state"] = "disabled"

            self.label_input["state"] = "disabled"
            self.label_input["text"] = tt("None")
            self.label_output["state"] = "disabled"
            self.label_output["text"] = tt("None")
            self.label_resolution["state"] = "disabled"
            self.label_resolution["text"] = "? x ? px"
            self.label_fps["state"] = "disabled"
            self.label_fps["text"] = "? FPS"

    def toggle_worker(self):
        if self._worker is not None:
            self._worker.stop()
            self._worker = None
            self.resolve_state()
            self.start_button["text"] = tt("Start")
            self.right_status["text"] = tt("Stoped")
        else:
            try:
                setting = Configuration.get_custom_config(Setting)
                self._worker = CamerasWorker(
                    in_cam = int(setting["input_cam"]),
                    out_cam = setting["output_cam"],
                    width = setting["width"] or None,
                    height = setting["height"] or None,
                    fps = setting["fps"] or None,
                    preview = self.config["show_preview_at_start"],
                    )
                self.toggle_stream()
                self._update_filters()
                self._worker.start()
                self.resolve_state()
                if self.previewer:
                    self._worker.preview = True
                    self.previewer._camera_worker = self._worker
                self.start_button["text"] = tt("Stop")
                self.right_status["text"] = tt("Running")
            except CameraError as e:
                self.right_status["text"] = f"{tt('Error')}: {e.args[0]}"
                self._worker = None

    def toggle_stream(self,stop=False):
        if self._worker is not None:
            if self._worker.streaming or stop:
                self._worker.streaming = False
                self.stream_button["text"] = tt("Stream")
            else:
                self._worker.streaming = True
                self.stream_button["text"] = tt("Stop Stream")

    def toggle_preview(self, stop=None):
        if not stop and (self.previewer is None or not self.previewer.opened):
            if self._worker:
                self._worker.preview = True
            self.previewer = WebcamPreview(self._worker, self)
            self.preview_button["text"] = tt("Close Preview")
            self.root.after(1, self.previewer.run)
        else:
            if self._worker:
                self._worker.preview = False
            if self.previewer:
                try:
                    self.previewer._exit()      
                except tk.TclError:
                    pass     
            self.preview_button["text"] = tt("Preview")

    def settings_changed(self):
        if self._worker:
            self.toggle_worker()
            self.toggle_worker()


    def toggle_setting(self):
            if self.settings is None or not self.settings.opened:
                self.settings = Setting(self)
                self.root.after(1, self.settings.run)
            elif self.settings:
                    try:
                        self.settings._exit()      
                    except tk.TclError:
                        pass     

Configuration.CUSTOM_CLASSES.append(Controler)