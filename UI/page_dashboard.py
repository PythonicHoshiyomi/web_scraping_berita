from PySide6 import QtWidgets, QtUiTools, QtCore
from PySide6.QtWidgets import QHeaderView, QTableWidgetItem
from PySide6.QtCore import QFile, Qt, QDate
import os

def load_ui(filename):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
    loader = QtUiTools.QUiLoader()
    f = QFile(path)
    f.open(QFile.OpenModeFlag.ReadOnly)
    ui = loader.load(f, None)
    f.close()
    return ui

class PageDashboard:
    def __init__(self):
        self.ui   = load_ui('page_dashboard.ui')
        central   = self.ui.centralWidget()

        # Ambil content area saja (tanpa sidebar bawaan .ui)
        # karena sidebar sudah ada di main.py
        from PySide6.QtWidgets import QFrame
        content_widget = central.findChild(QFrame, 'Sidebar')
        if content_widget:
            content_widget.hide()  # Sembunyikan sidebar bawaan

        self.page = central

        # Referensi widget
        self.table          = self.page.findChild(QtWidgets.QTableWidget, 'tableWidget')
        self.lbl_val_artikel= self.page.findChild(QtWidgets.QLabel,       'label_val_artikel')
        self.lbl_val_portal = self.page.findChild(QtWidgets.QLabel,       'label_val_portal')
        self.lbl_val_time   = self.page.findChild(QtWidgets.QLabel,       'label_val_time')
        self.lbl_date       = self.page.findChild(QtWidgets.QLabel,       'label_date')
        self.mini_val1      = self.page.findChild(QtWidgets.QLabel,       'miniVal1')
        self.mini_val2      = self.page.findChild(QtWidgets.QLabel,       'miniVal2')
        self.mini_val3      = self.page.findChild(QtWidgets.QLabel,       'miniVal3')
        self.combo_filter   = self.page.findChild(QtWidgets.QComboBox,    'comboBox_filter')

        self._setup_table()
        self._setup_date()
        self._setup_filter()

    def _setup_table(self):
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)

    def _setup_date(self):
        today = QDate.currentDate()
        bulan = ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni",
                 "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
        self.lbl_date.setText(f"📅  {today.day()} {bulan[today.month()]} {today.year()}")

    def _setup_filter(self):
        self.combo_filter.currentTextChanged.connect(self._on_filter_changed)

    def _on_filter_changed(self, text):
        keyword = "" if text == "Semua Portal" else text
        for row in range(self.table.rowCount()):
            match = any(
                self.table.item(row, col) and keyword.lower() in self.table.item(row, col).text().lower()
                for col in range(self.table.columnCount())
            )
            self.table.setRowHidden(row, not match if keyword else False)

    def get_page(self):
        return self.page

    def add_row(self, judul, tanggal, website):
        row = self.table.rowCount()
        self.table.insertRow(row)
        judul_item   = QTableWidgetItem(judul)
        tanggal_item = QTableWidgetItem(tanggal)
        website_item = QTableWidgetItem(website)
        tanggal_item.setTextAlignment(Qt.AlignCenter)
        website_item.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(row, 0, judul_item)
        self.table.setItem(row, 1, tanggal_item)
        self.table.setItem(row, 2, website_item)

    def update_stats(self, total, portal, waktu):
        self.lbl_val_artikel.setText(str(total))
        self.lbl_val_portal.setText(portal)
        self.lbl_val_time.setText(waktu)

    def update_mini_cards(self, total_portal, hari_ini, status="✔  Running"):
        self.mini_val1.setText(f"🌐  {total_portal}")
        self.mini_val2.setText(f"📄  {hari_ini}")
        self.mini_val3.setText(status)

    def update_filter_options(self, portals):
        self.combo_filter.blockSignals(True)
        self.combo_filter.clear()
        self.combo_filter.addItem("Semua Portal")
        self.combo_filter.addItems(portals)
        self.combo_filter.blockSignals(False)
