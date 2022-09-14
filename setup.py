#!/usr/bin/env python

from setuptools import setup, find_packages
from glob import glob

setup(
    name='WebCamEnhancer',
    version='0.5.1',
    description='Webcam enhancement controler with Tkinter GUI and console.',
    long_description=open("README.md", 'r').read(),
    long_description_content_type="text/markdown",
    authors=('Matous Polauf', 'Matt Ravenhall'),
    url='https://github.com/polauf/WebCamEnhancer',
    data_files=[
        ("pictures", glob('./WebCamEnhancer/img/*.*')),
        ("icons", glob('./WebCamEnhancer/icons/*.png')),
        ("locales", glob('./WebCamEnhancer/locales/*/*/base.po'))
    ],
    include_package_data=True,
    packages=find_packages(),
    classifiers=[
          'Development Status :: 4 - Beta',
          # 'Environment :: Console',
          'Environment :: X11 Applications',
          'Natural Language :: English',
          'Operating System :: POSIX :: Linux',
          'Operating System :: Microsoft :: Windows',
          'Operating System :: MacOS :: MacOS X',
          'Programming Language :: Python :: 3',
          'Topic :: Multimedia :: Video',
          'Topic :: Scientific/Engineering :: Image Processing',
          'Topic :: Scientific/Engineering :: Image Recognition'
          ],
    entry_points={
        "console_scripts": [
            'CustomCam=WebCamEnhancer.__main__:run'
        ]
    },
    install_requires=open('requirements.txt', 'r').readlines(),
    python_requires='>=3.10',
)
