from ..constants import APP_NAME, TRANSLATIONS_DIR
import gettext

gettext.bindtextdomain(APP_NAME, TRANSLATIONS_DIR)
gettext.textdomain(APP_NAME)


# TODO: Replace with actual config window
cfg = {
    "input_cam": "0",
    "output_cam": '/dev/video2',
    "width": 1024,
    "height": 726,
    "fps": None,
    "lang": "en"
}

try:
    tt = gettext.translation('base', localedir=TRANSLATIONS_DIR, languages=[cfg["lang"]]).gettext
except FileNotFoundError:
    tt = gettext.gettext

LANGUAGES = [("cs",tt("Czech"))]
