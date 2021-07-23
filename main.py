from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from pathlib import Path
from math import *
from random import*
from shutil import copyfile
from functools import partial
import re
import os
import sys
import ctypes

myappid = 'kr.edoli.namity' # arbitrary string
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

root_path = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()

source_tooltip = 'Regular expression'

target_tooltip = 'i: index \n' + \
                 'fn: file name \n' + \
                 'name: file name without extension \n' + \
                 'ext: extension \n' + \
                 'is_dir: is directory \n' + \
                 'st: stat (uid, gid, size, atime, mtime, ctime)'

sort_tooltip = 'fn: file name \n' + \
               'name: file name without extension \n' + \
               'ext: extension \n' + \
               'is_dir: is directory \n' + \
               'st: stat (uid, gid, size, atime, mtime, ctime)'

class MyStat():
    def __init__(self, stat):
        self.uid = stat.st_uid
        self.gid = stat.st_gid
        self.size = stat.st_size
        self.atime = stat.st_atime
        self.mtime = stat.st_mtime
        self.ctime = stat.st_ctime


def eval_sort_block(sort_function_str, fn, name, ext, is_dir, st):
    return eval(sort_function_str)


def eval_sort(sort_function_str):
    def sort_func(fn):
        path = Path(fn)
        name = path.stem
        ext = path.suffix
        if len(ext) > 0 and ext[0] == '.':
            ext = ext[1:]
        return eval_sort_block(sort_function_str, fn, name, ext, path.is_dir(), MyStat(path.stat()))
    return sort_func


def eval_block(new_fn, fn, i, name, ext, is_dir, st):
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
        self.update_listdir = False
        self.recursive = False

    def retrieve_fns(self):
        if self.recursive:
            return [str(path) for path in Path('.').rglob('*')]
        else:
            return os.listdir()

    def run(self):
        last_regex_src = None
        last_regex_dst = None
        last_sort_function = None

        fns = self.retrieve_fns()
        
        while True:
            if last_regex_src != self.regex_src or \
                last_regex_dst != self.regex_dst or \
                last_sort_function != self.sort_function or \
                self.refresh:

                self.change_status.emit('')

                try:
                    if self.update_listdir:
                        fns = self.retrieve_fns()
                        self.update_listdir = False
                except:
                    self.change_status.emit('List dir error')

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
                            filtered_fns.sort(key=eval_sort(self.sort_function))
                        except:
                            self.change_status.emit('Sort function error')

                    for i, fn in enumerate(filtered_fns):
                        m = matches[i]
                        path = Path(fn)
                        ext = path.suffix
                        if len(ext) > 0 and ext[0] == '.':
                            ext = ext[1:]
                        new_fn = m.expand(self.regex_dst)
                        new_fn = eval_block(new_fn, fn, i, path.stem, ext, path.is_dir(), MyStat(path.stat()))
                        replaced_fns.append(new_fn)

                    self.change_value.emit((filtered_fns, replaced_fns))
                except:
                    self.change_status.emit('Regular expression error')

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
        self.source_edit.setToolTip(source_tooltip)
        self.target_edit.textChanged.connect(self.regex_changed)
        self.target_edit.setToolTip(target_tooltip)
        self.sort_edit.textChanged.connect(self.regex_changed)
        self.sort_edit.setToolTip(sort_tooltip)

        self.recursive_checkbox = QCheckBox('Resursive', self)
        self.recursive_checkbox.clicked.connect(self.update_recursive_mode)

        self.remove_original_checkbox = QCheckBox('Remove original', self)
        self.remove_original_checkbox.setChecked(True)

        self.regist_context_button = QPushButton('Regist context menu', self)
        self.regist_context_button.clicked.connect(self.add_registry)

        self.source_list = QListWidget(self)
        self.target_list = QListWidget(self)

        self.source_list.currentRowChanged.connect(partial(self.list_row_changed, 0))
        self.target_list.currentRowChanged.connect(partial(self.list_row_changed, 1))
        
        vs1 = self.source_list.verticalScrollBar()
        vs2 = self.target_list.verticalScrollBar()
        vs1.valueChanged.connect(partial(self.move_scrollbar, vs2))
        vs2.valueChanged.connect(partial(self.move_scrollbar, vs1))

        self.execute_button = QPushButton('Execute')
        self.execute_button.clicked.connect(self.execute_replace)
        self.status_bar = QLabel('')

        self.source_layout = QHBoxLayout()
        self.source_layout.addWidget(self.source_edit)
        self.source_layout.addWidget(self.recursive_checkbox)
        
        self.form_layout = QGridLayout()
        self.form_layout.addWidget(QLabel('Source'), 0, 0)
        self.form_layout.addLayout(self.source_layout, 0, 1)
        self.form_layout.addWidget(QLabel('Destination'), 1, 0)
        self.form_layout.addWidget(self.target_edit, 1, 1)
        self.form_layout.addWidget(QLabel('Sort function'), 2, 0)
        self.form_layout.addWidget(self.sort_edit, 2, 1)

        self.option_layout = QHBoxLayout()
        self.option_layout.addWidget(self.remove_original_checkbox)
        self.option_layout.addWidget(self.regist_context_button)

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
            if len(self.replaced_fns) != len(set(self.replaced_fns)):
                self.regex_status('File name duplication')
                return
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

    def move_scrollbar(self, vs, value):
        vs.setValue(value)

    def regex_changed(self):
        self.worker.regex_src = self.source_edit.text()
        self.worker.regex_dst = self.target_edit.text()
        self.worker.sort_function = self.sort_edit.text()

    def list_row_changed(self, index):
        if index == 0:
            self.target_list.setCurrentRow(self.source_list.currentRow())
        elif index == 1:
            self.source_list.setCurrentRow(self.target_list.currentRow())

    def list_changed(self, value):
        self.source_list.clear()
        self.target_list.clear()

        self.source_list.addItems(value[0])
        self.target_list.addItems(value[1])

        self.filtered_fns = value[0]
        self.replaced_fns = value[1]

    def regex_status(self, value):
        self.status_bar.setText(f'<span style="color:#ff0000;">{value}</span>')

    def update_recursive_mode(self):
        checked = self.recursive_checkbox.isChecked()
        self.worker.recursive = checked
        self.worker.update_listdir = True
        self.worker.refresh = True

    def add_registry(self):
        err = os.system(f'{os.path.dirname(sys.argv[0])}\\registry.bat')

        if err == 0:
            msg = QMessageBox()
            msg.setText("Context menu registered")
            msg.setStandardButtons(QMessageBox.Ok)
            retval = msg.exec_()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(f'{os.path.dirname(sys.argv[0])}/icon.ico'))
    ex = MainApp()
    sys.exit(app.exec_())