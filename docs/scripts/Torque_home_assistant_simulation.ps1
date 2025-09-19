# --- Forcer l'UTF-8 dans la console WinPS 5.1 ---
chcp.com 65001 | Out-Null
[Console]::InputEncoding  = [Text.Encoding]::UTF8
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$OutputEncoding           = [Text.Encoding]::UTF8

# ---------- CONFIG ----------
$base    = "https://XXXXXXXXXXX.duckdns.org"     # PAS de /api/torque_pro ici
$token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.XXXXX0XXXXX0XXXXXXXXXXX0XXX0XXXXXXXXXXXXXXXXXXX0XXXXXXXXXXXXXXX0XXX0XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX0XX.GYJR7CP-ICZ45U3mMeuFbO-0kAEf1gKu7kDUVDVuaIw"
$headers = @{ "Authorization" = "Bearer $token" }
$uri     = "$base/api/torque_pro"
$skipCert = $false                           # $true si HTTPS self-signed (PS 7+)

function Send-TorqueFrame {
    param(
        [Parameter(Mandatory=$true)][string]$ProfileName,   
        [Parameter(Mandatory=$true)][string]$VehicleId,      
        [double]$Lat = 48.8566,
        [double]$Lon = 2.3522
    )

    $session = ([guid]::NewGuid().ToString("N")).Substring(0,12)

    # Corps POST comme Torque (x-www-form-urlencoded)
    $body = @{
        # COMMANDE SI 1 SEULE ENTREE TORQUE DANS HA: commente la ligne suivante
        eml          = "exemple@community.home-assistant"
        session      = $session
        id           = $VehicleId
        profileName  = $ProfileName
        lang         = "fr"

        "kff1006"    = ("{0:F6}" -f $Lat)   # GPS Latitude
        "kff1005"    = ("{0:F6}" -f $Lon)   # GPS Longitude
        "kff1010"    = "120"                # Altitude (m)
        "kff1239"    = "5"                  # Précision (m)

        "kff1266"    = "300"                # trip_time_since_start (s) -> converti en min
        "kff1268"    = "900"                # trip_time_moving (s)     -> converti en min
    }

    $ct = "application/x-www-form-urlencoded; charset=utf-8"
    if ($skipCert) {
        Invoke-RestMethod -Method Post -Uri $uri -Headers $headers -Body $body -ContentType $ct -SkipCertificateCheck
    } else {
        Invoke-RestMethod -Method Post -Uri $uri -Headers $headers -Body $body -ContentType $ct
    }
}  # FIN FONCTION

# (optionnel) Vérifier que l’endpoint répond
try {
    Invoke-RestMethod -Method Head -Uri $uri -Headers $headers | Out-Null
    Write-Host "Endpoint OK"
} catch {
    Write-Host $_
}

# ---------- SCÉNARIO DE TEST (téléphone community.home-assistant.io) ----------
# 1) "Simulation Car1 community.home-assistant.io"
1..5 | ForEach-Object {
    $lat = 48.84 + (Get-Random -Minimum -0.002 -Maximum 0.002)
    $lon = 2.34  + (Get-Random -Minimum -0.002 -Maximum 0.002)
    Send-TorqueFrame -ProfileName "Simulation Car1 community.home-assistant.io" -VehicleId "175812" -Lat $lat -Lon $lon
    Start-Sleep -Milliseconds 300
}

# 2) "Simulation Car2 community.home-assistant.io"
1..5 | ForEach-Object {
    $lat = 48.87 + (Get-Random -Minimum -0.002 -Maximum 0.002)
    $lon = 2.37  + (Get-Random -Minimum -0.002 -Maximum 0.002)
    Send-TorqueFrame -ProfileName "Simulation Car2 community.home-assistant.io" -VehicleId "175812" -Lat $lat -Lon $lon
    Start-Sleep -Milliseconds 300
}

Write-Host "Fini. Va voir dans HA → Paramètres → Appareils & services → Torque Pro. | Done. Go to HA → Settings → Devices & Services → Torque Pro." 