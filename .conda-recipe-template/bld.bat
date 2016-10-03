"%PYTHON%" -m pip install --no-cache --find-links http://192.99.4.95/wheels --trusted-host 192.99.4.95 "{{ package_name }}=={{ version }}"
if errorlevel 1 exit 1

:: Add more build steps here, if they are necessary.

:: See
:: http://docs.continuum.io/conda/build.html
:: for a list of environment variables that are set during the build process.
if not exist "%PREFIX%\Menu" mkdir "%PREFIX%\Menu"
copy "%RECIPE_DIR%\microdrop.ico" "%PREFIX%\Menu"
copy "%RECIPE_DIR%\Iconleak-Atrous-Console.ico" "%PREFIX%\Menu"
copy "%RECIPE_DIR%\microdrop-launcher.json" "%PREFIX%\Menu"
