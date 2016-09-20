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
        # Run plugin "on_install" hook.
        sp.call([sys.executable, '-m', 'mpm', '-d', args.plugins_directory,
                 'hook', 'on_install'])

    if args.config_file is None:
        # No configuration file specified, so construct configuration file path
        # based on plugins directory path.
        args.config_file = (args.plugins_directory.parent
                            .joinpath('microdrop.ini'))

    # Construct path to `RELEASE-VERSION` based on path to configuration file
    # (they should be in the same parent directory).
    release_version_path = args.config_file.parent.joinpath('RELEASE-VERSION')

    # Query the currently installed version of the MicroDrop Python package.
    installed_version_str = pkg_resources.get_distribution('microdrop').version
    installed_version = pkg_resources.parse_version(installed_version_str)

    if release_version_path.isfile():
        # A `RELEASE-VERSION` file exists in the same directory as the
        # configuration file.
        #
        # Parse the version from the `RELEASE-VERSION` file.
        release_version_str = release_version_path.lines()[0]
        release_version = pkg_resources.parse_version(release_version_str)
    else:
        # No `RELEASE-VERSION` file found in the same directory as the
        # configuration file.
        #
        # Create a `RELEASE-VERSION` file and populate it with the installed
        # MicroDrop package version.
        with release_version_path.open('w') as output:
            output.write(installed_version_str)
        release_version = installed_version

    if not (get_major_version(release_version) ==
            get_major_version(installed_version)):
        # Major version in `RELEASE-VERSION` file and major version of
        # installed MicroDrop package **do not match**.
        #
        # Notify the user and wait for user input to continue.
        logger.error('Configuration directory major version (%s) does not '
                     'match installed major MicroDrop version (%s)',
                     release_version, installed_version)
        print 'Press <enter> to continue...', raw_input()
        raise SystemExit(-1)
    else:
        # Major version in `RELEASE-VERSION` file and major version of
        # installed MicroDrop package **match**.
        original_directory = ph.path(os.getcwd())
        try:
            # Change directory into the parent directory of the configuration
            # file.
            os.chdir(args.config_file.parent)
            return_code = None
            # Return code of `5` indicates program should be restarted.
            while return_code is None or return_code == 5:
                # Launch MicroDrop and save return code.
                return_code = sp.call([sys.executable, '-m',
                                       'microdrop.microdrop', '-c',
                                       args.config_file])
        finally:
            # Restore original working directory.
            os.chdir(original_directory)


if __name__ == '__main__':
    main()
