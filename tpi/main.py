import argparse
import logging

log = logging.getLogger(__name__)


def get_main_parser():
    return argparse.ArgumentParser(prog="tpi")


def main(argv=None):
    parser = get_main_parser()
    args = parser.parse_args(argv)
    log.debug(args)
