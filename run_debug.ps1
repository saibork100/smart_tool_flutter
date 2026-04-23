# Run Flutter in debug mode — clears Debug dir first to avoid LNK1104
Set-Location "D:\smart_tool_flutter"
Stop-Process -Name "smart_tool_recognition" -Force -ErrorAction SilentlyContinue
$debugDir = "D:\smart_tool_flutter\build\windows\x64\runner\Debug"
if (Test-Path $debugDir) {
    Remove-Item $debugDir -Recurse -Force -ErrorAction SilentlyContinue
}
flutter run -d windows
