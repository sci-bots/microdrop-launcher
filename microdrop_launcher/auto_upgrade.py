import logging

import pip_helpers as pih

from . import conda_prefix, conda_upgrade


logger = logging.getLogger(__name__)


def auto_upgrade():
    '''
    Upgrade package.

    Parameters
    ----------
    package_name : str
        Package name.

    Returns
    -------
    (upgraded, original_version, new_version) : (bool, str)
        Tuple containing:
         - :data:`upgraded`: ``True`` if package was upgraded.
         - :data:`original_version`: Package version before upgrade.
         - :data:`new_version`:
             Package version after upgrade.  If package is up-to-date, this is
             the same as :data:`original_version`.
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
    except Exception, exception:
        logger.debug('Error upgrading:\n%s', exception)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    auto_upgrade()
