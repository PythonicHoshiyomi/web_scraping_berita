from PySide6 import QtWidgets, QtUiTools, QtCore
from PySide6.QtWidgets import (
    QHeaderView, QTableWidgetItem, QDialog, QVBoxLayout,
    QLabel, QTextEdit, QPushButton, QHBoxLayout, QFrame
)
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


# ── Dialog konten penuh ────────────────────────────────────────────

class ArticleDialog(QDialog):
    """Popup untuk menampilkan isi artikel secara penuh."""

    def __init__(self, judul: str, tanggal: str, website: str, konten: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Detail Artikel")
        self.resize(700, 500)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        lbl_judul = QLabel(judul)
        lbl_judul.setWordWrap(True)
        lbl_judul.setStyleSheet(
            "font-size: 15px; font-weight: bold; color: #2c3e50;"
        )
        layout.addWidget(lbl_judul)

        meta = f"🗓  {tanggal}    🌐  {website}" if tanggal else f"🌐  {website}"
        lbl_meta = QLabel(meta)
        lbl_meta.setWordWrap(True)
        lbl_meta.setStyleSheet("font-size: 11px; color: #7f8c8d;")
        layout.addWidget(lbl_meta)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #dcdde1;")
        layout.addWidget(line)

        txt = QTextEdit()
        txt.setReadOnly(True)
        txt.setPlainText(konten if konten else "(Konten tidak tersedia)")
        txt.setStyleSheet(
            "font-size: 13px; color: #2c3e50; background: #fafafa;"
            " border: 1px solid #dcdde1; border-radius: 6px; padding: 8px;"
        )
        layout.addWidget(txt)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_close = QPushButton("Tutup")
        btn_close.setFixedWidth(90)
        btn_close.setStyleSheet(
            "background:#2c3e50; color:white; border-radius:6px;"
            " padding:6px 12px; font-weight:bold;"
        )
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)


# ── PageDashboard ──────────────────────────────────────────────────

class PageDashboard:
    def __init__(self):
        self.ui     = load_ui('page_dashboard.ui')
        central     = self.ui.centralWidget()

        sidebar = central.findChild(QFrame, 'Sidebar')
        if sidebar:
            sidebar.hide()

        self.page = central

        # Simpan konten penuh: { row_index: konten_lengkap }
        self._full_content: dict[int, str] = {}

        # Referensi widget
        self.table           = self.page.findChild(QtWidgets.QTableWidget, 'tableWidget')
        self.lbl_val_artikel = self.page.findChild(QtWidgets.QLabel,       'label_val_artikel')
        self.lbl_val_portal  = self.page.findChild(QtWidgets.QLabel,       'label_val_portal')
        self.lbl_val_time    = self.page.findChild(QtWidgets.QLabel,       'label_val_time')
        self.lbl_date        = self.page.findChild(QtWidgets.QLabel,       'label_date')
        self.mini_val1       = self.page.findChild(QtWidgets.QLabel,       'miniVal1')
        self.mini_val2       = self.page.findChild(QtWidgets.QLabel,       'miniVal2')
        self.mini_val3       = self.page.findChild(QtWidgets.QLabel,       'miniVal3')
        self.combo_filter    = self.page.findChild(QtWidgets.QComboBox,    'comboBox_filter')

        self._setup_table()
        self._setup_date()
        self._setup_filter()

    # ── Setup ──────────────────────────────────────────────────────

    def _setup_table(self):
        hdr = self.table.horizontalHeader()

        # Pastikan tabel punya 4 kolom: Judul | Tanggal | Website | Konten
        if self.table.columnCount() < 4:
            self.table.setColumnCount(4)
            self.table.setHorizontalHeaderLabels(
                ["Judul", "Tanggal", "Website", "Konten"]
            )

        hdr.setSectionResizeMode(0, QHeaderView.Stretch)          # Judul
        hdr.setSectionResizeMode(1, QHeaderView.ResizeToContents) # Tanggal
        hdr.setSectionResizeMode(2, QHeaderView.ResizeToContents) # Website
        hdr.setSectionResizeMode(3, QHeaderView.Stretch)          # Konten

        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)

        # Double-click → popup konten penuh
        self.table.doubleClicked.connect(self._on_row_double_clicked)

    def _setup_date(self):
        today = QDate.currentDate()
        bulan = ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni",
                 "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
        if self.lbl_date:
            self.lbl_date.setText(
                f"📅  {today.day()} {bulan[today.month()]} {today.year()}"
            )

    def _setup_filter(self):
        if self.combo_filter:
            self.combo_filter.currentTextChanged.connect(self._on_filter_changed)

    # ── Public API ─────────────────────────────────────────────────

    def get_page(self):
        return self.page

    def add_row(self, judul: str, tanggal: str, website: str, konten: str = ""):
        """
        Tambah baris ke tabel Dashboard.
        konten: isi lengkap artikel (disimpan & ditampilkan sebagai preview 120 karakter)
        """
        row = self.table.rowCount()
        self.table.insertRow(row)

        konten_full    = konten
        konten_preview = konten_full[:120].replace("\n", " ")
        if len(konten_full) > 120:
            konten_preview += "…"

        judul_item   = QTableWidgetItem(judul)
        tanggal_item = QTableWidgetItem(tanggal)
        website_item = QTableWidgetItem(website)
        konten_item  = QTableWidgetItem(konten_preview)

        tanggal_item.setTextAlignment(Qt.AlignCenter)
        website_item.setTextAlignment(Qt.AlignCenter)
        konten_item.setToolTip("Double-klik untuk membaca selengkapnya")

        self.table.setItem(row, 0, judul_item)
        self.table.setItem(row, 1, tanggal_item)
        self.table.setItem(row, 2, website_item)
        self.table.setItem(row, 3, konten_item)

        self._full_content[row] = konten_full

    def clear_data(self):
        self.table.setRowCount(0)
        self._full_content.clear()

    def update_stats(self, total: int, portal: str, waktu: str):
        if self.lbl_val_artikel:
            self.lbl_val_artikel.setText(str(total))
        if self.lbl_val_portal:
            self.lbl_val_portal.setText(portal)
        if self.lbl_val_time:
            self.lbl_val_time.setText(waktu)

    def update_mini_cards(self, total_portal: int, hari_ini: int, status: str = "✔  Running"):
        if self.mini_val1:
            self.mini_val1.setText(f"🌐  {total_portal}")
        if self.mini_val2:
            self.mini_val2.setText(f"📄  {hari_ini}")
        if self.mini_val3:
            self.mini_val3.setText(status)

    def update_filter_options(self, portals: list):
        if not self.combo_filter:
            return
        self.combo_filter.blockSignals(True)
        self.combo_filter.clear()
        self.combo_filter.addItem("Semua Portal")
        self.combo_filter.addItems(portals)
        self.combo_filter.blockSignals(False)

    # ── Slot ───────────────────────────────────────────────────────

    def _on_filter_changed(self, text: str):
        keyword = "" if text == "Semua Portal" else text
        for row in range(self.table.rowCount()):
            match = any(
                self.table.item(row, col)
                and keyword.lower() in self.table.item(row, col).text().lower()
                for col in range(self.table.columnCount())
            )
            self.table.setRowHidden(row, not match if keyword else False)

    def _on_row_double_clicked(self, index: QtCore.QModelIndex):
        row = index.row()

        def cell(col):
            item = self.table.item(row, col)
            return item.text() if item else ""

        judul   = cell(0)
        tanggal = cell(1)
        website = cell(2)
        konten  = self._full_content.get(row, "")

        dlg = ArticleDialog(judul, tanggal, website, konten, parent=self.page)
        dlg.exec()