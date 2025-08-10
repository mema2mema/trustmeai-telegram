
param(
    [Parameter(Mandatory=$true)][string]$TELEGRAM_BOT_TOKEN,
    [Parameter(Mandatory=$true)][string]$BASE # e.g. https://your-app.up.railway.app
)

Write-Host "Deleting old webhook..." -ForegroundColor Cyan
Invoke-RestMethod -Uri "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/deleteWebhook" -Method Post | Out-Host

Write-Host "Setting new webhook..." -ForegroundColor Cyan
Invoke-RestMethod -Uri "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook" -Method Post -Body @{ url = "$BASE/webhook/$TELEGRAM_BOT_TOKEN" } | Out-Host

Write-Host "Webhook info:" -ForegroundColor Cyan
Invoke-RestMethod -Uri "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getWebhookInfo" -Method Get | Out-Host
