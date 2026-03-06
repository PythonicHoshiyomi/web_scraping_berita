from PySide6 import QtWidgets, QtUiTools, QtCore
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

class PageAbout:
    def __init__(self):
        self.ui   = load_ui('page_about.ui')
        central   = self.ui.centralWidget()
        from PySide6.QtWidgets import QFrame
        sidebar = central.findChild(QFrame, 'Sidebar')
        if sidebar:
            sidebar.hide()
        self.page = central

    def get_page(self):
        return self.page
