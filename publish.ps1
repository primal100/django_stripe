[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'High')]
param(
    [switch]$Publish,
    [ValidateSet('pypi', 'testpypi')]
    [string]$Repository = 'pypi',
    [string]$Python = 'python'
)

$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot

Push-Location $projectRoot
try {
    $version = & $Python -c "from django_stripe import __version__; print(__version__)"
    if ($LASTEXITCODE -ne 0 -or -not $version) {
        throw "Could not read the package version. Ensure '$Python' can import django_stripe."
    }
    $version = $version.Trim()

    & $Python -c "import build, twine" 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "Release tools are missing. Install them with: $Python -m pip install -e '.[release]'"
    }

    $releaseRoot = Join-Path $projectRoot 'dist'
    $releaseDirectory = Join-Path $releaseRoot "publish-$version-$([guid]::NewGuid().ToString('N'))"
    New-Item -ItemType Directory -Path $releaseDirectory | Out-Null
    Write-Host "Building django-stripe-subs $version..."
    & $Python -m build --outdir $releaseDirectory
    if ($LASTEXITCODE -ne 0) { throw 'Package build failed.' }

    $artifacts = @(Get-ChildItem -LiteralPath $releaseDirectory -File | Where-Object { $_.Name -match '\.(whl|tar\.gz)$' })
    if ($artifacts.Count -ne 2 -or @($artifacts | Where-Object Extension -eq '.whl').Count -ne 1 -or @($artifacts | Where-Object Name -Match '\.tar\.gz$').Count -ne 1) {
        throw "Expected exactly one wheel and one source archive in '$releaseDirectory'."
    }

    & $Python -m twine check --strict @($artifacts.FullName)
    if ($LASTEXITCODE -ne 0) { throw 'Twine validation failed.' }

    & $Python scripts/check_distribution.py $releaseDirectory
    if ($LASTEXITCODE -ne 0) { throw 'Distribution contents validation failed.' }

    Write-Host "Validated version $version. Artifacts are in: $releaseDirectory"
    if (-not $Publish) {
        Write-Host "Dry run only. To upload, run: .\publish.ps1 -Publish -Repository $Repository"
        return
    }

    $target = if ($Repository -eq 'pypi') { 'PyPI' } else { 'TestPyPI' }
    if ($PSCmdlet.ShouldProcess("$target version $version", 'Upload validated wheel and source archive with Twine')) {
        & $Python -m twine upload --repository $Repository @($artifacts.FullName)
        if ($LASTEXITCODE -ne 0) { throw "Twine upload to $target failed." }
        Write-Host "Published django-stripe-subs $version to $target."
    }
}
finally {
    Pop-Location
}
