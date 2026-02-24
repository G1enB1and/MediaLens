$path = 'c:\My_Projects\MediaManagerX\MediaManagerX\native\mediamanagerx_app\main.py'
$lines = Get-Content $path
# keep lines 1..2568 (indices 0..2567) and 2599..end (indices 2598..end)
$fixed = $lines[0..2567] + $lines[2598..($lines.Count-1)]
$fixed | Set-Content $path
