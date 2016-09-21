import datetime as dt
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

        def on_launch_clicked(row_i):
            def _wrapped(*args):
                launch_callback(row_i)
            return _wrapped

        def on_remove_clicked(row_i):
            def _wrapped(*args):
                remove_callback(row_i)
            return _wrapped

        button_launch_i = gtk.Button('Launch')
        button_remove_i = gtk.Button('Remove')
        button_launch_i.connect('clicked', on_launch_clicked(row_i))
        button_remove_i.connect('clicked', on_remove_clicked(row_i))
        for button_ij, j in zip((button_launch_i, button_remove_i),
                                range(j + 1, j + 3)):
            table.attach(button_ij, left_attach=j, right_attach=j + 1,
                         **row_kwargs)

    scrolled_window = gtk.ScrolledWindow()
    scrolled_window.set_policy(hscrollbar_policy=gtk.POLICY_AUTOMATIC,
                               vscrollbar_policy=gtk.POLICY_AUTOMATIC)
    scrolled_window.add_with_viewport(table)
    frame = gtk.Frame(label='Select profile to launch')
    frame.add(scrolled_window)
    frame.show_all()
    return frame


def launch_profile(profile_path):
    profile_path = ph.path(profile_path)

    config_file = profile_path.joinpath('microdrop.ini')
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
        # No `RELEASE-VERSION` file found in the same directory as the
        # configuration file.
        #
        # Create a `RELEASE-VERSION` file and populate it with the installed
        # MicroDrop package version.
        response = gd.yesno('Unable to determine compatible MicroDrop version '
                            'from profile.\nWas this profile created using '
                            'MicroDrop {}?'.format(installed_major_version()))
        if response == gtk.RESPONSE_NO:
            raise RuntimeError('Not launching MicroDrop since profile was not '
                               'created using MicroDrop {}.'
                               .format(installed_major_version()))
        with release_version_path.open('w') as output:
            output.write(installed_version_str)
        release_version = installed_version
        release_version_str = installed_version_str

    if not (get_major_version(release_version_str) ==
            get_major_version(installed_version_str)):
        # Major version in `RELEASE-VERSION` file and major version of
        # installed MicroDrop package **do not match**.
        #
        # Notify the user and wait for user input to continue.
        raise RuntimeError('Configuration directory major version (%s) does '
                           'not match installed major MicroDrop version (%s)'
                           % (release_version, installed_version))
    else:
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


class LaunchDialog(object):
    def __init__(self, df_profiles):
        self.df_profiles = df_profiles
        self.frame = None
        self.profile_row = None
        self.content_area = None

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
            try:
                return_code = launch_profile(profile_row_i.path)
            except Exception, exception:
                gd.error(str(exception))
                self.frame = None
                self.run()
            else:
                if return_code == 0:
                    profile_row_i.used_timestamp = str(dt.datetime.now())

        def on_remove_clicked(profile_row_i):
            dialog = gtk.MessageDialog(type=gtk.MESSAGE_QUESTION)
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
        self.content_area.pack_start(self.frame, expand=True, fill=True)
        self.content_area.reorder_child(self.frame, 0)

    def run(self):
        self.dialog = gtk.Dialog()
        self.dialog.set_title('MicroDrop Profile Manager')
        self.dialog.set_size_request(480, 320)
        self.content_area = self.dialog.get_content_area()

        buttons_area = gtk.HBox()
        buttons_box = gtk.HButtonBox()
        button_import = gtk.Button('Import...')
        button_create = gtk.Button('Create...')
        button_import.connect('clicked', lambda *args:
                              self.import_profile(self.df_profiles.path
                                                  .iloc[0]))
        button_create.connect('clicked', lambda *args:
                              self.create_profile(self.df_profiles.path
                                                  .iloc[0]))
        for button_i in (button_import, button_create):
            buttons_box.pack_end(button_i, expand=False, fill=False)
        buttons_area.pack_end(buttons_box, expand=False, fill=False)
        buttons_area.show_all()
        self.content_area.pack_end(buttons_area, expand=False, fill=False)

        self.update_profiles_frame()
        self.dialog.run()

        return self.profile_row


def load_profiles_info(profiles_path):
    profiles_path = ph.path(profiles_path)

    profiles_path.parent.makedirs_p()
    if profiles_path.exists():
        with profiles_path.open('r') as input_:
            profiles_str = input_.read()
            profiles = yaml.load(profiles_str)
    else:
        profiles = []

    default_profile_path = mpm.bin.get_plugins_directory().parent

    if not profiles and default_profile_path.isdir():
        # No profiles list found or empty profiles list.
        #
        # Use default profile path.
        profiles = [{'path': str(default_profile_path),
                     'used_timestamp': str(dt.datetime.now())}]

    df_profiles = pd.DataFrame(profiles, columns=SAVED_COLUMNS)
    df_profiles.sort_values('used_timestamp', ascending=False, inplace=True)
    df_profiles.drop_duplicates(subset=['path'], inplace=True)
    return df_profiles


def profile_major_version(profile):
    release_version_path = ph.path(profile).joinpath('RELEASE-VERSION')
    if release_version_path.isfile():
        return get_major_version(release_version_path.lines()[0])


def installed_major_version():
    installed_version_str = pkg_resources.get_distribution('microdrop').version
    return get_major_version(installed_version_str)


def main():
    major_version = get_major_version(pkg_resources
                                      .get_distribution('microdrop').version)
    # Look up MicroDrop application directories based on major version.
    microdrop_env_dirs = mdl.dirs.AppDirs('MicroDrop', version=major_version)
    # Construct path to list of profiles based on user configuration directory.
    profiles_path = microdrop_env_dirs.user_config_dir.joinpath('profiles.yml')

    # Load list of profiles from file.
    #
    # If file does not exist or list is empty, the profile list is initialized
    # with the default profile directory path.
    df_profiles = load_profiles_info(profiles_path)

    # Save most recent list of profiles to disk.
    with profiles_path.open('w') as output:
        profiles_str = yaml.dump(df_profiles[SAVED_COLUMNS].astype(str)
                                 .to_dict('records'), default_flow_style=False)
        output.write(profiles_str)

    # Look up major version of each profile.
    df_profiles['major_version'] = df_profiles.path.map(profile_major_version)

    # Display dialog to manage profiles or launch a profile.
    launch_dialog = LaunchDialog(df_profiles)
    launch_dialog.run()

    # Save most recent list of profiles to disk (most recently used first).
    #
    # List can be changed using dialog by:
    #  - Creating a new profile.
    #  - Importing a profile.
    #  - Updating used timestamp by launching a profile.
    df_profiles = launch_dialog.df_profiles.astype(str)
    df_profiles.sort_values('used_timestamp', ascending=False, inplace=True)

    with profiles_path.open('w') as output:
        profiles_str = yaml.dump(df_profiles[SAVED_COLUMNS]
                                 .to_dict('records'), default_flow_style=False)
        output.write(profiles_str)


if __name__ == '__main__':
    main()
