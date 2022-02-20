#!/usr/bin/env python3

"""Primary entry point to CustomCam from the command line."""

import inspect
import logging

from CustomCam.camera import CameraModifier
from CustomCam.utils import setup_logger, setup_argparse
import CustomCam.filters as filters


def run():
    """Command line run function."""

    # Set up argparse and logger
    args = setup_argparse()
    logger = setup_logger(
        "CustomCam",
        log_to_file=args.logfile,
        level=logging.DEBUG if args.verbose else logging.INFO
    )

    # Identify all filters
    filter_classes = dict(inspect.getmembers(filters, inspect.isclass))
    known_filters = {
        key: filter_classes[key](logger=logger) for key in filter_classes.keys()
        if key != 'Filter'
    }

    # Create cam-modifier
    modifier = CameraModifier(
        args.input_camera,
        args.output_camera,
        logger=logger,
        show_fps=args.fps,
        pref_width=args.pref_width,
        pref_height=args.pref_height,
        pref_fps=args.pref_fps,
        initial_filter=args.filter,
        filters=known_filters
    )

    logger.debug(args)

    logger.info(f"🎥 Welcome to CustomCam! 🎥")
    logger.info(f"---------------------------")

    # Start modifier
    modifier.run()


if __name__ == '__main__':
    run()
