from PySide6 import QtWidgets, QtUiTools, QtCore
from PySide6.QtWidgets import QHeaderView
from PySide6.QtCore import QFile
import os

def load_ui(filename):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
    loader = QtUiTools.QUiLoader()
    f = QFile(path)
    f.open(QFile.OpenModeFlag.ReadOnly)
    ui = loader.load(f, None)
    f.close()
    return ui

class PageScrap:
    def __init__(self):
        self.ui   = load_ui('page_scrap.ui')
        central   = self.ui.centralWidget()
        from PySide6.QtWidgets import QFrame
        sidebar = central.findChild(QFrame, 'Sidebar')
        if sidebar:
            sidebar.hide()
        self.page = central

        # Referensi widget — sesuai nama di ui_Scrap_v2
        self.table       = self.page.findChild(QtWidgets.QTableWidget,   'tableWidget')
        self.lineEdit    = self.page.findChild(QtWidgets.QLineEdit,      'lineEdit')
        self.progressBar = self.page.findChild(QtWidgets.QProgressBar,   'progressBar')
        self.logEdit     = self.page.findChild(QtWidgets.QPlainTextEdit, 'plainTextEdit')
        self.btnStart    = self.page.findChild(QtWidgets.QPushButton,    'pushButton_4')
        self.btnExport   = self.page.findChild(QtWidgets.QPushButton,    'btn_export')

        self._setup_table()

    def _setup_table(self):
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.setColumnWidth(0, 40)
        self.table.setColumnWidth(2, 100)

    def get_page(self):
        return self.page
