# Registers a weekly Windows task that runs pipeline/update.py (Sundays 10:00).
# If the PC is off at that time, it runs at the next start-up.
# Remove it with:  Unregister-ScheduledTask -TaskName "Earth Economy data update" -Confirm:$false
$root   = Split-Path -Parent $PSScriptRoot
$python = (Get-Command python).Source
$action = New-ScheduledTaskAction -Execute $python -Argument "`"$root\pipeline\update.py`"" -WorkingDirectory $root
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 10:00
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RunOnlyIfNetworkAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 1)
Register-ScheduledTask -TaskName "Earth Economy data update" -Action $action -Trigger $trigger -Settings $settings `
  -Description "Downloads index, exchange-rate and World Bank data, checks it, and rebuilds the site data. Log: pipeline\logs\latest.md" -Force
