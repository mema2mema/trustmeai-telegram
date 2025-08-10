param(
  [Parameter(Mandatory=$true)] [string]$TELEGRAM_BOT_TOKEN,
  [Parameter(Mandatory=$true)] [string]$BASE,
  [Parameter(Mandatory=$false)] [int]$TokenInPath = 0
)
Write-Host "Deleting old webhook..."
Invoke-RestMethod -Uri "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/deleteWebhook" -Method Post | Out-Null
if ($TokenInPath -eq 1) {
  $url = "$BASE/webhook/$TELEGRAM_BOT_TOKEN"
} else {
  $url = "$BASE/webhook"
}
Write-Host "Setting webhook to $url"
Invoke-RestMethod -Uri "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook" -Method Post -Body @{ url = $url } | ConvertTo-Json
