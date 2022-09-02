"""Camera filter classes, for applying various per-frame effects.

Each class defines a specific frame manipulation and all classes are discovered upon launch.
Therefore, additional filters can be added here by simply creating a new class that:
- Inherits from `filters.Filter`
- Implements an `apply` method which takes a frame (as a `np.array`), applies filter logic and returns that a `np.array`.
- Does not share a name with any existing class or input command.
"""
import sys

import cv2
import numpy as np
from numba import jit

from ..config import Config, get_background
from .middleware import Filter, Cascade, Selfie, SelfieCascade

def resolve_away(changer, mask, state=[Config.PRESENT_FILTER, 0, True]):
    """
    Resolves if user is away from cam.
    Uses from config:
    - Config.AWAY_TRESHOLD
    - Config.AWAY_FRAMES
    - Config.PRESET_FRAMES
    - Config.PRESENT_FILTER
    - Config.AWAY_FILTER

    params:
    changer: CameraModifier
    mask: Segmentation result
    state: Internal. (State storage)
    """
    # TODO: Optimize conditions. To mutch gunk.
    if state[0] != changer._filter:
        state[0] = changer._filter
    if state[1] > Config.AWAY_FRAMES and state[0] == Config.PRESENT_FILTER:
        state[0] = Config.AWAY_FILTER
        state[1] = 0
        changer._filter = state[0]
    elif state[1] > Config.PRESET_FRAMES and state[0] == Config.AWAY_FILTER:
        state[0] = Config.PRESENT_FILTER
        state[1] = 0
        changer._filter = state[0]
    elif state[0] == Config.PRESENT_FILTER:
        val = np.average(mask) < Config.AWAY_TRESHOLD
        if val and state[2]:
            state[1] += 1
            state[2] = val
        else:
            state[1] = 0
    elif state[0] == Config.AWAY_FILTER:
        val = np.average(mask) > Config.AWAY_TRESHOLD
        if val and state[2]:
            state[1] += 1
            state[2] = val
        else:
            state[1] = 0
    # Prints warning
    frames = Config.AWAY_FRAMES if state[0] == Config.PRESENT_FILTER else Config.PRESET_FRAMES
    if state[1] and state[1] > (frames - changer.fps*Config.WARNING_SECS) and not (state[1]%changer.fps):
        changer.logger.info(f"Changing {state[0]} in {int((frames - state[1])/changer.fps)}.")


def rotate_image(image: np.array, angle: float) -> np.array:
  return cv2.warpAffine(
      image,
      cv2.getRotationMatrix2D(
          tuple(np.array(image.shape[1::-1]) / 2),
          angle,
          1.0
          ),
        image.shape[1::-1],
        flags=cv2.INTER_LINEAR
        )

def draw_on_image(bottom: np.array, top: np.array, x=0, y=0):
    (h, w) = top.shape[:2]
    y1, y2 = y, y + h
    x1, x2 = x, x + w
    
    x_lim = 0
    y_lim = 0
    if x2 >= bottom.shape[1]:
        x_lim = x2 - bottom.shape[1] + 1
        w -= x_lim
        x2 -= x_lim
    if y2 >= bottom.shape[0]:
        y_lim = y2 - bottom.shape[0] + 1
        h -= y_lim
        y2 -= y_lim

    alpha_top = top[:h, :w, 3] / 255.0
    alpha_bottom = 1.0 - alpha_top
    for c in range(0, 3):
        bottom[y1:y2, x1:x2, c] = (alpha_top * top[:h, :w, c] +
                                   alpha_bottom * bottom[y1:y2, x1:x2, c])
    if bottom.shape[2] == 4:
        bottom[y1:y2, x1:x2, 3] = np.maximum(top[:h, :w, 3], bottom[y1:y2, x1:x2, 3])

class NoFilter(Filter):
    "Nothing."

    def apply(self, changer, frame):
        return frame
        

class Shake(Filter):
    "Shake two channels horizontally every frame."
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._frame_count = 0

    def apply(self, changer, frame):
        # Shake two channels horizontally each frame.
        channels = [[0, 1], [0, 2], [1, 2]]

        dx = 15 - self._frame_count % 5
        c1, c2 = channels[self._frame_count % 3]
        frame[:, :-dx, c1] = frame[:,  dx:, c1]
        frame[:,  dx:, c2] = frame[:, :-dx, c2]

        self._frame_count += 1

        return frame


class Pixel(Selfie):
    "Blur foreground person."
    # Based on: # Docs: https://google.github.io/mediapipe/solutions/selfie_segmentation.html

    def apply(self, changer, frame):
        # Identify foreground segment
        foreground = np.stack((super().apply(changer, frame),) * 3, axis=-1) > 0.1

        # Pixelate for background
        px_w, px_h = Config.PIXELATE_SIZE
        height, width, n_channels = frame.shape
        temp = cv2.resize(frame, (px_w, px_h), interpolation=cv2.INTER_LINEAR)
        pixelated = cv2.resize(temp, (width, height), interpolation=cv2.INTER_NEAREST)

        # Fill segments as required
        return np.where(foreground, pixelated, frame)


class Gray(Filter):
    "Grayscale image."

    def apply(self, changer, frame):
        return np.repeat(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), 3).reshape(frame.shape)


class Sepia(Filter):
    "Classic sepia filter."
    # Based on: https://gist.github.com/FilipeChagasDev/bb63f46278ecb4ffe5429a84926ff812

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def apply(self, changer, frame):
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

class LaughingMan(Cascade):
    "Only Laughing man overlay."

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rotation = 0.0
        self.face_img = cv2.imread(Config.FACE_IMAGE_PATH, -1)
        self.text_img = cv2.imread(Config.TEXT_IMAGE_PATH, -1)
        self.previous_coords = []
        self.previous_lifetime = 0
    
    def apply(self, changer, frame):
        faces = super().apply(changer, frame)
        
        if Config.LIFETIME != -1 and self.previous_lifetime > Config.LIFETIME:
            self.previous_coords = ()

        if len(faces):
            self.previous_lifetime = 0

        if not len(faces) and len(self.previous_coords):
            faces = self.previous_coords
            self.previous_lifetime +=1

        for (x, y, w, h) in faces:
            # Scale image to be larger then detected face
            ws = int(w * Config.SCALE)
            hs = int(h * Config.SCALE)
            ratio = ws/self.face_img.shape[0]
            size = (int(self.face_img.shape[1]*ratio), int(self.face_img.shape[0]*ratio))
            
            # TODO: Wrong hadling of negaitve corners in draw_on_image()
            xs = int(x - hs/4)
            if xs < 0: xs = 0
            ys = int(y - ws/4)
            if ys < 0: ys = 0

            combo = np.zeros(self.face_img.shape)
            draw_on_image(combo, rotate_image(self.text_img, self.rotation), 0, 0)
            draw_on_image(combo, self.face_img)
            draw_on_image(frame, cv2.resize(combo, size), xs, ys)

            # Debug rectangle
            # cv2.rectangle(frame, (x,y), (x+w, y+h), (0,255,0),2)
            
            self.previous_coords = faces

        self.rotation += Config.ROTATION_RATE

        return frame


class Background(Selfie):
    "Repleaces background with a picture."

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bg = get_background()
        self._frame_count = 0
        self.mask = None

    
    def apply(self, changer, frame):
        # simple 2-sample running average filter
        mask = super().apply(changer, frame)
        if self.mask is None:
            self.mask = mask
        else:
            self.mask = (self.mask/2 + mask)/1.5
        
        resolve_away(changer, mask)
        
        # resize background if needed
        if self.bg.shape != frame.shape:
            self.bg = cv2.resize(self.bg, (frame.shape[1], frame.shape[0]))

        # blend images with segmentation mask (fg*mask + bg*(1-mask))
        for i in range(3):
            frame[:,:,i] = frame[:,:,i]*self.mask + self.bg[:,:,i]*(1.-self.mask)
        
        
        self._frame_count += 1
        return frame


class Anonymous(Selfie):
    """Pixalated person with background picture."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bg = get_background()
        self.mask = None
        self._frame_count = 0
    
    def apply(self, changer, frame):
        mask = super().apply(changer, frame)
        # simple 2-sample running average filter
        if self.mask is None:
            self.mask = mask
        else:
            self.mask = (self.mask + mask)/2.

        # resize background if needed
        if self.bg.shape != frame.shape:
            self.bg = cv2.resize(self.bg, (frame.shape[1], frame.shape[0]))

        # blend images with segmentation mask (fg*mask + bg*(1-mask))
        for i in range(3):
            frame[:,:,i] = frame[:,:,i]*self.mask + self.bg[:,:,i]*(1.-self.mask)
        
        # Pixelate for background
        foreground = np.stack((self.mask,) * 3, axis=-1) > 0.1
        px_w, px_h = Config.PIXELATE_SIZE
        height, width, n_channels = frame.shape
        temp = cv2.resize(frame, (px_w, px_h), interpolation=cv2.INTER_LINEAR)
        pixelated = cv2.resize(temp, (width, height), interpolation=cv2.INTER_NEAREST)

        # Fill segments as required
        frame = np.where(foreground, pixelated, frame)

        self._frame_count += 1
        return frame   

class LMan(SelfieCascade):
    "Pixalated rest of the person with background picture and Laughing man overlay."

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rotation = 0.0
        self.bg = get_background()
        self.face_img = cv2.imread(Config.FACE_IMAGE_PATH, -1)
        self.text_img = cv2.imread(Config.TEXT_IMAGE_PATH, -1)
        self.previous_coords = []
        self.previous_lifetime = 0
        self.mask = None
        self._frame_count = 0
    
    def apply(self, changer, frame):
        mask, faces = super().apply(changer, frame)
        # simple 2-sample running average filter
        if self.mask is None:
            self.mask = mask
        else:
            self.mask = (self.mask + mask)/2.

        # resize background if needed
        if self.bg.shape != frame.shape:
            self.bg = cv2.resize(self.bg, (frame.shape[1], frame.shape[0]))

        # blend images with segmentation mask (fg*mask + bg*(1-mask))
        for i in range(3):
            frame[:,:,i] = frame[:,:,i]*self.mask + self.bg[:,:,i]*(1.-self.mask)
        
        # Pixelate for background
        foreground = np.stack((self.mask,) * 3, axis=-1) > 0.1
        px_w, px_h = Config.PIXELATE_SIZE
        height, width, n_channels = frame.shape
        temp = cv2.resize(frame, (px_w, px_h), interpolation=cv2.INTER_LINEAR)
        pixelated = cv2.resize(temp, (width, height), interpolation=cv2.INTER_NEAREST)

        # Fill segments as required
        frame = np.where(foreground, pixelated, frame)

        self._frame_count += 1

        if Config.LIFETIME != -1 and self.previous_lifetime > Config.LIFETIME:
            self.previous_coords = ()

        if len(faces):
            self.previous_lifetime = 0

        if not len(faces) and len(self.previous_coords):
            faces = self.previous_coords
            self.previous_lifetime +=1

        for (x, y, w, h) in faces:
            # Scale image to be larger then detected face
            ws = int(w * Config.SCALE)
            hs = int(h * Config.SCALE)
            ratio = ws/self.face_img.shape[0]
            size = (int(self.face_img.shape[1]*ratio), int(self.face_img.shape[0]*ratio))

            xs = int(x - hs/4)
            if xs < 0: xs = 0
            ys = int((y - ws/4)*(0.75+(changer.zoom/2.75)))
            if ys < 0: ys = 0

            combo = np.zeros(self.face_img.shape)
            draw_on_image(combo, rotate_image(self.text_img, self.rotation), 0, 0)
            draw_on_image(combo, self.face_img)
            draw_on_image(frame, cv2.resize(combo, size), xs, ys)

            # Debug rectangle
            # cv2.rectangle(frame, (x,y), (x+w, y+h), (0,255,0),2)
            
            self.previous_coords = faces

        self.rotation += Config.ROTATION_RATE

        return frame


class Away(Selfie):
    "Away sign with background picture."

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.frame = get_background().copy()
        self._made = False
        self.away = cv2.imread(Config.AWAY_IMG, cv2.IMREAD_UNCHANGED)
    
    def apply(self, changer, frame: np.array) -> np.array:
        if not self._made:
            self.frame = cv2.resize(self.frame, (frame.shape[1], frame.shape[0]))
            yoff = round((self.frame.shape[0]-self.away.shape[0])/2)
            xoff = round((self.frame.shape[1]-self.away.shape[1])/2)
            mask = self.away[:,:,3] / 255.0
            try:
                for i in range(3):
                    self.frame[yoff:yoff+self.away.shape[0], xoff:xoff+self.away.shape[1],i] =\
                        mask*self.away[:,:,i] + (
                            1 - mask)*self.frame[yoff:yoff+self.away.shape[0], xoff:xoff+self.away.shape[1],i]
            except ValueError:
                print("Can't add away to background. probably away is bigger. fix that.")
                sys.exit(1)
            self._made = True
        resolve_away(changer, super().apply(changer, frame))
        return self.frame


class ASCII(Selfie):
    "Change person to ASCIIart."
    # Based on: https://www.learnpythonwithrune.org/ascii-art-of-live-webcam-stream-with-opencv/ 

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Black Background
        self.bg = np.array([[[0,0,0]]],np.uint8)
        self.color = (0,1,0) # bgr
        self.mask = None
        self.coeficient = 1
        self.box = (6*self.coeficient, 8*self.coeficient)
        self.images = self.generate_ascii_letters(*self.box)

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
    
    def apply(self, changer, frame: np.array) -> np.array:
        mask = super().apply(changer, frame)
        # resize background if needed
        if self.bg.shape != frame.shape:
            self.bg = cv2.resize(self.bg, (frame.shape[1], frame.shape[0]))

        # blend images with segmentation mask (fg*mask + bg*(1-mask))
        for i in range(3):
            frame[:,:,i] = frame[:,:,i]*mask + self.bg[:,:,i]*(1.-mask)

        ascii = self.to_ascii_art(
            cv2.Canny(
                cv2.GaussianBlur(frame, (5, 5), 4),
                38,
                14),
            self.images,
            *self.box
        )

        return np.stack([c*ascii for c in self.color], axis=-1)