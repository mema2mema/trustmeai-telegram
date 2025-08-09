Param(
  [string]$Token,
  [string]$BaseUrl = "https://trustmeai-telegram-production.up.railway.app"
)
if (-not $Token) { Write-Error "Usage: .\set_webhook.ps1 -Token <BOT_TOKEN>"; exit 1 }
Invoke-RestMethod -Uri "https://api.telegram.org/bot$Token/deleteWebhook" -Method Post
Invoke-RestMethod -Uri "https://api.telegram.org/bot$Token/setWebhook" -Method Post -Body @{ url = "$BaseUrl/webhook/$Token" }
Write-Host "Webhook set to $BaseUrl/webhook/$Token"
