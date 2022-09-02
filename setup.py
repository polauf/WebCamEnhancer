#!/usr/bin/env python

from setuptools import setup


setup(
    name='CamEnhancer',
    version='0.1.0',
    description='Extendable webcam customisation in Python.',
    long_description=open("README.md", 'r').read(),
    long_description_content_type="text/markdown",
    authors=('Matous Polauf', 'Matt Ravenhall'),
    url='https://github.com/polauf/webvamenhancer',
    # package_dir={"CustomCam": "src"},
    packages=['CustomCam'],
    classifiers=[
          'Development Status :: 4 - Beta',
          'Environment :: Console',
          'Natural Language :: English',
          'Operating System :: POSIX :: Linux',
          'Operating System :: Microsoft :: Windows',
          'Operating System :: MacOS :: MacOS X',
          'Programming Language :: Python :: 3',
          'Topic :: Multimedia :: Video'
          ],
    entry_points={
        "console_scripts": [
            'CustomCam=CustomCam.__main__:run'
        ]
    },
    install_requires=open('requirements.txt', 'r').readlines(),
    python_requires='>=3.9',
)
