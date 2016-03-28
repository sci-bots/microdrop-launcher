import sys

from path_helpers import path
try:
    import gtk
    import pygtkhelpers.ui.dialogs as gd
except ImportError:
    GUI_AVAILABLE = False
else:
    GUI_AVAILABLE = True

import jinja2


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

# Batch file template.
launcher_template = '''
REM Change into [parent directory of batch file][1].
REM
REM [1]: http://stackoverflow.com/questions/16623780/how-to-get-windows-batchs-parent-folder
cd "%~dp0"
REM Launch Microdrop
"{{ py_exe }}" -m microdrop.microdrop -c "%~dp0microdrop.ini"
'''


def parse_args(args=None):
    '''Parses arguments, returns (options, args).'''
    from argparse import ArgumentParser

    if args is None:
        args = sys.argv

    parser = ArgumentParser(description='Create portable MicroDrop settings '
                            'directory.')
    parser.add_argument('-g', '--gui', action='store_true', help='Use dialog '
                        'to select output directory.')
    parser.add_argument('-f', '--force-overwrite', action='store_true',
                        help='Overwrite existing files in output directory.')
    parser.add_argument('output_dir', type=path, nargs='?',
                        help='Output directory.')

    args = parser.parse_args()

    if args.gui:
        if not GUI_AVAILABLE:
            parser.error('Please install `gtk` and `pygtkhelpers`.')

        if args.output_dir is not None and not args.output_dir.isdir():
            # Starting output directory was specified, but does not exist.
            parser.error('Directory "{}" does not exist.'
                         .format(args.output_dir))
            raise SystemExit(-1)

        # Display GTK dialog to select output directory.
        folder = gd.select_folder(folder=args.output_dir)
        if folder is None:
            parser.error('Folder selection cancelled.')
        folder = path(folder)
        if not args.force_overwrite and folder.isdir() and folder.listdir():
            response = gd.yesno('Output directory already exists and is not '
                                'empty.\n\nOverwrite?')
            if response == gtk.RESPONSE_YES:
                args.force_overwrite = True

        args.output_dir = folder
    elif args.output_dir is None:
        parser.error('No output directory specified.')

    return args


def main(output_dir, overwrite=False):
    '''
    Initialize output directory with minimal Microdrop configuration.

    The created configuration causes Microdrop to store plugins and device
    files within the configuration directory.  A batch file `microdrop.bat` is
    also created in the directory to launch Microdrop using the configuration.
    Note that the `microdrop.bat` can be launched within any working directory.

    Args
    ----

        output_dir (str) : Path to output directory.
        overwrite (bool) : If `False`, do not write to output directory if it
            already exists and is not empty.

    Returns
    -------

        (str) : Path to launcher script (i.e., `microdrop.bat`).
    '''
    output_dir = path(output_dir)

    if not output_dir.isdir():
        output_dir.makedirs_p()
    elif not overwrite and list(output_dir.files()):
        raise IOError('Output directory exists and is not empty.')

    config_path = output_dir.joinpath('microdrop.ini')
    with config_path.open('wb') as output:
        template = jinja2.Template(config_template)
        config_str = template.render(output_dir=output_dir.name)
        output.write(config_str)

    py_exe = path(sys.executable).abspath()
    launcher_path = output_dir.joinpath('microdrop.bat').abspath()
    with launcher_path.open('wb') as output:
        template = jinja2.Template(launcher_template)
        launcher_str = template.render(working_dir=output_dir.abspath(),
                                       py_exe=py_exe,
                                       config_path=config_path.abspath())
        output.write(launcher_str)

    return launcher_path


if __name__ == '__main__':
    args = parse_args()
    try:
        launcher_path = main(output_dir=args.output_dir,
                             overwrite=args.force_overwrite)
    except IOError, exception:
        print >> sys.stderr, exception
    else:
        message = ('Start MicroDrop with the following:\n\n    {}'
                   .format('"{}"'.format(launcher_path) if ' ' in launcher_path
                           else launcher_path))
        if GUI_AVAILABLE and args.gui:
            gd.info(message)
        else:
            print message
