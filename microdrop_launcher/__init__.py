import json
import os
import pkg_resources
import re
import subprocess as sp
import sys

import conda_helpers as ch
import path_helpers as ph


f_major_version = lambda v: int(v.split('.')[0])


def conda_version_info(package_name):
    '''
    .. versionadded:: 0.2.post5

    .. versionchanged:: 0.3.post2
        Add support for running in Conda environments.

    .. versionchanged:: 0.7.3
        Use :func:`conda_helpers.conda_exec` to search for available MicroDrop
        Conda packages.

        Add ``sci-bots`` Anaconda channel to Conda package search.

    .. versionchanged:: 0.7.8
        Fall back to using ``conda list`` to search for the installed version
        of MicroDrop if the version cannot be determined using ``conda
        search``.

    Parameters
    ----------
    package_name : str
        Conda package name.

    Returns
    -------
    dict
        Version information:

         - ``latest``: Latest available version.
         - ``installed``: Conda package description dictionary for installed
           version (`None` if not installed).

    Raises
    ------
    IOError
        If Conda executable not found.
    subprocess.CalledProcessError
        If `conda search` command fails.

        This happens, for example, if no internet connection is available.
    '''
    # Use `-f` flag to search for package, but *no other packages that have
    # `<package_name>` in the name).
    json_output = ch.conda_exec('search', '-c', 'sci-bots', '-c',
                                'wheeler-microfluidics', '-f', 'microdrop',
                                '--json', verbose=False)
    versions = json.loads(json_output)['microdrop']
    installed_versions = [v_i for v_i in versions if v_i['installed']]
    installed_version = installed_versions[0] if installed_versions else None

    if installed_version is None:
        # If not able to find installed version from `microdrop` Conda package
        # search, use `conda list ...` to try determine the installed version of
        # MicroDrop.
        try:
            installed_version = ch.package_version('microdrop', verbose=False)
        except NameError:
            # Installed MicroDrop Conda package not found (perhaps this is a
            # development environment?)
            pass

    return {'installed': installed_version, 'versions': versions}
