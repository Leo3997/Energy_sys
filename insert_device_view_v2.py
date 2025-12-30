import sys

# Read entire file
with open('f:/energy/dashboard.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find </main> tag
main_close_line = -1
for i, line in enumerate(lines):
    if '</main>' in line:
        main_close_line = i
        break

if main_close_line == -1:
    print("ERROR: Could not find </main> tag")
    sys.exit(1)

print(f"Found </main> at line {main_close_line + 1}")

# Check if view-devices already exists
content = ''.join(lines)
if 'view-devices' in content:
    print("Device view already exists, skipping insertion")
    sys.exit(0)

# HTML to insert (before </main>)
device_view_html = '''
            <!-- Device Overview View -->
            <div id="view-devices" class="view-section" style="display: none;">
                <div class="header">
                    <div class="header-left">
                        <h1>
                            <span class="header-title-gradient">全厂设备概览</span>
                            <span style="font-size: 14px; color: var(--text-secondary); margin-top: 4px; font-weight: 400;">
                                Discovered Devices from InfluxDB
                            </span>
                        </h1>
                    </div>
                    <div class="header-controls">
                        <button class="control-btn" onclick="fetchDeviceList()">
                            <i class="ri-refresh-line"></i> 刷新列表
                        </button>
                    </div>
                </div>

                <div id="device-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 20px; margin-top: 24px;">
                    <div style="color: var(--text-muted); padding: 20px;">Loading devices...</div>
                </div>
            </div>

'''

# Insert before </main>
lines.insert(main_close_line, device_view_html)

# Write back
with open('f:/energy/dashboard.html', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("✅ Successfully inserted device view HTML before </main>")
