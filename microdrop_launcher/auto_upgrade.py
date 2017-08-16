import json
import logging

import pip_helpers as pih

import conda_helpers as ch


logger = logging.getLogger(__name__)


def _strip_conda_menuinst_messages(conda_output):
    '''
    Strip away Conda menuinst log messages to work around [issue with
    `menuinst`][0].

    For example:

        INFO menuinst_win32:__init__(182): Menu: name: 'MicroDrop', prefix: 'C:\Users\chris\Miniconda2\envs\dropbot.py', env_name: 'dropbot.py', mode: 'None', used_mode: 'user'

    See [here][1] for more information.

    [0]: https://github.com/ContinuumIO/menuinst/issues/49
    [1]: https://groups.google.com/a/continuum.io/forum/#!topic/anaconda/RWs9of4I2KM
    '''
    return '\n'.join(line_i for line_i in conda_output.splitlines()
                     if not line_i.strip().startswith('INFO'))


def _strip_progress_messages(conda_output):
    '''
    Strip progress messages from Conda install output log.

    For example:

        {"maxval": 133256, "finished": false, "fetch": "microdrop-laun", "progress": 0}
    '''
    cre_json_progress = re.compile(r'{"maxval":[^,]+,\s+"finished":[^,]+,'
                                   r'\s+"fetch":\s+[^,]+,\s+"progress":[^}]+}')
    return '\n'.join(line_i for line_i in conda_output.splitlines()
                     if not cre_json_progress.search(line_i))


def main():
    '''
    .. versionadded:: 0.1.post62

    .. versionchanged:: 0.7.5
        Use Conda install dry-run to check for new version.

    .. versionchanged:: 0.7.6
        Fix displayed package name during upgrade.

        Fail gracefully with warning on JSON decode error.
    '''
    # Upgrade `microdrop-launcher` package if there is a new version available.
    print 'Checking for `microdrop-launcher` updates',

    # Check if new version of `microdrop-launcher` would be installed.
    dry_run_response = json.loads(ch.conda_exec('install', '--dry-run',
                                                '--json',
                                                'microdrop-launcher',
                                                verbose=False))
    try:
        dry_run_unlinked, dry_run_linked = ch.install_info(dry_run_response)
    except RuntimeError, exception:
        if 'CondaHTTPError' in str(exception):
            print 'Error checking for updates - no network connection'
            return
        else:
            print 'Error checking for updates.\n{}'.format(exception)
    else:
        # Try to find package specifier for new version of
        # `midrodrop-launcher`.
        # **N.B.**, `dry_run_linked` will be `None` if there is no new version.
        launcher_packages = [package_i for package_i, channel_i in
                             (dry_run_linked or [])
                             if 'microdrop-launcher' ==
                             package_i.split('==')[0]]
        if dry_run_linked and launcher_packages:
            # A new version of the launcher is available for installation.
            print 'Upgrading to:', launcher_packages[0]
            install_log_json = ch.conda_exec('install', '--json',
                                             'microdrop-launcher', '--quiet',
                                             verbose=False)
            install_log_json = _strip_conda_menuinst_messages(install_log_json)
            try:
                install_response = json.loads(install_log_json)
            except ValueError:
                # Error decoding JSON response.
                # XXX Assume install succeeded.
                print ('Warning: could not decode `microdrop-launcher` install'
                       ' log:')
                print install_log_json
                return
            unlinked, linked = ch.install_info(install_response)
            print 'Uninstall:'
            print '\n'.join(' - `{} (from {})`'.format(package_i, channel_i)
                            for package_i, channel_i in unlinked)
            print ''
            print 'Install:'
            print '\n'.join(' - `{} (from {})`'.format(package_i, channel_i)
                            for package_i, channel_i in linked)
        else:
            # No new version of the launcher is available for installation.
            print ('Up to date: {}'
                   .format(ch.package_version('microdrop-launcher',
                                              verbose=False)
                           .get('dist_name')))


if __name__ == '__main__':
    main()
