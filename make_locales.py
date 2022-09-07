"""
Helper script to create locale directories and stuff.
"""

import os, shutil
from pathlib import Path
from WebCamEnhancer.constants import APP_NAME, APP_AUTHOR, APP_VERSION
from WebCamEnhancer.core.utils import init_gettext
init_gettext()
from googletrans import LANGUAGES, Translator
from copy import deepcopy

tools_path = Path('/usr/lib/python3.10/Tools/i18n/')

there = Path(__file__).parent / 'WebCamEnhancer/locales'
os.chdir(there)
os.system(f"python {tools_path/'pygettext.py'} -k tt -d base -o base.pot ../gui/*.py")
print("base.pot generated.")

translator = Translator()
print(translator.translate("Ahoj"))

def g_translate(fh, lang):
    code = ""
    done = False
    out = []
    for line in fh.readlines():
        if line.startswith("msgid"):
            try:
                code = line.split("\"")[1]
            except IndexError:
                pass
        elif code and line.startswith("msgstr \"\""):
            try:
                word = translator.translate(code, src="en",dest=lang).text
            except Exception as e:
                print(f"Translate not working: {e}: {e.args}")
            line = f"msgstr \"{word}\""
            print(f"Translated({lang}): {code} -> {word}")
            code = ""
        out.append(line)
    return "".join(out)

codes = []
with open(there/ 'base.pot','r') as fh:
    for line in fh.readlines():
        if line.startswith("msgid"):
            codes.append(line.split("\"")[1])

for l, name in LANGUAGES.items():
    if l == 'en':
        continue
    lang_dir = there / l / 'LC_MESSAGES'
    lang_dir.mkdir(exist_ok=True, parents=True)
    if not (lang_dir / 'base.po').exists():
        print(f"Generate for {name} {lang_dir / 'base.po'}")
        shutil.copy(there / 'base.pot', lang_dir / 'base.po')
        with open(lang_dir/ 'base.po','r') as fh:
            d = g_translate(fh, l)
            d = d.replace('PACKAGE VERSION',APP_VERSION)
            d = d.replace('FIRST AUTHOR <EMAIL@ADDRESS>, YEAR.', f"{APP_AUTHOR} <matous@polauf.cz>, 2022.")
            d = d.replace('Copyright (C) YEAR ORGANIZATION', 'Copyleft. Provided AS IS.')
            d = d.replace('SOME DESCRIPTIVE TITLE.', f"Translation for {APP_NAME}.")
            d = d.replace('Language-Team: LANGUAGE <LL@li.org>', f"Language-Team: GOOGLE-TRANSLATOR-{name} <{l.upper()}@{l}.org>")
        with open(lang_dir / 'base.po','w') as fh:
            fh.write(d)
    else:
        out = []
        has = deepcopy(codes)
        with open(lang_dir/ 'base.po') as fh:
            for line in fh.readlines():
                if line.startswith("msgid"):
                    try:
                        has.remove(line.split("\"")[1])
                    except ValueError:
                        pass
                out.append(line)
            if has:
                for code in has:
                    try:
                        word = translator.translate(code, src="en",dest=l).text
                        out.append('\n')
                        out.append(f"msgid \"{code}\"\n")
                        out.append(f"msgstr \"{word}\"\n")
                    except Exception as e:
                        print(f"Translate not working: {e}: {e.args}")
        with open(lang_dir/ 'base.po', 'w') as fh:
            fh.write("".join(out))

    os.chdir(lang_dir)
    os.system(f"python {tools_path/'msgfmt.py'} -o base.mo base")
    print(f"Generated 'base.mo' file for {name}")

