import sys

from paver.easy import task, needs, path, sh, cmdopts, options
from paver.setuputils import setup, install_distutils_tasks
from distutils.extension import Extension
from distutils.dep_util import newer

sys.path.insert(0, path('.').abspath())
import version

setup(name='microdrop-launcher',
      version=version.getVersion(),
      description='MicroDrop launcher',
      keywords='',
      author='Christian Fobel',
      author_email='christian@fobel.net',
      url='https://github.com/wheeler-microfluidics/microdrop-launcher',
      license='GPL',
      packages=['microdrop_launcher'],
      install_requires=['jinja2', 'microdrop-plugin-manager>=0.3.post4',
                        'path_helpers'],
      # Install data listed in `MANIFEST.in`
      include_package_data=True,
      entry_points = {'console_scripts':
                      ['microdrop-profile-manager = '
                       'microdrop_launcher.bin.profile_launcher:main',
                       'launch-microdrop = '
                       'microdrop_launcher.bin.launch:main']})


@task
@needs('generate_setup', 'minilib', 'setuptools.command.sdist')
def sdist():
    """Overrides sdist to make sure that our setup.py is generated."""
    pass
