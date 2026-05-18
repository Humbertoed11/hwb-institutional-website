path = 'HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/main_app.py'
with open(path, 'r') as f:
    lines = f.readlines()

new_lines = []
for i, line in enumerate(lines):
    if 'try:' in line and 'render_template' in lines[i+1]:
        # Identify the indent
        indent = line[:line.find('try:')]
        new_lines.append(line)
        new_lines.append('    ' + lines[i+1])
        # Add the except block after the render_template line
        # I need to find where the render_template call ends
    else:
        new_lines.append(line)
# (Actually, let's just restore the file and do a cleaner injection)
