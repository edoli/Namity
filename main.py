from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from pathlib import Path
from math import *
from random import*
from shutil import copyfile
import re
import os
import sys
import ctypes

myappid = 'kr.edoli.namity' # arbitrary string
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

root_path = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()

def eval_block(new_fn, fn, i, name, ext):
    return eval("f'{}'".format(new_fn))


class Worker(QThread):

    change_value = pyqtSignal(tuple)
    change_status = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.regex_src = ''
        self.regex_dst = ''
        self.sort_function = ''
        self.refresh = False

    def run(self):
        last_regex_src = None
        last_regex_dst = None
        last_sort_function = None
        while True:
            if last_regex_src != self.regex_src or \
                last_regex_dst != self.regex_dst or \
                last_sort_function != self.sort_function or \
                self.refresh:

                self.change_status.emit('')

                fns = os.listdir()

                try:
                    filtered_fns = []
                    replaced_fns = []
                    matches = []
                    pat = re.compile(self.regex_src)
                    for fn in fns:
                        m = pat.search(fn)
                        if m:
                            filtered_fns.append(fn)
                            matches.append(m)

                    if self.sort_function != '':
                        try:
                            eval('filtered_fns.sort(key=lambda x: {})'.format(self.sort_function))
                        except:
                            self.change_status.emit('sort error')

                    for i, fn in enumerate(filtered_fns):
                        m = matches[i]
                        path = Path(fn)
                        ext = path.suffix
                        if len(ext) > 0 and ext[0] == '.':
                            ext = ext[1:]
                        new_fn = m.expand(self.regex_dst)
                        new_fn = eval_block(new_fn, fn, i, path.stem, ext)
                        replaced_fns.append(new_fn)

                    self.change_value.emit((filtered_fns, replaced_fns))
                except:
                    self.change_status.emit('regular expression error')

                last_regex_src = self.regex_src
                last_regex_dst = self.regex_dst
                last_sort_function = self.sort_function
                self.refresh = False


class MainApp(QWidget):

    def __init__(self):
        super().__init__()
        self.filtered_fns = []
        self.replaced_fns = []
        self.worker = Worker()
        self.worker.change_value.connect(self.list_changed)
        self.worker.change_status.connect(self.regex_status)
        self.initUI()
        self.worker.start()

    def initUI(self):
        self.source_edit = QLineEdit('', self)
        self.target_edit = QLineEdit('', self)
        self.sort_edit = QLineEdit('', self)

        self.source_edit.textChanged.connect(self.regex_changed)
        self.target_edit.textChanged.connect(self.regex_changed)
        self.sort_edit.textChanged.connect(self.regex_changed)

        self.remove_original_checkbox = QCheckBox('Remove original', self)
        self.remove_original_checkbox.setChecked(True)

        self.source_list = QListWidget(self)
        self.target_list = QListWidget(self)

        self.execute_button = QPushButton('Execute')
        self.execute_button.clicked.connect(self.execute_replace)
        self.status_bar = QLabel('')
        
        self.form_layout = QGridLayout()
        self.form_layout.addWidget(QLabel('Source'), 0, 0)
        self.form_layout.addWidget(self.source_edit, 0, 1)
        self.form_layout.addWidget(QLabel('Destination'), 1, 0)
        self.form_layout.addWidget(self.target_edit, 1, 1)
        self.form_layout.addWidget(QLabel('Sort function'), 2, 0)
        self.form_layout.addWidget(self.sort_edit, 2, 1)

        self.option_layout = QHBoxLayout()
        self.option_layout.addWidget(self.remove_original_checkbox)

        self.list_layout = QHBoxLayout()
        self.list_layout.addWidget(self.source_list)
        self.list_layout.addWidget(QLabel('→'))
        self.list_layout.addWidget(self.target_list)

        self.layout = QVBoxLayout()
        self.layout.addLayout(self.form_layout)
        self.layout.addLayout(self.option_layout)
        self.layout.addLayout(self.list_layout)
        self.layout.addWidget(self.execute_button)
        self.layout.addWidget(self.status_bar)

        self.setLayout(self.layout)
        self.setWindowTitle('Namity')
        self.show()

    def execute_replace(self):
        if len(self.filtered_fns) == len(self.replaced_fns):
            try:
                for pair in zip(self.filtered_fns, self.replaced_fns):
                    if self.remove_original_checkbox.isChecked():
                        os.rename(pair[0], pair[1])
                    else:
                        copyfile(pair[0], pair[1])

                    self.refresh = True
            except:
                # TODO: handle file exists
                pass

    def regex_changed(self):
        self.worker.regex_src = self.source_edit.text()
        self.worker.regex_dst = self.target_edit.text()
        self.worker.sort_function = self.sort_edit.text()

    def list_changed(self, value):
        self.source_list.clear()
        self.target_list.clear()

        self.source_list.addItems(value[0])
        self.target_list.addItems(value[1])

        self.filtered_fns = value[0]
        self.replaced_fns = value[1]

    def regex_status(self, value):
        self.status_bar.setText(f'<span style="color:#ff0000;">{value}</span>')

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon('icon.ico'))
    ex = MainApp()
    sys.exit(app.exec_())