# 🎥 CustomCam

Extendable webcam customisation in Python.

CustomCam uses [pyvirtualcamera](https://github.com/letmaik/pyvirtualcam) to interact with virtual output devices. As this package was primarily developed for Linux, the Quick Start commands address that use case. To set up virtual output devices for other platforms, check the [pyvirtualcam docs](https://github.com/letmaik/pyvirtualcam/blob/master/README.md).

## Quick Start
### Install
```text
pip install CustomCam                    # Install CustomCam
sudo apt install v4l2loopback-dkms       # Install virtual camera creator (Linux)
```

### Launch
```text
sudo modprobe v4l2loopback devices=1     # Create virtual camera (Linux)
CustomCam                                # Launch CustomCam
````

## Usage
### On-Launch
```text
usage: CustomCam [-h] [--input_camera INPUT_CAMERA]
                 [--output_camera OUTPUT_CAMERA] [--fps]
                 [--pref_width PREF_WIDTH] [--pref_height PREF_HEIGHT]
                 [--pref_fps PREF_FPS]
                 [--filter {Gray,NoFilter,Segment,Sepia,Shake,BlurBox,Frame,Pixel,BlurSat}]
                 [--verbose] [--logfile]

🎥 CustomCam. Extendable webcam modification on your commandline.

optional arguments:
  -h, --help            show this help message and exit
  --input_camera INPUT_CAMERA
                        ID of webcam device (default: 0)
  --output_camera OUTPUT_CAMERA
                        Dummy output device (default: /dev/video2)
  --pref_width PREF_WIDTH
                        Overwrite camera width. (default: None)
  --pref_height PREF_HEIGHT
                        Overwrite camera height. (default: None)
  --pref_fps PREF_FPS   Overwrite camera fps. (default: None)
  --filter {Gray,NoFilter,Segment,Sepia,Shake,BlurBox,Frame,Pixel,BlurSat}
  --verbose             Enable verbose logging. (default: False)
  --logfile             Write log to disk. (default: False)
```

### Mid-Run
Users are able to change the active filter, display statistics, flip the camera, close the program etc. whilst CustomCam is running by entering the appropriate command in the terminal in which CustomCam was launched.

```text
Filters:
• 'BlurBox': Blur background via single face detection.
• 'BlurSat': Blur background via saturation detection.
• 'Frame': Highlight targets of face detection.
• 'Gray': Apply grayscale.
• 'NoFilter': Applies no filters.
• 'Pixel': Pixelate individuals in the foreground.
• 'Segment': Blur background using mediapipe's SelfieSegmentation.
• 'Sepia': Apply sepia effect.
• 'Shake': Shake two channels horizontally.

Options:
• 'f', 'flip': Flip camera
• 's', 'stats': Display statistics
• 'h', 'help': Get this help
• 'q', 'quit': Exit CustomCam
```

## Creating your own filters
User-defined filters can be added to `filters.py`.

Filter classes must:
- Inherit from `filters.Filter`
- Implement a `__str__` method that return string containing a short description of the filter.
- Implement an `apply` method which takes a frame (as a `np.array`), applies filter logic and returns that a `np.array`.
- Not share a name with any existing class or input command.
