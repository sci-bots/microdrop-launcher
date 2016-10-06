import os
import pkg_resources
import re
import subprocess as sp
import sys

import path_helpers as ph


def conda_prefix():
    '''
    Returns
    -------
    path_helpers.path
        Path to Conda environment prefix.

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


def conda_upgrade(package_name):
    '''
    Upgrade Conda package.

    Parameters
    ----------
    package_name : str
        Package name.

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

    See also
    --------
    :func:`pip_helpers.upgrade`
    '''
    result = {'package': package_name,
              'original_version': None,
              'new_version': None,
              'installed_dependencies': []}

    conda_exe = conda_prefix().joinpath('Scripts', 'conda.exe')
    if not conda_exe.isfile():
        # Could not locate `conda` executable.
        return result

    output = sp.check_output([conda_exe, 'list', package_name])
    output_last_line = output.strip().splitlines()[-1]

    result = {'package': package_name,
              'original_version': None,
              'new_version': None,
              'installed_dependencies': []}

    if not output_last_line.startswith('#'):
        # Extract installed package version.
        #
        # If package is installed, output will be of the form:
        #
        #     # packages in environment at C:\Users\Christian\MicroDrop:
        #     #
        #     foo        0.1.0      0      <channel>
        result['original_version'] = re.split(r'\s+', output_last_line)[1]
    else:
        # Package is not installed.
        raise pkg_resources.DistributionNotFound(package_name, [])

    # Running in a Conda environment.
    process = sp.Popen([conda_exe, 'install', '-y',
                        package_name], stdout=sp.PIPE,
                        stderr=sp.STDOUT)
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
