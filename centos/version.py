import sys
import os

apps = ['dd', 'dm1', 'dmd', 'fshd', 'sma']

if len(sys.argv) <> 3:
    print "version.py <old_version> <new_version>"
    exit(1)
    
old_version = sys.argv[1]
new_version = sys.argv[2]

for app in apps:
    os.chdir(app)
    try:
        spec_file = open("%s.spec" % app, "r+")
        content = spec_file.read()
        content = content.replace(old_version, new_version)
        spec_file.seek(0)
        spec_file.truncate()
        spec_file.write(content)
    finally:
        spec_file.close()
        os.chdir("..")