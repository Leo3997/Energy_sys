import re

# Read the file
with open('f:/energy/dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Find and remove the view-devices section (it's in the wrong place)
# Pattern to match the entire view-devices div
pattern = r'\s*<!-- Device Overview View -->.*?<div id="view-devices".*?</div>\s*</div>\s*'
content_cleaned = re.sub(pattern, '', content, flags=re.DOTALL)

# Now find the closing tag of view-settings to insert view-devices AFTER it
# Find </div> that closes view-settings, followed by </main>
settings_end_pattern = r'(</div>\s*<!-- End view-settings or similar -->.*?)(</main>)'

# If that doesn't work, try finding the id="view-settings" closing
# Actually, let's find </main> and insert before it

main_close_index = content_cleaned.rfind('</main>')
if main_close_index == -1:
    print("ERROR: </main> not found")
    exit(1)

# Insert the view-devices section before </main>
device_view_html = '''
            <!-- Device Overview View -->
            <div id="view-devices" class="view-section">
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

new_content = content_cleaned[:main_close_index] + device_view_html + content_cleaned[main_close_index:]

# Write back
with open('f:/energy/dashboard.html', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("✅ Fixed view-devices nesting - removed from wrong location and re-inserted before </main>")
print("   Note: Removed inline 'display: none' style")
