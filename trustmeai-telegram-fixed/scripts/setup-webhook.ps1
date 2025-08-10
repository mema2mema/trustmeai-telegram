
param(
    [Parameter(Mandatory=$true)][string]$TELEGRAM_BOT_TOKEN,
    [Parameter(Mandatory=$true)][string]$BASE,
    [switch]$UseTokenInPath
)
Invoke-RestMethod -Uri "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/deleteWebhook" -Method Post | Out-Host
if ($UseTokenInPath) {
    Invoke-RestMethod -Uri "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook" -Method Post -Body @{ url = "$BASE/webhook/$TELEGRAM_BOT_TOKEN" } | Out-Host
} else {
    Invoke-RestMethod -Uri "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook" -Method Post -Body @{ url = "$BASE/webhook" } | Out-Host
}
Invoke-RestMethod -Uri "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getWebhookInfo" -Method Get | Out-Host
