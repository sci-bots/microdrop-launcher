import os

from win32com.shell import shell, shellcon
import pkg_resources
import pythoncom


def create_microdrop_shortcut(target_path, name, description=None,
                              overwrite=False, icon=None):
    '''
    Create desktop shortcut with MicroDrop version.

    Args
    ----

        batch_path (str) : Path to MicroDrop launch batch file.
    '''
    # Look up MicroDrop major version.
    microdrop_dist = pkg_resources.get_distribution('microdrop')
    major_version = '.'.join(microdrop_dist.version.split('.')[:2])

    # Surround target path in quotes if it contains spaces.
    if ' ' in target_path and not (target_path.startswith('"') and
                                   target_path.endswith('"')):
        target_path = '"{}"'.format(target_path)

    # Strip extension from name.
    if name.endswith('.lnk'):
        name = name[:-len('.lnk')]

    shortcut_name = name.format(target_path=target_path,
                                major_version=major_version)

    # Create shortcut instance.
    # See [here][1] for more information.
    #
    # [1]: http://docs.activestate.com/activepython/2.4/pywin32/pythoncom__CoCreateInstance_meth.html
    shortcut = pythoncom.CoCreateInstance(shell.CLSID_ShellLink, None,
                                          pythoncom.CLSCTX_INPROC_SERVER,
                                          shell.IID_IShellLink)

    # Set shortcut attributes.
    shortcut.SetPath(str(target_path))
    if description:
        shortcut.SetDescription(description.format(target_path=target_path,
                                                   major_version=major_version))
    else:
        shortcut.SetDescription(shortcut_name)

    if icon is None:
        icon_path = pkg_resources.resource_filename('microdrop', 'microdrop.ico')
    else:
        icon_path = icon

    if not (icon_path == False):
        shortcut.SetIconLocation(icon_path, 0)

    # Get `Desktop` path.
    desktop_path = shell.SHGetFolderPath(0, shellcon.CSIDL_DESKTOP, 0, 0)
    shortcut_filepath = os.path.join(desktop_path, shortcut_name + '.lnk')

    # Save shortcut to `Desktop`.
    persist_file = shortcut.QueryInterface(pythoncom.IID_IPersistFile)

    if not overwrite:
        # Get non-existing filename by appending ` (%d)` to the end of the shortcut
        # name, increasing the count until a unique name is found.
        i = 0
        while True:
            shortcut_filepath = os.path.join(desktop_path, shortcut_name +
                                             ('' if i == 0 else ' ({})'.format(i))
                                             + '.lnk')
            if not os.path.isfile(shortcut_filepath):
                break
            i += 1
    persist_file.Save(shortcut_filepath, 0)
    return shortcut_filepath
