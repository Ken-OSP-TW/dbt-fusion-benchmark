# measures end-to-end dbt buld wall clock time.
# + project parsing
# + Jinja rendering and SQL compilation
# +DuckDB connection
# + DuckDB SQL execution
# + table creation
$ErrorActionPreference = "Stop"

$rows = 1000000
$runs = 5

$coreDbt = ".\.venv-core\Scripts\dbt.exe"
$fusionDbt = ".\.venv-fusion\Scripts\dbt.exe"

New-Item -ItemType Directory -Force -Path ".\warehouse" | Out-Null
New-Item -ItemType Directory -Force -Path ".\benchmark_results" | Out-Null

$results = @()

for ($run = 1; $run -le $runs; $run++) {
    # Alternate order on each repetition to reduce machine/cache bias.
    if ($run % 2 -eq 1) {
        $engines = @(
            @{ Name = "core"; Executable = $coreDbt },
            @{ Name = "fusion"; Executable = $fusionDbt }
        )
    }
    else {
        $engines = @(
            @{ Name = "fusion"; Executable = $fusionDbt },
            @{ Name = "core"; Executable = $coreDbt }
        )
    }

    foreach ($engine in $engines) {
        $databasePath = ".\warehouse\$($engine.Name)_run_$run.duckdb"

        Remove-Item $databasePath -Force -ErrorAction SilentlyContinue

        $env:DUCKDB_PATH = $databasePath

        Write-Host ""
        Write-Host "===== Run $run / $runs : $($engine.Name) ====="

        $duration = Measure-Command {
            & $engine.Executable parse `
                --profiles-dir . `
                --no-partial-parse `
                --vars "{`"rows`": $rows}"
        }

        $results += [PSCustomObject]@{
            Engine  = $engine.Name
            Run     = $run
            Rows    = $rows
            Seconds = [Math]::Round($duration.TotalSeconds, 3)
        }
    }
}

Remove-Item Env:\DUCKDB_PATH -ErrorAction SilentlyContinue

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$outputFile = ".\benchmark_results\parse_$timestamp.csv"

$results | Export-Csv -Path $outputFile -NoTypeInformation

Write-Host ""
Write-Host "Results written to: $outputFile"
$results | Format-Table -AutoSize