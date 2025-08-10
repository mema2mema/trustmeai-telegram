
param(
    [Parameter(Mandatory=$true)][string]$BASE # e.g. https://your-app.up.railway.app
)
Invoke-WebRequest -Uri "$BASE/health" -UseBasicParsing | Select-Object -ExpandProperty StatusCode
