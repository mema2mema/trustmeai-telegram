param(
  [Parameter(Mandatory=$true)] [string]$TELEGRAM_BOT_TOKEN
)
Invoke-RestMethod -Uri "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getWebhookInfo" -Method Get | ConvertTo-Json
