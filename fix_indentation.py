import re

# Read the file
with open('kpi_refresh_system/streamlit_app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the problematic section (single company mode display_tab1)
# We need to fix indentation from line 1236 onwards
fixed_lines = lines[:1236]  # Keep everything before line 1236 as is

# Process lines from 1236 onwards
in_display_tab1 = False
indent_level = 0

for i in range(1236, len(lines)):
    line = lines[i]
    
    # Check if we're at the display_tab1 line
    if i == 1236:  # Line 1237 in 1-indexed
        fixed_lines.append(line)  # Keep "with display_tab1:" as is
        in_display_tab1 = True
        continue
    
    # If we're inside display_tab1, we need to check indentation
    if in_display_tab1:
        # Check if line starts a new with statement at wrong indentation
        if line.strip().startswith('with display_tab2:'):
            in_display_tab1 = False
            fixed_lines.append(line)
            continue
            
        # For lines inside display_tab1, ensure proper indentation
        # Count current indentation
        current_indent = len(line) - len(line.lstrip())
        
        # If line has content, add 4 spaces if it's not properly indented
        if line.strip():
            # Special handling for lines that were incorrectly dedented
            if current_indent < 12:  # Should be at least 12 spaces (3 levels)
                # Add 4 spaces to current indentation
                fixed_line = '    ' + line
            else:
                fixed_line = line
            fixed_lines.append(fixed_line)
        else:
            fixed_lines.append(line)
    else:
        fixed_lines.append(line)

# Write the fixed file
with open('kpi_refresh_system/streamlit_app_fixed.py', 'w', encoding='utf-8') as f:
    f.writelines(fixed_lines)

print("Fixed indentation and saved to streamlit_app_fixed.py")