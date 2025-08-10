param(
  [Parameter(Mandatory=$true)] [string]$BASE
)
Invoke-WebRequest -Uri "$BASE" -Method Get | Select-Object -ExpandProperty StatusCode
