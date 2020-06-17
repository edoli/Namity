import os
import shutil

os.system('pyinstaller --onefile --noconsole --icon=icon.ico main.py')
shutil.copyfile('icon.ico', 'dist/')