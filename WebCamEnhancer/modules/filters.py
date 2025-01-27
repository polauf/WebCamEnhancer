import cv2, time
import numpy as np
from numba import jit
from ..core.base import Filter
from ..core.utils import draw_on_image, rotate_image

class Shake(Filter):
    "Shake two channels horizontally every frame."

    def prepare(self, resolution):
        self._frame_count = 0

    def apply(self,frame):
        # Shake two channels horizontally each frame.
        channels = [[0, 1], [0, 2], [1, 2]]

        dx = 15 - self._frame_count % 5
        c1, c2 = channels[self._frame_count % 3]
        frame[:, :-dx, c1] = frame[:,  dx:, c1]
        frame[:,  dx:, c2] = frame[:, :-dx, c2]

        self._frame_count += 1

        return frame

class Info(Filter):

    CONFIG_TEMPLATE = {
        "color": "#FFF",
        "scale": 1.5,
        "thickness": 2
    }

    def prepare(self, resolution):
        self.last_time = time.perf_counter()
        self.color = self.hex2color(self.config["color"])
        self.scale = self.config["scale"]
        self.thickness = self.config["thickness"]

    def apply(self, frame):
        text = [f"FPS: {int(1 / (time.perf_counter() - self.last_time))}"]
        text.append(f"Filters: {', '.join(self.worker._active_filters)}")
        props = self.worker.input_cam_properties
        text.append(f"Resolution: {props['width']}x{props['height']}")
        self.last_time = time.perf_counter()

        y0, dy = 50, int(30*self.scale)
        for i, line in enumerate(text):
            y = y0 + i*dy
            cv2.putText(frame, line, (5, y), cv2.FONT_HERSHEY_PLAIN, self.scale, self.color.tolist(), self.thickness)
        return frame

class ImageQuality(Filter):
    "Apply some color/saturation corrections."

    CONFIG_TEMPLATE = {
        "gamma": 1.68,
        "hue": 1.,
        "saturation":1.1,
        "value": 1.15,

        "red":1.25,
        "green": .95,
        "blue": .85
    }

    def make_setting(self, ):
        pass

    def prepare(self, resolution):
        self.lookUpTable = np.empty((1,256), np.uint8)
        for i in range(256):
            self.lookUpTable[0,i] = np.clip(pow(i / 255.,  self.config["gamma"]) * 255., 0, 255)

        self.hsv = np.array([self.config["hue"], self.config["saturation"], self.config["value"]])
        self.bgr = np.array([self.config["blue"], self.config["green"], self.config["red"]])

    def apply(self, frame):
            # gamma
            frame = cv2.LUT(frame, self.lookUpTable)
            if (self.hsv/1).any():
                (h, s, v) = cv2.split(cv2.cvtColor(frame, cv2.COLOR_BGR2HSV).astype("float32"))
                h = np.clip(h*self.hsv[0], 0, 255)
                s = np.clip(s*self.hsv[1], 0, 255)
                v = np.clip(v*self.hsv[2], 0, 255)

                frame = cv2.cvtColor(cv2.merge([h,s,v]).astype("uint8"), cv2.COLOR_HSV2BGR)
            if (self.bgr/1).any():
                (b, g, r) = cv2.split(frame.astype("float32"))
                b = np.clip(b*self.bgr[0], 0, 255)
                g = np.clip(g*self.bgr[1], 0, 255)
                r = np.clip(r*self.bgr[2], 0, 255)

                frame = cv2.merge([b,g,r]).astype("uint8")
            return frame

class Pixel(Filter):
    """Blur foreground person.
    # Based on: # Docs: https://google.github.io/mediapipe/solutions/selfie_segmentation.html
    """

    CONFIG_TEMPLATE = {
        "size_x": 48,
        "size_y": 48
    }

    def prepare(self,*_):
        self.size = (self.config["size_x"], self.config["size_y"])

    def apply(self, frame):
        foreground = np.stack((self.middleware["Selfie"].get(),) * 3, axis=-1) > 0.1

        height, width, n_channels = frame.shape
        temp = cv2.resize(frame, tuple(self.size), interpolation=cv2.INTER_LINEAR)

        return np.where(foreground, cv2.resize(temp, (width, height), interpolation=cv2.INTER_NEAREST), frame)


class Gray(Filter):
    "Grayscale image."

    def apply(self, frame):
        return np.repeat(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), 3).reshape(frame.shape)


class Sepia(Filter):
    """Classic sepia filter.
    # Based on: https://gist.github.com/FilipeChagasDev/bb63f46278ecb4ffe5429a84926ff812
    """

    def apply(self, frame):
        grayscale_norm = np.array(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), np.float32)/255

        # Solid color
        sepia = np.ones(frame.shape)
        sepia[:, :, 0] *= 153  # Blue channel
        sepia[:, :, 1] *= 204  # Green channel
        sepia[:, :, 2] *= 255  # Red channel

        # Hadamard
        sepia[:, :, 0] *= grayscale_norm  # Blue channel
        sepia[:, :, 1] *= grayscale_norm  # Green channel
        sepia[:, :, 2] *= grayscale_norm  # Red channel

        return np.array(sepia, np.uint8)

class LaughingMan(Filter):
    "Laughing man overlay."

    CONFIG_TEMPLATE = {
        "face_image_path": "img/lman_face.png",
        "plate_image_path": "img/lman_plate.png",
        "lifetime": -1,
        "scale": 1.6,
        "rotation_rate": -2.
    }

    def prepare(self, resolution):
        self.rotation = 0.0
        self.previous_coords = []
        self.previous_lifetime = 0

        self.face_img = cv2.imread(self.get_existing_file("face_image_path"), cv2.IMREAD_UNCHANGED)
        self.text_img = cv2.imread(self.get_existing_file("plate_image_path"), cv2.IMREAD_UNCHANGED)

        self.lifetime = self.config["lifetime"]
        self.scale = self.config["scale"]
        self.rotation_rate = self.config["rotation_rate"]

    
    def apply(self, frame):
        faces = self.middleware["Cascade"].get()
        if self.lifetime != -1 and self.previous_lifetime > self.lifetime:
            self.previous_coords = ()

        if len(faces):
            self.previous_lifetime = 0

        if not len(faces) and len(self.previous_coords):
            faces = self.previous_coords
            self.previous_lifetime +=1

        for (x, y, w, h) in faces:
            # Scale image to be larger then detected face
            ws, hs = int(w * self.scale), int(h * self.scale)
            ratio = ws/self.face_img.shape[0]
            size = (int(self.face_img.shape[1]*ratio), int(self.face_img.shape[0]*ratio))
            xc, yc = int(x + w/2), int(y + h/2.42)

            combo = np.zeros(self.face_img.shape)
            draw_on_image(combo, rotate_image(self.text_img, self.rotation), xy=(0, 0))
            draw_on_image(combo, self.face_img, xy=(0,0))
            draw_on_image(frame, cv2.resize(combo, size), center=(xc, yc))

            # Debug rectangle
            # cv2.rectangle(frame, (x,y), (x+w, y+h), (0,255,0),2)
            
            self.previous_coords = faces

        self.rotation += self.rotation_rate

        return frame


class Background(Filter):
    "Repleaces background with a picture."

    CONFIG_TEMPLATE = {
        "background_image_path": "img/background.png"
    }

    def prepare(self, resolution):
        self.bg = cv2.resize(cv2.imread(self.get_existing_file("background_image_path"), cv2.IMREAD_UNCHANGED), resolution)
        self.mask = None

    
    def apply(self, frame):
        # simple 2-sample running average filter
        mask = self.middleware["Selfie"].get()
        if self.mask is None:
            self.mask = mask
        else:
            self.mask = (self.mask/2 + mask)/1.5
                          
        # blend images with segmentation mask (fg*mask + bg*(1-mask))
        for i in range(3):
            frame[:,:,i] = frame[:,:,i]*self.mask + self.bg[:,:,i]*(1.-self.mask)

        return frame


class Away(Filter):
    "Away sign with background picture."

    CONFIG_TEMPLATE = {
        "away_image_path": "img/away.png",
        "background_path": "img/background.png"
    }

    def prepare(self, resolution):
        self.away = cv2.imread(self.get_existing_file("away_image_path"), cv2.IMREAD_UNCHANGED)
        self.bg = cv2.imread(self.get_existing_file("background_path"), cv2.IMREAD_UNCHANGED)
        self.done = False
    
    def apply(self, frame):
        if not self.done:
            yoff = round((frame.shape[0]-self.away.shape[0])/2)
            xoff = round((frame.shape[1]-self.away.shape[1])/2)
            mask = self.away[:,:,3] / 255.0
            try:
                self.bg = cv2.resize(self.bg, (frame.shape[1], frame.shape[0]))
                for i in range(3):
                    self.bg[yoff:yoff+self.away.shape[0], xoff:xoff+self.away.shape[1],i] = \
                        mask*self.away[:,:,i] + (
                            1 - mask)*self.bg[yoff:yoff+self.away.shape[0], xoff:xoff+self.away.shape[1],i]
            except ValueError:
                raise ValueError("AwayFilter: Can't add away to background. probably away is bigger. fix that.")
        return self.bg


class ASCII(Filter):
    """Change person to ASCIIart.
    # Based on: https://www.learnpythonwithrune.org/ascii-art-of-live-webcam-stream-with-opencv/
    """

    CONFIG_TEMPLATE = {
        "character_color": "#FFFF00",
        "canny_threshold_1": 35,
        "canny_threshold_2": 14,
        "canny_aperture_size": 3,
        "canny_l2_enabled": False,
        "gaussian_kernel": 5

    }

    def prepare(self, resolution):
        # distinguish background color
        self.bg = cv2.resize(np.array([[[0,255,0]]],np.uint8), resolution)
        self.color = self.hex2color(self.config["character_color"])
        #RGB to BGR
        self.color = np.array([*reversed(self.color)])
        self.coeficient = 1
        self.box = (6*self.coeficient, 8*self.coeficient)
        self.images = self.generate_ascii_letters(*self.box)
        self.canny_kwargs = {
            "threshold1": self.config["canny_threshold_1"],
            "threshold2": self.config["canny_threshold_2"],
            "apertureSize": int(self.config["canny_aperture_size"]),
            "L2gradient": bool(self.config["canny_l2_enabled"])
            }
        self.gaussian_kernel = (self.config["gaussian_kernel"], self.config["gaussian_kernel"])

    @staticmethod
    @jit(nopython=True)
    def to_ascii_art(frame, images, box_height=12, box_width=16):
        height, width = frame.shape
        for i in range(0, height, box_height):
            for j in range(0, width, box_width):
                roi = frame[i:i + box_height, j:j + box_width]
                best_match = np.inf
                best_match_index = 0
                for k in range(1, images.shape[0]):
                    total_sum = np.sum(np.absolute(np.subtract(roi, images[k])))
                    if total_sum < best_match:
                        best_match = total_sum
                        best_match_index = k
                roi[:,:] = images[best_match_index]
        return frame

    @staticmethod
    def generate_ascii_letters(height, width,):
        images = []
        # letters = "# $%&\\'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[]^_`abcdefghijklmnopqrstuvwxyz{|}~"
        letters = " \\()-./:[]_`|~=ˇ´¯<>€ŧ¶ø#°15973"
        for letter in letters:
            img = np.zeros((height, width), np.uint8)
            img = cv2.putText(img, letter, (0, 5), cv2.FONT_HERSHEY_SIMPLEX, int(height/6), 255)
            images.append(img)
        return np.stack(images)
    
    def apply(self, frame):
        mask = self.middleware["Selfie"].get()
        # blend images with segmentation mask (fg*mask + bg*(1-mask))
        for i in range(3):
            frame[:,:,i] = frame[:,:,i]*mask + self.bg[:,:,i]*(1.-mask)

        ascii = self.to_ascii_art(
            cv2.Canny(
                cv2.GaussianBlur(frame, self.gaussian_kernel, 4),
                **self.canny_kwargs),
            self.images,
            *self.box
        )
        # set foreground color
        colorized = np.asarray(cv2.cvtColor(ascii,cv2.COLOR_GRAY2BGR)*(np.asarray(self.color, np.float32)/255.),np.uint8)
        return colorized