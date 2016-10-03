import logging

import pip_helpers as pih

from . import conda_prefix, conda_upgrade


logger = logging.getLogger(__name__)


def auto_upgrade():
    '''
    Upgrade package.

    .. versionadded:: 0.1.post43

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
    '''
    try:
        package_name = 'microdrop-launcher'
        if conda_prefix():
            result = conda_upgrade(package_name)
        else:
            result = pih.upgrade(package_name)
        if result['new_version']:
            logger.info('Upgraded %s: %s->%s', result['package'],
                        result['original_version'], result['new_version'])
        else:
            logger.info('%s up to date: %s', result['package'],
                        result['original_version'])
        return result
    except Exception, exception:
        logger.debug('Error upgrading:\n%s', exception)
        return {'original_version': None, 'new_version': None,
                'installed_dependencies': []}


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    auto_upgrade()
