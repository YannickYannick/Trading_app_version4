@echo off
echo Creating migrations...
python manage.py makemigrations trading
if %errorlevel% neq 0 (
    echo Error creating migrations!
    pause
    exit /b %errorlevel%
)

echo.
echo Applying migrations...
python manage.py migrate
if %errorlevel% neq 0 (
    echo Error applying migrations!
    pause
    exit /b %errorlevel%
)

echo.
echo Initializing algorithm schemas...
python manage.py init_algorithm_schemas
if %errorlevel% neq 0 (
    echo Error initializing schemas!
    pause
    exit /b %errorlevel%
)

echo.
echo All done! You can now restart your Django server.
pause



