import json
import os
import pkg_resources
import re
import subprocess as sp
import sys

import conda_helpers as ch
import path_helpers as ph


f_major_version = lambda v: int(v.split('.')[0])


def conda_activate_command():
    '''
    .. versionadded:: 0.3.post2

    Returns
    -------
    list
        Command list to activate Conda environment.

        Can be prepended to a command list to run the command in the activated
        Conda environment corresponding to the running Python executable.
    '''
    prefix = conda_prefix()
    return ['call', r'{prefix}\Scripts\activate.bat' .format(prefix=prefix),
            prefix]


def conda_root():
    '''
    .. versionadded:: 0.3.post2

    Returns
    -------
    path_helpers.path
        Path to Conda **root** environment.
    '''
    return ph.path(sp.check_output(conda_activate_command() +
                                   ['&', 'conda', 'info', '--root'],
                                   shell=True).strip())


def conda_prefix():
    '''
    Returns
    -------
    path_helpers.path
        Path to Conda environment prefix corresponding to running Python
        executable.

        Return ``None`` if not running in a Conda environment.
    '''
    if any(['continuum analytics, inc.' in sys.version.lower(),
            'conda' in sys.version.lower()]):
        # Assume running under Conda.
        if 'CONDA_PREFIX' in os.environ:
            conda_prefix = ph.path(os.environ['CONDA_PREFIX'])
        else:
            # Infer Conda prefix as parent directory of Python executable.
            conda_prefix = ph.path(sys.executable).parent.realpath()
    else:
        # Assume running under Conda.
        conda_prefix = None
    return conda_prefix


def conda_executable():
    '''
    .. versionadded:: 0.2.post5

    Returns
    -------
    path_helpers.path
        Path to Conda executable.
    '''
    for conda_filename_i in ('conda.exe', 'conda.bat'):
        conda_exe = conda_prefix().joinpath('Scripts', conda_filename_i)
        if conda_exe.isfile():
            return conda_exe
    else:
        raise IOError('Could not locate `conda` executable.')


def conda_upgrade(package_name, match_major_version=False):
    '''
    Upgrade Conda package.

    .. versionchanged:: 0.2.post5
        Use `func:conda_version_info` to query Conda package version info.

    .. versionchanged:: 0.2.post6
        Add optional :data:`match_major_version` parameter.

    .. versionchanged:: 0.3.post2
        Add support for running in Conda environments.

    .. versionchanged:: 0.3.post3
        Explictly set `wheeler-microfluidics` channel for install operations.

    Parameters
    ----------
    package_name : str
        Package name.
    match_major_version : bool,optional
        Only upgrade to versions within the same major version.

    Returns
    -------
    dict
        Dictionary containing:
         - :data:`original_version`: Package version before upgrade.
         - :data:`new_version`: Package version after upgrade (`None` if
           package was not upgraded).
         - :data:`installed_dependencies`: List of dependencies installed
           during package upgrade.  Each dependency is represented as a
           dictionary of the form ``{'package': ..., 'version': ...}``.

    Raises
    ------
    pkg_resources.DistributionNotFound
        If package not installed.
    IOError
        If Conda executable not found in Conda environment.
    subprocess.CalledProcessError
        If `conda search` command fails (in Conda environment).

        This happens, for example, if no internet connection is available.

    See also
    --------
    :func:`pip_helpers.upgrade`
    '''
    result = {'package': package_name,
              'original_version': None,
              'new_version': None,
              'installed_dependencies': []}

    try:
        version_info = conda_version_info(package_name)
    except IOError:
        # Could not locate `conda` executable.
        return result

    result = {'package': package_name,
              'original_version': version_info['installed'],
              'new_version': None,
              'installed_dependencies': []}

    if result['original_version'] is None:
        # Package is not installed.
        raise pkg_resources.DistributionNotFound(package_name, [])

    if match_major_version:
        installed_major_version = f_major_version(version_info['installed'])
        latest_version = filter(lambda v: f_major_version(v) ==
                                installed_major_version,
                                version_info['versions'])[-1]
    else:
        latest_version = version_info['versions'][-1]

    if result['original_version'] == latest_version:
        # Latest version already installed.
        return result

    # Running in a Conda environment.
    process = sp.Popen(conda_activate_command() +
                       ['&', 'conda', 'install', '-c', 'wheeler-microfluidics',
                        '-y', '{}=={}'.format(package_name, latest_version)],
                       shell=True, stdout=sp.PIPE, stderr=sp.STDOUT)
    lines = []
    ostream = sys.stdout

    # Iterate until end of `stdout` stream (i.e., `b''`).
    for stdout_i in iter(process.stdout.readline, b''):
        ostream.write('.')
        lines.append(stdout_i)
    process.wait()
    print >> ostream, ''
    output = ''.join(lines)
    if process.returncode != 0:
        raise RuntimeError(output)

    if '# All requested packages already installed.' in output:
        pass
    elif 'The following NEW packages will be INSTALLED' in output:
        match = re.search(r'The following NEW packages will be INSTALLED:\s+'
                          r'(?P<packages>.*)\s+Linking packages', output,
                          re.MULTILINE | re.DOTALL)
        cre_package = re.compile(r'\s*(?P<package>\S+):\s+'
                                 r'(?P<version>\S+)-[^-]+\s+')
        packages_str = match.group('packages')
        packages = [match_i.groupdict()
                    for match_i in cre_package.finditer(packages_str)]
        for package_i in packages:
            if package_i['package'] == package_name:
                result['new_version'] = package_i['version']
        installed_dependencies = filter(lambda p: p['package'] != package_name,
                                        packages)
        result['installed_dependencies'] = installed_dependencies
    return result


def conda_version_info(package_name):
    '''
    .. versionadded:: 0.2.post5

    .. versionchanged:: 0.3.post2
        Add support for running in Conda environments.

    .. versionchanged:: 0.7.3
        Use :func:`conda_helpers.conda_exec` to search for available MicroDrop
        Conda packages.

        Add ``sci-bots`` Anaconda channel to Conda package search.

    Parameters
    ----------
    package_name : str
        Conda package name.

    Returns
    -------
    dict
        Version information:

         - ``latest``: Latest available version.
         - ``installed``: Installed version (`None` if not installed).

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
    json_output = ch.conda_exec('search', '-c', 'wheeler-microfluidics', '-f',
                                'microdrop', '--json')
    versions = json.loads(json_output)['microdrop']
    installed_versions = [v_i for v_i in versions if v_i['installed']]
    installed_version = installed_versions[0] if installed_versions else None
    return {'installed': installed_version, 'versions': versions}
