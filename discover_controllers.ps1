$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$propertyCache = @{}
function Prop($id, $name) {
    $key = $id + '|' + $name
    if ($propertyCache.ContainsKey($key)) { return $propertyCache[$key] }
    $p = Get-PnpDeviceProperty -InstanceId $id -KeyName $name -ErrorAction SilentlyContinue
    $value = if ($p) { $p.Data } else { $null }
    $propertyCache[$key] = $value
    return $value
}
# One inventory query supplies hardware IDs, compatible IDs and service names.
# Expensive container/parent queries are restricted to plausible Xbox devices.
$all = @(Get-CimInstance Win32_PnPEntity)
$byId = @{}
foreach ($d in $all) { if ($d.PNPDeviceID) { $byId[$d.PNPDeviceID] = $d } }
$result = New-Object 'System.Collections.Generic.List[object]'
foreach ($dev in $all) {
    $id = [string]$dev.PNPDeviceID
    if ($dev.Present -eq $false -or $dev.ConfigManagerErrorCode -eq 24 -or $dev.ConfigManagerErrorCode -eq 45) { continue }
    if ($id -notmatch '^(HID|USB|BTHENUM|BTHLEDEVICE|BTHLE)\\') { continue }
    $identity = $id + ' ' + (@($dev.HardwareID) -join ' ')
    if ($identity -notmatch 'VID_045E|VID&0*[12]?045E' -and $dev.Service -notmatch '^(xinputhid|xusb21|xusb22|xboxgip|xboxgipservice)$' -and $dev.Name -notmatch 'Xbox') { continue }
    $ancestors = New-Object 'System.Collections.Generic.List[object]'
    $parent = [string](Prop $id 'DEVPKEY_Device_Parent')
    for ($i = 0; $i -lt 12 -and $parent; $i++) {
        $parentRecord = $byId[$parent]
        $parentService = if ($parentRecord) { [string]$parentRecord.Service } else { [string](Prop $parent 'DEVPKEY_Device_Service') }
        $ancestors.Add(@{
            id=$parent; name=[string]$parentRecord.Name; service=$parentService;
            container=[string](Prop $parent 'DEVPKEY_Device_ContainerId')
        })
        if ($parent -match 'VIGEM|VIRTUAL|ROOT\\VJOY|ROOT\\RDP' -or $parentService -match 'ViGEm|VJoy') { break }
        $parent = [string](Prop $parent 'DEVPKEY_Device_Parent')
    }
    $result.Add(@{
        id=$id; name=[string]$dev.Name; service=[string]$dev.Service;
        hardware=@($dev.HardwareID); compatible=@($dev.CompatibleID);
        container=[string](Prop $id 'DEVPKEY_Device_ContainerId');
        ancestors=@($ancestors.ToArray())
    })
}
ConvertTo-Json -InputObject @($result.ToArray()) -Depth 8 -Compress
