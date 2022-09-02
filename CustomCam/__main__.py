import inspect
import logging
from camera import CameraModifier
from utils import setup_logger, setup_argparse
import filters as filters
import middleware


try:
    # Set up argparse and logger
    args = setup_argparse()
    logger = setup_logger(
        "CustomCam",
        log_to_file=args.logfile,
        level=logging.DEBUG if args.verbose else logging.INFO
    )
    # Identify all filters anf filter out middleware classes
    middleware_classes = dict(inspect.getmembers(middleware, lambda x: inspect.isclass(x) and issubclass(x, middleware.Filter))).values()
    filter_classes = dict(inspect.getmembers(filters, lambda x: inspect.isclass(x) and issubclass(x, middleware.Filter) and x not in middleware_classes))

    # Main thing
    modifier = CameraModifier(
        args.input,
        args.output,
        logger=logger,
        pref_width=args.width,
        pref_height=args.height,
        pref_fps=args.fps,
        initial_filter=args.filter,
        filters={n: c() for n,c in filter_classes.items()}
    )

    logger.debug(args)

    # Run main thing
    modifier.run()

except KeyboardInterrupt:
    logger.info("Ending streams. Good bye!")
        
