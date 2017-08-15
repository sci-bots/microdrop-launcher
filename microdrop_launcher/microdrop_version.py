import logging
import pkg_resources
import subprocess as sp

import yaml

from . import conda_version_info, f_major_version
from .dirs import AppDirs

logger = logging.getLogger(__name__)


def cache_microdrop_version():
    '''
    .. versionadded:: 0.2.post7

    .. versionchanged:: 0.7.3
        Fix call to :func:`f_major_version`.

     1. Look up latest version of MicroDrop Conda package.
     2. If latest version not cached in
        `<microdrop_env_dirs.user_config_dir>/latest-version.yml`,
        (over)write file with version in `yaml` format, i.e.:

            version: <version specifier>

    See [here].

    [1]: http://knsv.github.io/mermaid/live_editor/#/view/Z3JhcGggTFIKICAgTGF1bmNoKExhdW5jaCk7CiAgIENoZWNrTWljcm9Ecm9wPkNoZWNrIGZvciBNaWNyb0Ryb3AgdXBkYXRlc107CiAgIE1pY3JvRHJvcFVwVG9EYXRle1VwIHRvIGRhdGU_fTsKICAgQ2hlY2tNaWNyb0Ryb3BMYXVuY2hlcj5DaGVjayBmb3IgTWljcm9Ecm9wIExhdW5jaGVyIHVwZGF0ZXNdOwogICBNaWNyb0Ryb3BMYXVuY2hlclVwVG9EYXRle1VwIHRvIGRhdGU_fTsKICAgVXBncmFkZU1pY3JvRHJvcExhdW5jaGVyPlVwZ3JhZGUgTWljcm9Ecm9wIExhdW5jaGVyXTsKICAgU2hvd01pY3JvRHJvcExhdW5jaGVyKFNob3cgTWljcm9Ecm9wIExhdW5jaGVyKTsKICAgTGF1bmNoUHJvZmlsZT5MYXVuY2ggcHJvZmlsZV07CiAgIFNob3dNaWNyb0Ryb3AoTWljcm9Ecm9wKTsKICAgT3BlblByb2ZpbGU-T3BlbiBwcm9maWxlIGRpcmVjdG9yeV07CiAgIFByb2ZpbGVQcm9tcHQ-T3BlbiBwcm9maWxlIGNvbW1hbmQgcHJvbXB0XTsKICAgUmVtb3ZlUHJvZmlsZT5SZW1vdmUgcHJvZmlsZV07CiAgIFJlbW92ZVByb2ZpbGVDb25maXJte0RlbGV0ZSBkYXRhP307CiAgIFJlbW92ZVByb2ZpbGVGcm9tTGlzdD5SZW1vdmUgcHJvZmlsZSBmcm9tIGxpc3RdOwogICBEZWxldGVQcm9maWxlRGF0YT5EZWxldGUgcHJvZmlsZSBkYXRhXTsKICAgQ2hlY2tMYXRlc3RWZXJzaW9uQ2FjaGVke0xhdGVzdCB2ZXJzaW9uIGNhY2hlZD99OwogICBDYWNoZUxhdGVzdE1pY3JvRHJvcFZlcnNpb24-IlNhdmUgbGF0ZXN0IE1pY3JvRHJvcCB2ZXJzaW9uIHRvIGZpbGU6PC9icj48Y29kZT5ldGNcTWljcm9Ecm9wXDIuMFxBVkFJTEFCTEUtVkVSU0lPTlMuY3N2PC9jb2RlPiJdOwogICBDaGVja01pY3JvRHJvcFZlcnNpb257Ikluc3RhbGxlZCB2ZXJzaW9uPC9icj5tYXRjaGVzIGxhdGVzdCBpbjo8L2JyPjxjb2RlPkFWQUlMQUJMRS1WRVJTSU9OUy5jc3Y8L2NvZGU-PyJ9OwogICBJZ25vcmVWZXJzaW9ueyJWZXJzaW9uIGlnbm9yZWQgaW46PC9icj48Y29kZT5BVkFJTEFCTEUtVkVSU0lPTlMuY3N2PC9jb2RlPj8ifTsKICAgUHJvbXB0Rm9yVXBncmFkZT5Qcm9tcHQgdXNlciB0byB1cGdyYWRlXTsKICAgVXBncmFkZUNvbmZpcm17VXBncmFkZSBNaWNyb0Ryb3A_fTsKICAgVXBncmFkZU1pY3JvRHJvcD5VcGdyYWRlIE1pY3JvRHJvcF07CiAgIFNhdmVJZ25vcmU-IlNhdmUgaWdub3JlIHByZWZlcmVuY2UgaW46PC9icj48Y29kZT5BVkFJTEFCTEUtVkVSU0lPTlMuY3N2PC9jb2RlPiJdOwogICBDbG9zZU1pY3JvRHJvcD5DbG9zZSBNaWNyb0Ryb3BdOwogICBDbG9zZU1pY3JvRHJvcExhdW5jaGVyPkNsb3NlIE1pY3JvRHJvcCBMYXVuY2hlcl07CiAgIFdhaXRGb3JVcGRhdGVUaHJlYWQoV2FpdCBmb3IgdXBkYXRlIHRocmVhZCk7CgogICBMYXVuY2ggLS0-IENoZWNrTWljcm9Ecm9wOwogICBMYXVuY2ggLS0-IFNob3dNaWNyb0Ryb3BMYXVuY2hlcjsKCiAgIENoZWNrTWljcm9Ecm9wTGF1bmNoZXIgLS0-IE1pY3JvRHJvcExhdW5jaGVyVXBUb0RhdGU7CiAgIENoZWNrTWljcm9Ecm9wIC0tPiBNaWNyb0Ryb3BVcFRvRGF0ZTsKICAgTWljcm9Ecm9wTGF1bmNoZXJVcFRvRGF0ZSAtLT58Tm98VXBncmFkZU1pY3JvRHJvcExhdW5jaGVyOwogICBVcGdyYWRlTWljcm9Ecm9wTGF1bmNoZXIgLS0-IFdhaXRGb3JVcGRhdGVUaHJlYWQ7CgogICBDaGVja01pY3JvRHJvcFZlcnNpb24gLS0-fE5vfElnbm9yZVZlcnNpb247CiAgIENoZWNrTWljcm9Ecm9wVmVyc2lvbiAtLT58WWVzfFNob3dNaWNyb0Ryb3A7CiAgIElnbm9yZVZlcnNpb24gLS0-fFllc3xTaG93TWljcm9Ecm9wOwogICBJZ25vcmVWZXJzaW9uIC0tPnxOb3xQcm9tcHRGb3JVcGdyYWRlOwogICBQcm9tcHRGb3JVcGdyYWRlIC0tPiBVcGdyYWRlQ29uZmlybTsKCiAgIFVwZ3JhZGVDb25maXJtIC0tPnxOb3xTaG93TWljcm9Ecm9wOwogICBVcGdyYWRlQ29uZmlybSAtLT58WWVzfFVwZ3JhZGVNaWNyb0Ryb3A7CiAgIFVwZ3JhZGVDb25maXJtIC0tPnxJZ25vcmV8U2F2ZUlnbm9yZTsKICAgU2F2ZUlnbm9yZSAtLT4gU2hvd01pY3JvRHJvcDsKCiAgIFVwZ3JhZGVNaWNyb0Ryb3AgLS0-IFNob3dNaWNyb0Ryb3A7CiAgIENsb3NlTWljcm9Ecm9wIC0tPiBXYWl0Rm9yVXBkYXRlVGhyZWFkOwogICBXYWl0Rm9yVXBkYXRlVGhyZWFkIC0tPnxOb3QgcmVhZHl8V2FpdEZvclVwZGF0ZVRocmVhZDsKICAgV2FpdEZvclVwZGF0ZVRocmVhZCAtLT58UmVhZHl8Q2xvc2VNaWNyb0Ryb3BMYXVuY2hlcjsKCiAgIExhdW5jaFByb2ZpbGUgLS0-IENoZWNrTWljcm9Ecm9wVmVyc2lvbjsKICAgU2hvd01pY3JvRHJvcCAtLT4gQ2xvc2VNaWNyb0Ryb3A7CgogICBTaG93TWljcm9Ecm9wTGF1bmNoZXIgLS0-IExhdW5jaFByb2ZpbGU7CiAgIFNob3dNaWNyb0Ryb3BMYXVuY2hlciAtLT4gT3BlblByb2ZpbGU7ICAgCiAgIFNob3dNaWNyb0Ryb3BMYXVuY2hlciAtLT4gUHJvZmlsZVByb21wdDsKICAgU2hvd01pY3JvRHJvcExhdW5jaGVyIC0tPiBSZW1vdmVQcm9maWxlOwogICBPcGVuUHJvZmlsZSAtLT4gU2hvd01pY3JvRHJvcExhdW5jaGVyOwogICBQcm9maWxlUHJvbXB0IC0tPiBTaG93TWljcm9Ecm9wTGF1bmNoZXI7CiAgIFJlbW92ZVByb2ZpbGUgLS0-IFJlbW92ZVByb2ZpbGVDb25maXJtOwogICBSZW1vdmVQcm9maWxlQ29uZmlybSAtLT58Q2FuY2VsfFNob3dNaWNyb0Ryb3BMYXVuY2hlcjsKICAgUmVtb3ZlUHJvZmlsZUNvbmZpcm0gLS0-fFllc3xEZWxldGVQcm9maWxlRGF0YTsKICAgRGVsZXRlUHJvZmlsZURhdGEgLS0-IFJlbW92ZVByb2ZpbGVGcm9tTGlzdDsKICAgUmVtb3ZlUHJvZmlsZUNvbmZpcm0gLS0-fE5vfFJlbW92ZVByb2ZpbGVGcm9tTGlzdDsKICAgUmVtb3ZlUHJvZmlsZUZyb21MaXN0IC0tPiBTaG93TWljcm9Ecm9wTGF1bmNoZXI7CgogICBTaG93TWljcm9Ecm9wTGF1bmNoZXIgLS0-IENsb3NlTWljcm9Ecm9wTGF1bmNoZXI7CgogICBNaWNyb0Ryb3BVcFRvRGF0ZSAtLT58WWVzfENoZWNrTWljcm9Ecm9wTGF1bmNoZXI7CiAgIE1pY3JvRHJvcFVwVG9EYXRlIC0tPnxOb3xDaGVja0xhdGVzdFZlcnNpb25DYWNoZWQ7CiAgIENoZWNrTGF0ZXN0VmVyc2lvbkNhY2hlZCAtLT58Tm98Q2FjaGVMYXRlc3RNaWNyb0Ryb3BWZXJzaW9uOwogICBDYWNoZUxhdGVzdE1pY3JvRHJvcFZlcnNpb24gLS0-IENoZWNrTWljcm9Ecm9wTGF1bmNoZXI7CiAgIENoZWNrTGF0ZXN0VmVyc2lvbkNhY2hlZCAtLT58WWVzfENoZWNrTWljcm9Ecm9wTGF1bmNoZXI7
    '''
    try:
        # Try to look up available versions of MicroDrop from Conda channels
        # and which version is installed.
        version_info = conda_version_info('microdrop')
    except IOError:
        # Conda executable not found.
        return
    except sp.CalledProcessError:
        # `conda search` command failed, e.g., no internet connection
        # is available.
        return
    else:
        installed_info = version_info['installed']
        if not installed_info:
            # No `microdrop` Conda package found.
            logger.debug('Could not find installed `microdrop` Conda package.')
            # XXX This also happens if `microdrop` is installed using `conda
            # develop`.
            return
        installed_major_version = f_major_version(installed_info['version'])
        # Find latest version of MicroDrop with the same **major version
        # number** as the installed version.
        latest_info = filter(lambda v: f_major_version(v['version']) ==
                             installed_major_version,
                             version_info['versions'])[-1]

        # Load cached version information (or empty dictionary if no cached
        # info is available).
        cached_path, cached_info = load_cached_version()

        if 'version' in latest_info:
            # Write latest version to file.
            latest_version = latest_info['version']
            if (pkg_resources.parse_version(installed_info['version']) <
                pkg_resources.parse_version(latest_version)):
                # A new version of MicroDrop is available.
                logger.info('new version available: MicroDrop v%s (installed '
                            'version: v%s)', latest_version,
                            installed_info['version'])
            elif (pkg_resources.parse_version(installed_info['version']) >
                  pkg_resources.parse_version(latest_version)):
                # Installed version of MicroDrop is newer than all available
                # versions on Conda channels.
                logger.info('Installed version of MicroDrop (v%s) is newer '
                            'than latest version on Conda channels (v%s)',
                            installed_info['version'], latest_version)
            else:
                # Latest available version of MicroDrop is installed.
                logger.info('The latest version of MicroDrop (v%s) is '
                            'installed.', installed_info['version'])

            if (latest_info['version'] != cached_info.get('version')):
                try:
                    with cached_path.open('w') as output:
                        cached_info = {'version': latest_version}
                        yaml.dump(cached_info, stream=output)
                    logger.debug('wrote version info for MicroDrop v%s to %s',
                                 latest_version, cached_path)
                except:
                    logger.error('Error caching latest version.',
                                 exc_info=True)


def load_cached_version():
    '''
    .. versionadded:: 0.2.post9

    Returns
    -------
    (cached_path, cached_info) : (str, dict)
        Where:
         - :data:`cached_path` is the path to the file containing cached
           MicroDrop version info.
         - :data:`cached_info` is a dictionary that MAY contain a string
           version specifier with the key ``version``, and MAY also contain a
           boolean value with the key ``ignore``.  If ``ignore`` is set to
           ``True``, user should not be prompted to upgrade to the version.
    '''
    # `pkg_resources.DistributionNotFound` raised if package not installed.
    version = pkg_resources.get_distribution('microdrop').version
    major_version = f_major_version(version)

    # Look up MicroDrop application directories based on major
    # version.
    microdrop_env_dirs = AppDirs('MicroDrop', version='{}.0'
                                 .format(major_version))
    # Construct path to cached latest version info.
    cached_version_path = (microdrop_env_dirs.user_config_dir
                           .joinpath('latest-version.yml'))

    cached_version_info = {}

    # Load cached version as a dictionary, (at least) including:
    #
    #  - `'version'` (str): A `microdrop` package version specifier.
    if cached_version_path.isfile():
        try:
            with cached_version_path.open('r') as input_:
                cached_version_info = yaml.load(input_.read())
                assert(isinstance(cached_version_info, dict))
        except:
            # Assume corrupted cached version file.
            try:
                # Delete corrupted cached version file.
                cached_version_path.remove()
            except:
                # Nothing more we can do if removal fails.
                logger.error('Could not delete malformed.', exc_info=True)
    return cached_version_path, cached_version_info


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(message)s')

    logging.info('Caching the latest version number of MicroDrop available.')
    print '    ',
    try:
        cache_microdrop_version()
    except:
        logger.debug('Error looking up latest MicroDrop version.',
                     exc_info=True)
