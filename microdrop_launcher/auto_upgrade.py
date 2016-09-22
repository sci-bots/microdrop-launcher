import pip_helpers as pih


def auto_upgrade(package_name='microdrop-launcher'):
    '''
    Upgrade current package, w/o upgrading dependencies that are already
    satisfied.

    See `here`_ for more details.

    .. _here: https://gist.github.com/qwcode/3088149
    '''
    # Upgrade package *without installing any dependencies*.
    pih.install(['-U', '--no-deps', '--no-cache', package_name])
    # Install any *new* dependencies.
    pih.install(['--no-cache', package_name])
