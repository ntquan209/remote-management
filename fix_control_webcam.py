path = r'd:\Data\Project\remote-lab-project\frontend\src\pages\control.js'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old = '''    emitCommand('WEBCAM_START', targetMachine);'''
new = '''    sessionStorage.setItem(`webcam_active_${targetMachine}`, 'TRUE');
    console.log(`[WEBCAM CONTROL] Enable webcam for ${targetMachine}`);
    emitCommand('WEBCAM_START', targetMachine);'''

if old in content:
    content = content.replace(old, new)
    with open(path, 'w', encoding='utf-8', newline='\r\n') as f:
        f.write(content)
    print("Added sessionStorage.setItem")
else:
    print("Could not find WEBCAM_START line")
