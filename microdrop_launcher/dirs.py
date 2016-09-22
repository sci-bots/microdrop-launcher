import appdirs
import path_helpers as ph

from . import conda_prefix

class AppDirs(appdirs.AppDirs):
    """Convenience wrapper for getting application dirs."""
    def __init__(self, *args, **kwargs):
        self.conda_prefix = conda_prefix()
        super(AppDirs, self).__init__(*args, **kwargs)

    def _get_conda_path(self, base):
        sub_directories = map(str, [v for v in (self.appauthor, self.appname,
                                                self.version) if v])
        return self.conda_prefix.joinpath(*[base] + sub_directories)

    @property
    def user_data_dir(self):
        if self.conda_prefix is None:
            return ph.path(appdirs.AppDirs.user_data_dir.fget(self))
        else:
            return self._get_conda_path('share')

    @property
    def site_data_dir(self):
        if self.conda_prefix is None:
            return ph.path(appdirs.AppDirs.site_data_dir.fget(self))
        else:
            return self.user_data_dir

    @property
    def user_config_dir(self):
        if self.conda_prefix is None:
            return ph.path(appdirs.AppDirs.user_config_dir.fget(self))
        else:
            return self._get_conda_path('etc')

    @property
    def site_config_dir(self):
        if self.conda_prefix is None:
            return ph.path(appdirs.AppDirs.site_config_dir.fget(self))
        else:
            return self.user_config_dir

    @property
    def user_cache_dir(self):
        if self.conda_prefix is None:
            return ph.path(appdirs.AppDirs.user_cache_dir.fget(self))
        else:
            return self._get_conda_path('cache')

    @property
    def user_log_dir(self):
        if self.conda_prefix is None:
            return ph.path(appdirs.AppDirs.user_log_dir.fget(self))
        else:
            return self._get_conda_path('cache').joinpath('log')
