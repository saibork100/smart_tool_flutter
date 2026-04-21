param([int]$Device = 1)

# Add adb to PATH — adjust if your Android SDK is in a different location
$env:PATH += ";$env:LOCALAPPDATA\Android\Sdk\platform-tools"

# Replace with your Android phone's IP address (Settings > Developer options > Wireless debugging)
if ($Device -eq 2) {
    $target = "x.x.x.x:5555"   # put your Android phone IP address here
} else {
    $target = "x.x.x.x:5555"   # put your Android phone IP address here
}

adb connect $target
flutter run -d $target
