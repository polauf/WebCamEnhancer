"""
Helper script to create locale directories and stuff.
"""

import os, shutil
from pathlib import Path
from WebCamEnhancer.constants import APP_NAME, APP_AUTHOR, APP_VERSION
from WebCamEnhancer.core.utils import init_gettext
init_gettext()
from googletrans import LANGUAGES, Translator
#from WebCamEnhancer.gui.settings import LANGUAGES

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
        pass
        # tryied to merge to add new words. maybe with little bt of more tinkering
        # os.chdir(lang_dir)
        # #git merge-file -p <current> <common> <other> > <dest>
        # os.system(f"touch empty.po")
        # os.system(f"git merge-file -p base.po empty.po ../../base.pot > test.po")

    os.chdir(lang_dir)
    os.system(f"python {tools_path/'msgfmt.py'} -o base.mo base")
    print(f"Generated 'base.mo' file for {name}")

