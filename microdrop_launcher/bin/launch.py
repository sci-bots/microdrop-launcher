import argparse
import logging
import os
import pkg_resources
import subprocess as sp
import sys

import mpm
import mpm.bin
import path_helpers as ph


def get_major_version(version):
    '''
    Parameters
    ----------
    version : pkg_resources.SetuptoolsVersion

    Returns
    -------
    int
        Major version number.
    '''
    return sum([(pkg_resources.parse_version('%d.0' % i) <= version)
                for i in xrange(5)]) - 1


logger = logging.getLogger(__name__)

INSTALL_REQUIREMENTS_PARSER = \
    argparse.ArgumentParser(add_help=False,
                            parents=[mpm.bin.LOG_PARSER,
                                     mpm.bin.PLUGINS_DIR_PARSER])


def parse_args(args=None):
    '''Parses arguments, returns (options, args).'''
    if args is None:
        args = sys.argv

    parser = argparse.ArgumentParser(description='Microdrop launcher',
                                     parents=[INSTALL_REQUIREMENTS_PARSER])
    parser.add_argument('--install-plugin-requirements', action='store_true')

    return parser.parse_args()


def main(args=None):
    if args is None:
        args = parse_args()
    args = mpm.bin.validate_args(args)
    logger.debug('Arguments: %s', args)

    if args.install_plugin_requirements:
        sp.call([sys.executable, '-m', 'mpm', '-d', args.plugins_directory,
                 'hook', 'on_install'])

    if args.config_file is None:
        args.config_file = (args.plugins_directory.parent
                            .joinpath('microdrop.ini'))

    release_version_path = args.config_file.parent.joinpath('RELEASE-VERSION')
    installed_version_str = pkg_resources.get_distribution('microdrop').version
    installed_version = pkg_resources.parse_version(installed_version_str)

    if release_version_path.isfile():
        release_version_str = release_version_path.lines()[0]
        release_version = pkg_resources.parse_version(release_version_str)
    else:
        with release_version_path.open('w') as output:
            output.write(installed_version_str)
        release_version = installed_version
    if not (get_major_version(release_version) ==
            get_major_version(installed_version)):
        logger.error('Configuration directory major version (%s) does not '
                     'match installed major MicroDrop version (%s)',
                     release_version, installed_version)
        raise SystemExit(-1)
    else:
        original_directory = ph.path(os.getcwd())
        try:
            os.chdir(args.config_file.parent)
            return_code = None
            # Return code of `5` indicates program should be restarted.
            while return_code is None or return_code == 5:
                return_code = sp.call([sys.executable, '-m',
                                       'microdrop.microdrop', '-c',
                                       args.config_file])
        finally:
            os.chdir(original_directory)


if __name__ == '__main__':
    main()
