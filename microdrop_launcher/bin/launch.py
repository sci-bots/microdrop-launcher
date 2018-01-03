import argparse
import logging
import subprocess as sp
import sys

import mpm
import mpm.bin

from ..auto_upgrade import main as auto_upgrade
from ..profile import launch_profile


logger = logging.getLogger(__name__)

INSTALL_REQUIREMENTS_PARSER = \
    argparse.ArgumentParser(add_help=False,
                            parents=[mpm.bin.LOG_PARSER,
                                     mpm.bin.PLUGINS_DIR_PARSER])


def parse_args(args=None):
    '''Parses arguments, returns (options, args).'''
    if args is None:
        args = sys.argv

    parser = argparse.ArgumentParser(description='MicroDrop launcher',
                                     parents=[INSTALL_REQUIREMENTS_PARSER])
    parser.add_argument('--install-plugin-requirements', action='store_true')
    parser.add_argument('--no-upgrade', action='store_true',
                        help='Do not check for package upgrade.')

    return parser.parse_args()


def main(args=None):
    if args is None:
        args = parse_args()
    args = mpm.bin.validate_args(args)
    logger.debug('Arguments: %s', args)

    if args.install_plugin_requirements:
        # Run plugin "on_install" hook.
        sp.call([sys.executable, '-m', 'mpm', '-d', args.plugins_directory,
                 'hook', 'on_install'])

    if args.config_file is None:
        # No configuration file specified, so construct configuration file path
        # based on plugins directory path.
        args.config_file = (args.plugins_directory.parent
                            .joinpath('microdrop.ini'))

    return_code = launch_profile(args.config_file.parent)

    if not args.no_upgrade:
        # Upgrade `microdrop-launcher` package if there is a new version
        # available.
        print 'Checking for `microdrop-launcher` updates',
        upgrade_info = auto_upgrade()
        if upgrade_info['new_version']:
            print 'Upgraded to:', upgrade_info['new_version']
        else:
            print ('Up to date: microdrop-launcher=={}'
                   .format(upgrade_info['original_version']))

    return return_code


if __name__ == '__main__':
    raise SystemExit(main())
