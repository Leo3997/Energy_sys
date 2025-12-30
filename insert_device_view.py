import re

# Read the file
with open('f:/energy/dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()

# The HTML to insert
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

# Check if already exists
if 'view-devices' in content:
    print("Device view already exists in file")
else:
    # Find the pattern: closing div of view-dashboard followed by </main>
    # We want to insert before </main>
    pattern = r'(</div>\s*</main>)'
    
    # Insert device view before </main>
    new_content = re.sub(pattern, device_view_html + r'\n\1', content, count=1)
    
    if new_content != content:
        with open('f:/energy/dashboard.html', 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("Successfully inserted device view HTML")
    else:
        print("Pattern not found, trying alternative approach")
        # Try finding just </main>
        if '</main>' in content:
            parts = content.rsplit('</main>', 1)
            new_content = parts[0] + device_view_html + '\n        </main>' + (parts[1] if len(parts) > 1 else '')
            with open('f:/energy/dashboard.html', 'w', encoding='utf-8') as f:
                f.write(new_content)
            print("Successfully inserted device view HTML (alternative method)")
        else:
            print("ERROR: Could not find </main> tag")
