# CustomCam

Extendable webcam customisation in Python.

Fork of [CustomCam](https://github.com/mattravenhall/CustomCam).

CustomCam uses [pyvirtualcamera](https://github.com/letmaik/pyvirtualcam) to interact with virtual output devices. As this package was primarily developed for Linux, the Quick Start commands address that use case. To set up virtual output devices for other platforms, check the [pyvirtualcam docs](https://github.com/letmaik/pyvirtualcam/blob/master/README.md).

## Usage
### On-Launch

Temporarly:

 if you want to run it, in root dir `WebCameraEnhancer` run `python -m CustomCam` + arguments. (Need work to become package again ... TODO for now.)


```text
CustomCam. Extendable webcam modification on your commandline.

options:
  -h, --help            show this help message and exit
  --input INPUT, -i INPUT
                        ID of webcam device (default: 0)
  --output OUTPUT, -o OUTPUT
                        Dummy output device (default: /dev/video2)
  --width WIDTH, -cw WIDTH
                        Overwrite camera width. (default: 1024)
  --height HEIGHT, -ch HEIGHT
                        Overwrite camera height. (default: 768)
  --fps FPS             Overwrite camera fps. (default: None)
  --filter {LMan,Pixel,Cascade,Away,Anonymous,NoFilter,Gray,Selfie,Background,SelfieCascade,Config,Sepia,Shake,LaughingMan}, -f {LMan,Pixel,Cascade,Away,Anonymous,NoFilter,Gray,Selfie,Background,SelfieCascade,Config,Sepia,Shake,LaughingMan}
  --verbose, -v         Enable verbose logging. (default: False)
  --logfile, -lf        Write log to disk. (default: False)           Write log to disk. (default: False)
```

### Mid-Run
Users are able to change the active filter, display statistics, flip the camera, close the program etc. whilst CustomCam is running by entering the appropriate command in the terminal in which CustomCam was launched.

```text
Filters:
	Anonymous       Pixalated person with background picture.
	Away            Away sign with background picture.
	Background      Repleaces background with a picture.
	Gray            Grayscale image.
	LMan            Pixalated rest of the person with background picture and Laughing man overlay.
	LaughingMan     Only Laughing man overlay.
	NoFilter        Nothing.
	Pixel           Blur foreground person.
	Sepia           Classic sepia filter.
	Shake           Shake two channels horizontally every frame.

Options:
	f, flip         Flip the camera.
	s, stats        Display information about stream.
	z+, z-          Zoom picture.
	a, p            Fast switch between default filters: Away (Away) or Present (Background).
	h, help         Get this help.
	q, quit         Exits the application.

```

## Creating your own filters
User-defined filters can be added to `filters.py`.

Filter classes must:
- Inherit from `middleware.Filter`
- Implement an `apply` method which takes a frame (as a `np.array`), applies filter logic and returns that a `np.array`.
- Not share a name with any existing class or input command.
