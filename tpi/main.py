import argparse
import logging

log = logging.getLogger(__name__)


def get_main_parser():
    parser = argparse.ArgumentParser(prog="tpi")
    return parser


def main(argv=None):
    parser = get_main_parser()
    args = parser.parse_args(argv)
    log.debug(args)
