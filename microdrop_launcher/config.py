from datetime import datetime
import copy
import os
import pkg_resources
import sys
import tempfile
import types

from configobj import ConfigObj
import jinja2
import path_helpers as ph


# Batch file template.
launcher_template = '''
@echo off
REM Change into [parent directory of batch file][1].
REM
REM [1]: http://stackoverflow.com/questions/16623780/how-to-get-windows-batchs-parent-folder
cd "%~dp0"
REM Launch Microdrop
"{{ py_exe }}" -m microdrop.microdrop -c "%~dp0microdrop.ini"
'''

# Microdrop configuration file template.
config_template = '''
data_dir = .
[plugins]
        # directory containing microdrop plugins
        directory = plugins
[microdrop.gui.experiment_log_controller]
        notebook_directory = notebooks
[microdrop.gui.dmf_device_controller]
        device_directory = devices
'''


def directory_multi_keys(root, parent_keys=None):
    '''
    Collect all items in nested key-value mapping that satisfy one of the
    following:

     - End with ``"_dir"``.
     - Contain ``"directory"``.

    Parameters
    ----------
    root : dict-like
        Nested key-value mapping.
    parent_keys : list
        Keys of parents of ``root`` in hierarchy.

    Returns
    -------
    list
        List of tuples.

        Within each tuple, first element is a tuple of keys (one key per
        hierarchy level) and the second element is the corresponding item
        value.
    '''
    if parent_keys is None:
        parent_keys = []
    multi_keys = []
    for k, v in root.iteritems():
        if isinstance(v, dict):
            # Item is a nested dictionary.
            multi_keys_i = directory_multi_keys(v, parent_keys=
                                                parent_keys + [k])
            multi_keys.extend(multi_keys_i)
        elif isinstance(v, types.StringTypes) and any([k.endswith('_dir'),
                                                       'directory' in k]):
            # Item is a directory path
            multi_keys.append((tuple(parent_keys + [k]), ph.path(v)))
    return multi_keys


def config_relative_paths_to(config, root):
    '''
    Parameters
    ----------
    config : configobj.ConfigObj
        Configuration.
    root : str
        Root directory to resolve configuration paths against.

    Returns
    -------
    configobj.ConfigObj
        Copy of input configuration with descendent paths of ``root`` directory
        replaced with *relative* paths (with respect to ``root``).
    '''
    # Wrap `root` in `path` wrapper for convenience methods.
    root = ph.path(root)
    # Copy input config, since we are modifying it.
    config_i = copy.deepcopy(config)

    # Find config entries corresponding to directory paths.
    real_config_root = root.realpath() + os.path.sep
    dir_multi_keys = directory_multi_keys(config_i)

    # Replace descendent paths of `root` directory in config with *relative*
    # paths (with respect to `root`).
    for multi_key_i, dir_i in dir_multi_keys:
        real_dir_i = root.joinpath(dir_i).realpath()

        if os.path.commonprefix([real_dir_i + os.path.sep,
                                 real_config_root]) == real_config_root:
            # Directory is a descendent of configuration directory.

            # Replace directory reference in configuration object with
            # *relative* path to configuration directory.
            rel_path_i = root.relpathto(real_dir_i)

            config_parent_i = config_i
            for k in multi_key_i[:-1]:
                config_parent_i = config_parent_i[k]
            config_parent_i[multi_key_i[-1]] = str(rel_path_i)
    return config_i


def create_config_directory_with_paths(output_directory, paths_ini_path=None,
                                       overwrite=False):
    '''
    Create new configuration directory, where configuration file contains
    relative paths with respect to new directory.

    If :data:`paths_ini_path` is specified, replace descendent directory paths
    in :data:`paths_ini_path` with relative paths with respect to output
    directory.

    Parameters
    ----------
    output_dir : str
        Path to output directory.
    paths_ini_path : str
        Path to existing ``microdrop.ini`` file to extract directory paths
        from.
    overwrite : bool
        If ``False``, do not write to output directory if it already exists and
        is not empty.

    Returns
    -------
    path_helpers.path
        Path to launcher script (i.e., ``microdrop.bat``).
    '''
    paths_ini_path = ph.path(paths_ini_path)
    if paths_ini_path.isfile():
        # Load existing configuration file.
        paths_config = ConfigObj(paths_ini_path)
        data_dir = paths_config.get('data_dir', '.')
        paths_config_directory = (paths_ini_path.parent.joinpath(data_dir)
                                  .realpath())

        # Get configuration with descendent paths of default configuration
        # directory replaced with relative paths.
        output_config = config_relative_paths_to(config=paths_config,
                                                 root=paths_config_directory)
    else:
        output_config = None

    # Create new directory (at original path).
    launcher_path = create_config_directory(output_directory,
                                            overwrite=overwrite)

    if output_config is not None:
        output_dir_items = directory_multi_keys(output_config)

        # Open default configuration file in new directory.
        output_ini = output_directory.joinpath('microdrop.ini')
        output_config = ConfigObj(output_ini)

        # Replace directory paths in configuration with directories from
        # original configuration file.
        for multi_key_i, directory_i in output_dir_items:
            config_parent_i = output_config
            for k in multi_key_i[:-1]:
                config_parent_i = config_parent_i[k]
            config_parent_i[multi_key_i[-1]] = str(directory_i)
        # Save updated configuration file.
        output_config.write()
    return launcher_path


def create_config_directory(output_dir, overwrite=False):
    '''
    Initialize output directory with minimal Microdrop configuration.

    The created configuration causes Microdrop to store plugins and device
    files within the configuration directory.  A batch file `microdrop.bat` is
    also created in the directory to launch Microdrop using the configuration.
    Note that the ``microdrop.bat`` can be launched within any working directory.

    Parameters
    ----------
    output_dir : str
        Path to output directory.
    overwrite : bool
        If ``False``, do not write to output directory if it already exists and
        is not empty.

    Returns
    -------
    path_helpers.path
        Path to launcher script (i.e., ``microdrop.bat``).
    '''
    output_dir = ph.path(output_dir)

    if not output_dir.isdir():
        output_dir.makedirs_p()
    elif not overwrite and list(output_dir.files()):
        raise IOError('Output directory exists and is not empty.')

    config_path = output_dir.joinpath('microdrop.ini')
    with config_path.open('w') as output:
        template = jinja2.Template(config_template)
        config_str = template.render(output_dir=output_dir.name)
        output.write(config_str)

    py_exe = ph.path(sys.executable).abspath()
    launcher_path = output_dir.joinpath('microdrop.bat').abspath()
    with launcher_path.open('w') as output:
        template = jinja2.Template(launcher_template)
        launcher_str = template.render(working_dir=output_dir.abspath(),
                                       py_exe=py_exe,
                                       config_path=config_path.abspath())
        output.write(launcher_str)
    release_version_path = output_dir.joinpath('RELEASE-VERSION')
    with release_version_path.open('w') as output:
        try:
            microdrop_dist = pkg_resources.get_distribution('microdrop')
        except Exception:
            print >> sys.stderr, ('[warning] could not find microdrop '
                                  'distribution.')
        else:
            output.write(microdrop_dist.version)

    return launcher_path


def replace_config_directory(config_directory, backup=True):
    '''
    Replace existing Microdrop configuration directory with newly initialized
    configuration.

    Directory paths from existing configuration will be copied to new
    configuration.

    Descendent paths of existing configuration directory will be replaced by
    corresponding relative paths in new configuration (with respect to new
    directory).

    Parameters
    ----------
    config_directory : str
        Path to existing Microdrop configuration directory.
    backup : True
        If ``True``, existing directory will be renamed with timestamp suffix.
        Otherwise, the existing directory will be **deleted**.

    Returns
    -------
    None or path_helpers.path
        If :data:`backup` is ``True``, the backed up directory path is
        returned.

        Otherwise, ``None`` is returned.
    '''
    config_directory = ph.path(config_directory)
    assert(config_directory.isdir())
    try:
        new_config_directory = ph.path(tempfile
                                       .mkdtemp(prefix='microdrop_config-'))

        config_ini = config_directory.joinpath('microdrop.ini')
        launcher_path = \
            create_config_directory_with_paths(new_config_directory,
                                               paths_ini_path=config_ini
                                               if config_ini.isfile()
                                               else None)

        if backup:
            # Rename existing directory with appended timestamp postfix.
            backup_name = datetime.now().strftime('{}.%Y.%m.%d-%Hh%Mm%S'
                                                  .format(config_directory.name))
            backup_directory = config_directory.parent.joinpath(backup_name)
            config_directory.rename(backup_directory)
        else:
            # **Delete original configuration directory.**
            config_directory.rmtree()

        # Rename new configuration directory with original name.
        launcher_path.parent.rename(config_directory)
    except:
        # Clean up temporary new directory.
        if new_config_directory.isdir():
            new_config_directory.rmtree()
        raise

    if backup:
        return backup_directory
