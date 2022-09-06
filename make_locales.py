"""
Helper script to create locale directories and stuff.
"""

import os, shutil
from pathlib import Path
from WebCamEnhancer.constants import APP_NAME, APP_AUTHOR, APP_VERSION
from WebCamEnhancer.gui.settings import LANGUAGES

tools_path = Path('/usr/lib/python3.10/Tools/i18n/')

there = Path(__file__).parent / 'WebCamEnhancer/locales'
os.chdir(there)
os.system(f"python {tools_path/'pygettext.py'} -k tt -d base -o base.pot ../gui/*.py")
print("base.pot generated.")

for l,name in LANGUAGES:
    if l == 'en':
        continue
    lang_dir = there / l / 'LC_MESSAGES'
    lang_dir.mkdir(exist_ok=True, parents=True)
    if not (lang_dir / 'base.po').exists():
        print(f"Generate for {name} {lang_dir / 'base.po'}")
        shutil.copy(there / 'base.pot', lang_dir / 'base.po')
        with open(lang_dir/ 'base.po','r') as fh:
            d = fh.read()
            d = d.replace('PACKAGE VERSION',APP_VERSION)
            d = d.replace('FIRST AUTHOR <EMAIL@ADDRESS>, YEAR.', f"{APP_AUTHOR} <matous@polauf.cz>, 2022.")
            d = d.replace('Copyright (C) YEAR ORGANIZATION', 'Copyleft. Provided AS IS.')
            d = d.replace('SOME DESCRIPTIVE TITLE.', f"Translation for {APP_NAME}.")
            d = d.replace('Language-Team: LANGUAGE <LL@li.org>', f"Language-Team: {name} <{l.upper()}@{l}.org>")
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

