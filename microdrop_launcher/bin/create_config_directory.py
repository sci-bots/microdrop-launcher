'''
Create MicroDrop configuration directory.

If output directory already exists, rename directory and offer to move existing
`devices` directory (containing experiment logs).
'''
import sys

from path_helpers import path
try:
    import gtk
    import pygtkhelpers.ui.dialogs as gd
except ImportError:
    GUI_AVAILABLE = False
else:
    GUI_AVAILABLE = True

from ..config import create_config_directory


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
        folder = gd.select_folder(folder=args.output_dir, title='Select '
                                  'MicroDrop configuration output folder')
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


if __name__ == '__main__':
    args = parse_args()
    try:
        launcher_path = create_config_directory(output_dir=args.output_dir,
                                                overwrite=args.force_overwrite)
    except IOError, exception:
        print >> sys.stderr, exception
    else:
        launcher_path.parent.joinpath('devices').makedirs_p()
        launcher_path.parent.joinpath('plugins').makedirs_p()
        message = ('Start MicroDrop with the following:\n\n    {}'
                   .format('"{}"'.format(launcher_path) if ' ' in launcher_path
                           else launcher_path))
        if GUI_AVAILABLE and args.gui:
            gd.info(message)
        else:
            print message
