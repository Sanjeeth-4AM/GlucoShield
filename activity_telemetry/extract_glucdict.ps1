$zip = 'D:\ML PROJECT\data\raw\Glucdict\Glucdict Dataset.zip'
$out = 'D:\ML PROJECT\data\raw\Glucdict\extracted'
New-Item -ItemType Directory -Force -Path $out | Out-Null
Write-Output "Starting Expand-Archive on $zip..."
Expand-Archive -Path $zip -DestinationPath $out -Force
Write-Output "Expand-Archive completed successfully."
