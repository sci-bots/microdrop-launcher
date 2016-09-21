import datetime as dt
import functools as ft
import os
import pkg_resources
import re
import subprocess as sp
import sys

import gtk
import microdrop_launcher as mdl
import microdrop_launcher.dirs
import mpm
import mpm.bin
import pandas as pd
import path_helpers as ph
import pygtkhelpers.ui.dialogs as gd
import yaml

from microdrop_launcher.config import create_config_directory

cre_version = re.compile(r'^(?P<major>\d+)\.')

get_major_version = lambda version: '{}.0'.format(cre_version
                                                  .match(version)
                                                  .group('major'))
SAVED_COLUMNS = ['used_timestamp', 'path']
ICON_PATH = pkg_resources.resource_filename('microdrop', 'microdrop.ico')


def get_profiles_table(df_profiles, launch_callback, remove_callback,
                       short_threshold=40):
    def short_path(path_i):
        base_i, name_i = ph.path(path_i).splitpath()

        if len(base_i) > short_threshold:
            base_i = ph.path(base_i[:short_threshold]).parent.joinpath('...')
        return base_i.joinpath(name_i)

    grid_columns = ['path', 'major_version']
    # One header row plus one row per profile
    # One column for each column in `grid_columns`, plus two columns for launch
    # and remove buttons, respectively.
    table = gtk.Table(df_profiles.shape[0] + 1, len(grid_columns) + 2)

    for i, column_i in enumerate(grid_columns):
        label_i = gtk.Label()
        label_i.set_markup('<b>{}</b>'.format(column_i))
        table.attach(label_i, left_attach=i, right_attach=i + 1, top_attach=0,
                     bottom_attach=1, xpadding=5, ypadding=5,
                     xoptions=gtk.SHRINK, yoptions=gtk.SHRINK)

    for i, (ix, row_i) in enumerate(df_profiles.iterrows()):
        row_kwargs = dict(top_attach=i + 1, bottom_attach=i + 2,
                          xpadding=5, ypadding=5,
                          xoptions=gtk.SHRINK | gtk.FILL, yoptions=gtk.SHRINK)
        for j, column_ij in enumerate(grid_columns):
            if column_ij == 'path':
                label_ij = gtk.Label(short_path(row_i.path))
                timestamp_str_ij = re.sub(r'\.\d+$', '',
                                          str(row_i.used_timestamp))
                label_ij.set_tooltip_text('{}\nLast used: {}'
                                          .format(row_i.path,
                                                  timestamp_str_ij))
                label_ij.set_alignment(0, .5)
            else:
                label_ij = gtk.Label(row_i[column_ij])
            table.attach(label_ij, left_attach=j, right_attach=j + 1,
                         **row_kwargs)

        button_launch_i = gtk.Button('Launch')
        button_open_i = gtk.Button('Open')
        button_remove_i = gtk.Button('Remove')
        on_launch_clicked = ft.partial(launch_callback, row_i)
        on_open_clicked = ft.partial(ph.path(row_i.path).launch)
        on_remove_clicked = ft.partial(remove_callback, row_i)
        button_launch_i.connect('clicked', lambda *args: on_launch_clicked())
        button_open_i.connect('clicked', lambda *args: on_open_clicked())
        button_remove_i.connect('clicked', lambda *args: on_remove_clicked())
        # button_remove_i.connect('clicked', lambda
        for button_ij, j in zip((button_launch_i, button_open_i,
                                 button_remove_i), range(j + 1, j + 4)):
            table.attach(button_ij, left_attach=j, right_attach=j + 1,
                         **row_kwargs)

    scrolled_window = gtk.ScrolledWindow()
    scrolled_window.set_policy(hscrollbar_policy=gtk.POLICY_AUTOMATIC,
                               vscrollbar_policy=gtk.POLICY_ALWAYS)
    scrolled_window.add_with_viewport(table)
    scrolled_window.props.shadow_type = gtk.SHADOW_NONE
    scrolled_window.get_child().props.shadow_type = gtk.SHADOW_NONE
    frame = gtk.Frame(label='Select profile to launch')
    frame.add(scrolled_window)
    # frame.props.shadow_type = gtk.SHADOW_NONE
    frame.show_all()
    return frame


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

        # Prompt user to confirm profile version matches installed MicroDrop
        # version.
        dialog = gtk.MessageDialog(type=gtk.MESSAGE_QUESTION)
        dialog.set_icon_from_file(ICON_PATH)
        dialog.set_title('Confirm MicroDrop {} profile'
                         .format(installed_major_version()))
        dialog.add_buttons(gtk.STOCK_YES, gtk.RESPONSE_YES,
                           gtk.STOCK_NO, gtk.RESPONSE_NO)
        dialog.set_markup('Unable to determine compatible MicroDrop version '
                          'from profile:\n\n    {}\n\n'
                          'Was this profile created using the installed '
                          'version of MicroDrop ({})?'
                          .format(profile_path, installed_major_version()))
        label = (dialog.get_content_area().get_children()[0].get_children()[-1]
                 .get_children()[0])
        label.set_tooltip_text(profile_path)
        response = dialog.run()
        dialog.destroy()
        if response == gtk.RESPONSE_NO:
            raise RuntimeError('Not launching MicroDrop since profile was not '
                               'created using the installed version of '
                               'MicroDrop ({})'
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


def launch_profile_row(profile_row_i):
    try:
        return_code = launch_profile(profile_row_i.path)
    except Exception, exception:
        dialog = gtk.MessageDialog(type=gtk.MESSAGE_ERROR,
                                   message_format=str(exception))
        dialog.set_icon_from_file(ICON_PATH)
        dialog.set_title('Error launching profile')
        dialog.add_buttons(gtk.STOCK_OK, gtk.RESPONSE_OK)
        dialog.run()
        dialog.destroy()
    else:
        return return_code


class LaunchDialog(object):
    def __init__(self, df_profiles):
        self.df_profiles = df_profiles
        self.content_area = None
        self.frame = None
        self.profile_row = None
        self.return_code = None

    def import_profile(self, folder=None):
        # Display GTK dialog to select output directory.
        folder = gd.select_folder(folder=folder, title='Select MicroDrop '
                                  'profile directory')
        if folder is None:
            return

        major_version = profile_major_version(folder)
        self.df_profiles = self.df_profiles.append({'path': folder,
                                                    'major_version':
                                                    major_version},
                                                   ignore_index=True)
        self.df_profiles.drop_duplicates(subset=['path'], inplace=True)
        self.update_profiles_frame()

    def create_profile(self, folder=None):
        # Display GTK dialog to select output directory.
        folder = gd.select_folder(folder=folder, title='Select new MicroDrop '
                                  'profile directory')
        if folder is None:
            return
        else:
            folder = ph.path(folder).realpath()

        if folder.files() or folder.dirs():
            response = gd.yesno('Directory is not empty.\n\nOverwrite?')
            if response == gtk.RESPONSE_NO:
                return
        try:
            create_config_directory(output_dir=folder, overwrite=True)
        except IOError, exception:
            print >> sys.stderr, exception
            return
        else:
            folder.joinpath('devices').makedirs_p()
            folder.joinpath('plugins').makedirs_p()

        self.df_profiles = self.df_profiles.append({'path': folder,
                                                    'major_version':
                                                    installed_major_version()},
                                                   ignore_index=True)
        self.df_profiles.drop_duplicates(subset=['path'], inplace=True)
        self.update_profiles_frame()

    def update_profiles_frame(self):
        def on_launch_clicked(profile_row_i):
            self.dialog.hide()
            self.profile_row = profile_row_i.copy()
            self.return_code = launch_profile_row(profile_row_i)
            if self.return_code is None:
                self.frame = None
                self.run()
            elif self.return_code == 0:
                profile_row_i.used_timestamp = str(dt.datetime.now())

        def on_remove_clicked(profile_row_i):
            dialog = gtk.MessageDialog(type=gtk.MESSAGE_QUESTION)
            dialog.set_icon_from_file(ICON_PATH)
            dialog.set_title('Remove profile')
            RESPONSE_REMOVE, RESPONSE_REMOVE_WITH_DATA, RESPONSE_CANCEL = \
                range(3)
            dialog.add_buttons('_Remove', RESPONSE_REMOVE, 'Remove with _data',
                               RESPONSE_REMOVE_WITH_DATA, 'Can_cel',
                               RESPONSE_CANCEL)
            dialog.set_markup('Remove profile from list?\n\n'
                              '<b>"Remove with data"</b> removes profile from '
                              'list <b>and deletes the profile '
                              'directory</b>.')
            response = dialog.run()
            dialog.destroy()
            if response not in (RESPONSE_REMOVE, RESPONSE_REMOVE_WITH_DATA):
                return
            try:
                if response == RESPONSE_REMOVE_WITH_DATA:
                    response = gd.yesno('Remove profile data (cannot be '
                                        'undone)?')
                    if response == gtk.RESPONSE_YES:
                        ph.path(profile_row_i.path).rmtree()
                    else:
                        return
            except Exception, exception:
                gd.error(str(exception))
            finally:
                self.df_profiles = (self.df_profiles
                                    .loc[self.df_profiles.path !=
                                         profile_row_i.path].copy())
            self.update_profiles_frame()

        if self.frame is not None:
            self.content_area.remove(self.frame)
        self.frame = get_profiles_table(self.df_profiles, on_launch_clicked,
                                        on_remove_clicked)
        self.content_area.pack_start(self.frame, expand=True, fill=True, padding=10)
        self.content_area.reorder_child(self.frame, 0)

    def run(self):
        self.dialog = gtk.Dialog()
        self.dialog.set_icon_from_file(ICON_PATH)
        self.dialog.set_title('MicroDrop Profile Manager')
        self.content_area = self.dialog.get_content_area()

        buttons_area = gtk.HBox()
        buttons_box = gtk.HButtonBox()
        button_import = gtk.Button('Import...')
        button_create = gtk.Button('Create...')
        button_import.connect('clicked', lambda *args:
                              self.import_profile(self.df_profiles
                                                  .path.get(0)))
        button_create.connect('clicked', lambda *args:
                              self.create_profile(self.df_profiles.path
                                                  .get(0)))
        for button_i in (button_import, button_create):
            buttons_box.pack_end(button_i, expand=False, fill=False)
        buttons_area.pack_end(buttons_box, expand=False, fill=False)
        buttons_area.show_all()
        self.content_area.pack_end(buttons_area, expand=False, fill=False)

        self.update_profiles_frame()
        self.dialog.show()
        table = self.frame.get_child().get_child().get_child()
        x, y, width, height = table.get_allocation()
        self.dialog.set_size_request(width + 30, 320)
        self.dialog.props.resizable = False
        self.dialog.run()

        return self.profile_row


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


def profile_major_version(profile):
    release_version_path = ph.path(profile).joinpath('RELEASE-VERSION')
    if release_version_path.isfile():
        return get_major_version(release_version_path.lines()[0])


def installed_major_version():
    installed_version_str = pkg_resources.get_distribution('microdrop').version
    return get_major_version(installed_version_str)


def parse_args(args=None):
    '''Parses arguments, returns (options, args).'''
    from argparse import ArgumentParser

    if args is None:
        args = sys.argv

    major_version = get_major_version(pkg_resources
                                      .get_distribution('microdrop').version)
    # Look up MicroDrop application directories based on major version.
    microdrop_env_dirs = mdl.dirs.AppDirs('MicroDrop', version=major_version)
    # Construct path to list of profiles based on user configuration directory.
    default_profiles_path = (microdrop_env_dirs.user_config_dir
                             .joinpath('profiles.yml'))

    parser = ArgumentParser(description='MicroDrop {} profile manager'
                            .format(major_version))

    parser.add_argument('-f', '--profiles-path', type=ph.path,
                        help='Path to profiles list (default=%(default)s)',
                        default=default_profiles_path)
    parser.add_argument('--default', action='store_true',
                        help='Launch most recently used profile.')

    args = parser.parse_args()

    if not args.profiles_path.isfile():
        parser.error('Cannot access profiles path: {}'
                     .format(args.profiles_path))

    return args


def main():
    args = parse_args()

    # Load list of profiles from file.
    #
    # If file does not exist or list is empty, the profile list is initialized
    # with the default profile directory path.
    df_profiles = load_profiles_info(args.profiles_path)
    drop_version_errors(df_profiles, missing=False, mismatch=True,
                        inplace=True)

    # Save most recent list of profiles to disk.
    with args.profiles_path.open('w') as output:
        profiles_str = yaml.dump(df_profiles[SAVED_COLUMNS].astype(str)
                                 .to_dict('records'), default_flow_style=False)
        output.write(profiles_str)

    # Look up major version of each profile.
    df_profiles['major_version'] = df_profiles.path.map(profile_major_version)

    if args.default:
        return_code = launch_profile_row(df_profiles.iloc[0])
        if return_code == 0:
            df_profiles.used_timestamp[0] = str(dt.datetime.now())
    else:
        # Display dialog to manage profiles or launch a profile.
        launch_dialog = LaunchDialog(df_profiles)
        launch_dialog.run()
        return_code = launch_dialog.return_code
        df_profiles = launch_dialog.df_profiles

    # Save most recent list of profiles to disk (most recently used first).
    #
    # List can be changed using dialog by:
    #  - Creating a new profile.
    #  - Importing a profile.
    #  - Updating used timestamp by launching a profile.
    df_profiles = df_profiles.astype(str)
    df_profiles.sort_values('used_timestamp', ascending=False, inplace=True)

    with args.profiles_path.open('w') as output:
        profiles_str = yaml.dump(df_profiles[SAVED_COLUMNS]
                                 .to_dict('records'), default_flow_style=False)
        output.write(profiles_str)

    return return_code


if __name__ == '__main__':
    return_code = main()
    raise SystemExit(return_code)
