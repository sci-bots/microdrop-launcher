import os
import pkg_resources
import re
import subprocess as sp
import sys

from mpm.bin.install_dependencies import install_dependencies
import mpm
import mpm.commands
import mpm.bin
import pandas as pd
import path_helpers as ph
import yaml
try:
    import gtk
except ImportError:
    GUI_AVAILABLE = False
else:
    GUI_AVAILABLE = True

from .config import create_config_directory

cre_version = re.compile(r'^(?P<major>\d+)\.')

get_major_version = lambda version: '{}.0'.format(cre_version
                                                  .match(version)
                                                  .group('major'))

ICON_PATH = pkg_resources.resource_filename('microdrop', 'microdrop.ico')
SAVED_COLUMNS = ['used_timestamp', 'path']


def load_profiles_info(profiles_path):
    '''
    Load list of profiles from file.

    If file does not exist or list is empty, the profile list is initialized
    with the default profile directory path (creating a profile at the default
    location, if it does not already exist).

    Parameters
    ----------
    profiles_path : str
        Path to file containing list of profiles.

    Returns
    -------
    df_profiles : pandas.DataFrame
        Table of MicroDrop profile descriptions including the columns:

         - ``path`` File system path to profile directory.
         - ``used_timestamp`` Most recent time that profile was launched.
    '''
    profiles_path = ph.path(profiles_path)

    profiles_path.parent.makedirs_p()
    if profiles_path.exists():
        with profiles_path.open('r') as input_:
            profiles_str = input_.read()
            profiles = yaml.load(profiles_str)
    else:
        profiles = []

    default_profile_path = mpm.bin.get_plugins_directory().parent

    if not profiles and not default_profile_path.isdir():
        # No existing profiles.  Create default profile.
        print 'No existing profiles.  Create default profile at {}.'.format(default_profile_path)
        create_config_directory(output_dir=default_profile_path)

        for sub_directory_i in ('devices', 'plugins'):
            default_profile_path.joinpath(sub_directory_i).makedirs_p()

        # Create a `RELEASE-VERSION` file and populate it with the installed
        # MicroDrop package version.
        release_version_path = default_profile_path.joinpath('RELEASE-VERSION')
        with release_version_path.open('w') as output:
            output.write(pkg_resources.get_distribution('microdrop').version)

    if not profiles and default_profile_path.isdir():
        # No profiles list found or empty profiles list.
        #
        # Use default profile path.
        profiles = [{'path': str(default_profile_path),
                     'used_timestamp': None}]

    df_profiles = pd.DataFrame(profiles, columns=SAVED_COLUMNS)
    df_profiles.loc[df_profiles.used_timestamp == 'nan', 'used_timestamp'] = ''
    df_profiles.sort_values('used_timestamp', ascending=False, inplace=True)
    df_profiles.drop_duplicates(subset=['path'], inplace=True)
    return df_profiles


def drop_version_errors(df_profiles, missing=False, mismatch=False,
                        inplace=False):
    '''
    Drop rows for profiles with version errors.

    Parameters
    ----------
    df_profiles : pandas.DataFrame
        Table of MicroDrop profile descriptions.

        Must include *at least* the column ``path`` containing the file system
        path to each profile directory.
    missing : bool, optional
        If ``True``, drop rows for profiles where no ``RELEASE-VERSION`` file
        is found in the profile directory.
    mismatch : bool, optional
        If ``True``, drop rows for profiles where major version in
        ``RELEASE-VERSION`` file and major version of installed MicroDrop
        package **do not match**.
    inplace : bool, optional
        If ``True``, do operation inplace and return None.
    '''
    def version_error(profile_path):
        try:
            verify_profile_version(profile_path)
        except RuntimeError:
            # Major version in `RELEASE-VERSION` file and major version of
            # installed MicroDrop package **do not match**.
            return mismatch
        except IOError:
            # No `RELEASE-VERSION` file found in the profile directory.
            return missing
        else:
            return False

    error_mask = df_profiles.path.map(version_error)
    result = df_profiles.drop(error_mask[error_mask].index, inplace=inplace)
    if inplace:
        return df_profiles
    else:
        return result


def verify_profile_version(profile_path):
    '''
    Parameters
    ----------
    profile_path : str
        Path to profile directory.

    Raises
    ------
    IOError
        If no version file found in profile directory.
    RuntimeError
        If profile version does not match installed MicroDrop version.
    '''
    profile_path = ph.path(profile_path)

    release_version_path = profile_path.joinpath('RELEASE-VERSION')

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
        # No `RELEASE-VERSION` file found in the profile directory.
        raise IOError('No version file found in profile directory.')

    if not (get_major_version(release_version_str) ==
            get_major_version(installed_version_str)):
        # Major version in `RELEASE-VERSION` file and major version of
        # installed MicroDrop package **do not match**.
        #
        # Notify the user and wait for user input to continue.
        raise RuntimeError('Configuration directory major version (%s) does '
                           'not match installed major MicroDrop version (%s)'
                           % (release_version, installed_version))


def launch_profile(profile_path):
    profile_path = ph.path(profile_path)
    config_file = profile_path.joinpath('microdrop.ini')

    try:
        verify_profile_version(profile_path)
    except IOError:
        # No `RELEASE-VERSION` file found in the profile directory.

        if GUI_AVAILABLE:
            # Prompt user to confirm profile version matches installed
            # MicroDrop version.
            dialog = gtk.MessageDialog(type=gtk.MESSAGE_QUESTION)
            dialog.set_icon_from_file(ICON_PATH)
            dialog.set_title('Confirm MicroDrop {} profile'
                            .format(installed_major_version()))
            dialog.add_buttons(gtk.STOCK_YES, gtk.RESPONSE_YES,
                            gtk.STOCK_NO, gtk.RESPONSE_NO)
            dialog.set_markup('Unable to determine compatible MicroDrop '
                              'version from profile:\n\n    {}\n\n'
                              'Was this profile created using the installed '
                              'version of MicroDrop ({})?'
                              .format(profile_path, installed_major_version()))
            label = (dialog.get_content_area().get_children()[0]
                     .get_children()[-1].get_children()[0])
            label.set_tooltip_text(profile_path)
            response = dialog.run()
            dialog.destroy()
            if response == gtk.RESPONSE_NO:
                raise RuntimeError('Not launching MicroDrop since profile was '
                                   'not created using the installed version of'
                                   ' MicroDrop ({})'
                                   .format(installed_major_version()))

        # Create a `RELEASE-VERSION` file and populate it with the installed
        # MicroDrop package version.
        release_version_path = profile_path.joinpath('RELEASE-VERSION')
        with release_version_path.open('w') as output:
            output.write(pkg_resources.get_distribution('microdrop').version)

    # Major version in `RELEASE-VERSION` file and major version of
    # installed MicroDrop package **match**.
    original_directory = ph.path(os.getcwd())
    try:
        # Change directory into the parent directory of the configuration
        # file.
        os.chdir(config_file.parent)
        return_code = None
        # Return code of `5` indicates program should be restarted.
        while return_code is None or return_code == 5:
            # Launch MicroDrop and save return code.
            return_code = sp.call([sys.executable, '-m',
                                    'microdrop.microdrop', '-c',
                                    config_file])
    finally:
        # Restore original working directory.
        os.chdir(original_directory)
    return return_code


def profile_major_version(profile):
    release_version_path = ph.path(profile).joinpath('RELEASE-VERSION')
    if release_version_path.isfile():
        return get_major_version(release_version_path.lines()[0])


def installed_major_version():
    installed_version_str = pkg_resources.get_distribution('microdrop').version
    return get_major_version(installed_version_str)


def import_profile(df_profiles, profile_path):
    '''
    Run post-installation hook for each plugin in profile and append imported
    profile to profiles table.

    Parameters
    ----------
    df_profiles : pandas.DataFrame
        Table of MicroDrop profile descriptions.

        Must include *at least* the column ``path`` containing the file system
        path to each profile directory.
    profile_path : str
        Path to profile directory.

    Returns
    -------
    pandas.DataFrame
        Table of MicroDrop profile descriptions with row appended for imported
        profile.
    '''
    plugins_directory = (mpm.commands
                         .get_plugins_directory(microdrop_user_root=
                                                profile_path))
    install_dependencies(plugins_directory)
    major_version = profile_major_version(profile_path)
    df_profiles = df_profiles.append({'path': profile_path,
                                      'major_version': major_version},
                                     ignore_index=True)
    df_profiles.drop_duplicates(subset=['path'], inplace=True)
    return df_profiles