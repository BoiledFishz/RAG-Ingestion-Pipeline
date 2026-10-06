param([Parameter(Mandatory=$true)][int]$MeasurementProcessId)
# Temporary process-scoped execution request. No power policy or registry edit.
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class Project2MeasurementPower {
    [DllImport("kernel32.dll")]
    public static extern uint SetThreadExecutionState(uint flags);
}
'@
try {
    $taskExecutionResult = [Project2MeasurementPower]::SetThreadExecutionState([uint32]2147483649)
    if ($taskExecutionResult -eq 0) { throw 'Execution request failed' }
    $taskAuditPath = Join-Path (Split-Path $PSScriptRoot -Parent) 'audit/project2-v1'
    @{status='active';return_flags=$taskExecutionResult;measurement_pid=$MeasurementProcessId;helper_pid=$PID;time_utc=(Get-Date).ToUniversalTime().ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskAuditPath 'v03_power_request_active.json') -Encoding UTF8
    while (Get-Process -Id $MeasurementProcessId -ErrorAction SilentlyContinue) {
        Start-Sleep -Seconds 20
    }
} finally {
    [void][Project2MeasurementPower]::SetThreadExecutionState([uint32]2147483648)
    if ($taskAuditPath) {
        @{status='released';time_utc=(Get-Date).ToUniversalTime().ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskAuditPath 'v03_power_request_released.json') -Encoding UTF8
    }
}
