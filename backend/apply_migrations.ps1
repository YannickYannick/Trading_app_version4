# Script PowerShell pour appliquer les migrations

Write-Host "Creating migrations..." -ForegroundColor Cyan
python manage.py makemigrations trading
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error creating migrations!" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Applying migrations..." -ForegroundColor Cyan
python manage.py migrate
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error applying migrations!" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Initializing algorithm schemas..." -ForegroundColor Cyan
python manage.py init_algorithm_schemas
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error initializing schemas!" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "All done! You can now restart your Django server." -ForegroundColor Green

