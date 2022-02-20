#!/usr/bin/env python

from setuptools import setup


setup(
    name='CustomCam',
    version='0.0.2',
    description='Extendable webcam customisation in Python.',
    long_description=open("README.md", 'r').read(),
    long_description_content_type="text/markdown",
    author='Matt Ravenhall',
    url='https://github.com/mattravenhall/CustomCam',
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
    python_requires='>=3.7',
)
