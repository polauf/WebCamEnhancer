import tkinter as tk
from tkinter.filedialog import asksaveasfilename
import tkinter.ttk as ttk
from PIL import ImageTk, Image
from pathlib import Path
import cv2, io

from ..core.utils import logger
from ..config import Configuration

class WebcamPreview:
    """
    Creates window with canvas to see and manipulate with webcam stream.
    """

    ZOOM_RATIONS = {0.5: "2:1", 1.: "1:1" , 2.: "1:2", 4.: "1:4"}

    CONFIG_TEMPLATE = {
        "offset": (),
        "zoom": 2.0
    }

    def __init__(self, camera_worker, master=None):
        self._camera_worker = camera_worker
        self.config = Configuration.get_custom_config(self.__class__)
        self.build(master)
        self.opened = True

    def build(self, master=None):
        # build ui
        self.root = tk.Tk() if master is None else tk.Toplevel(master.root)
        self.root.configure(borderwidth=5)
        self.root.resizable(False, False)
        self.root.title(tt("Webcam preview"))
        self.root.protocol("WM_DELETE_WINDOW", self._exit)
        #self.root.bind("<Configure>", self.conf)

        offset = self.config["offset"]
        if offset:
            self.root.geometry(f"+{offset[0]}+{offset[1]}")


        self.canvas = tk.Canvas(self.root,background="#000000", relief="flat", takefocus=False)
        self.canvas.pack(anchor="ne", expand="true", fill="both", side="top")

        buttons = ttk.Frame(self.root, height=30)
        self.start_button = ttk.Button(buttons, command=self.toggle_collection)
        self.start_button.configure(text=tt("Stop") if self._camera_worker.preview else tt("Start"))
        self.start_button.pack(side="right")

        self.save_button = ttk.Button(buttons, command=self.save_canvas)
        self.save_button.configure(text=tt("Save"))
        self.save_button.pack(side="right")

        self.zoom = tk.DoubleVar(self.root, value=self.config["zoom"])
        self.zoom.trace_add("write", self.zoom_change)
        self.zoom_button = ttk.Menubutton(buttons, text=f"{tt('Zoom')} {self.ZOOM_RATIONS[self.zoom.get()]}",)
        self.zoom_button.menu = tk.Menu(self.zoom_button, tearoff = 0)
        self.zoom_button["menu"] =  self.zoom_button.menu
        for ratio, label in self.ZOOM_RATIONS.items():
            self.zoom_button.menu.add_radiobutton(label=label, variable=self.zoom, value=ratio)
        self.zoom_button.pack(side="left")

        buttons.pack(
            anchor="s", expand="false", fill="x", padx=10, pady=5, side="bottom"
        )

    def zoom_change(self, *_):
        self.zoom_button.configure(text = f"{tt('Zoom')} {self.ZOOM_RATIONS[self.zoom.get()]}")

    def _exit(self, *_):
        try:
            self.config["offset"] = self.root.geometry().split('+')[1:]
        except tk.TclError:
            pass
        self.config["zoom"] = self.zoom.get()
        self.opened = False
        self.root.destroy()

    def toggle_collection(self):
        if self._camera_worker.preview:
            self._camera_worker.preview = False
            self.start_button.configure(text=tt("Start"))
        else:
            self._camera_worker.preview = True
            self.start_button.configure(text=tt("Stop"))
            self.update_canvas()

    def update_canvas(self):
        if self._camera_worker.preview:
            frame = self._camera_worker.get_frame(False)
            if frame is not None:
                ratio = self.zoom.get()
                frame = cv2.cvtColor(cv2.resize(frame, (int(frame.shape[1]/ratio), int(frame.shape[0]/ratio))), cv2.COLOR_BGR2RGB)
                self.canvas.configure(width=frame.shape[1], height=frame.shape[0])
                self.image = ImageTk.PhotoImage(image=Image.fromarray(frame))
                self.canvas.create_image(0, 0, image=self.image, anchor=tk.NW)
            self.root.after(1, self.update_canvas)

    def save_canvas(self):
        ps = self.canvas.postscript(colormode='color')
        img = Image.open(io.BytesIO(ps.encode('utf-8')))
        name = asksaveasfilename(
            defaultextension=".jpeg",
            initialdir= Path().home().absolute(),
            filetypes=((tt("Images"), "*.jpeg *.png"),),
            title=tt("Save Screenshot As")
            )
        if name:
            img.save(name, Path(name).suffix[1:])
            logger.info(f"Screenshot saved as '{name}'")

    def recording(self):
        # TODO: need to hookup to microphone through PyAudio? 
        writer= cv2.VideoWriter('basicvideo.mp4', cv2.VideoWriter_fourcc(*'DIVX'), 20, (width,height))


    def run(self):
        self.update_canvas()
        self.root.mainloop()

Configuration.CUSTOM_CLASSES.append(WebcamPreview)