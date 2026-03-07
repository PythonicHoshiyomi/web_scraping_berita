from PySide6 import QtWidgets, QtUiTools, QtCore
from PySide6.QtWidgets import QHeaderView, QTableWidgetItem, QDialog, QVBoxLayout, QLabel, QTextEdit, QPushButton, QHBoxLayout
from PySide6.QtCore import QFile, Qt
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

    def __init__(self, judul: str, tanggal: str, url: str, konten: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Detail Artikel")
        self.resize(700, 500)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # Judul
        lbl_judul = QLabel(judul)
        lbl_judul.setWordWrap(True)
        lbl_judul.setStyleSheet(
            "font-size: 15px; font-weight: bold; color: #2c3e50;"
        )
        layout.addWidget(lbl_judul)

        # Meta: tanggal & URL
        meta = f"🗓  {tanggal}    🔗  {url}" if tanggal else f"🔗  {url}"
        lbl_meta = QLabel(meta)
        lbl_meta.setWordWrap(True)
        lbl_meta.setStyleSheet("font-size: 11px; color: #7f8c8d;")
        layout.addWidget(lbl_meta)

        # Garis pemisah
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setStyleSheet("color: #dcdde1;")
        layout.addWidget(line)

        # Konten
        txt = QTextEdit()
        txt.setReadOnly(True)
        txt.setPlainText(konten if konten else "(Konten tidak tersedia)")
        txt.setStyleSheet(
            "font-size: 13px; color: #2c3e50; background: #fafafa;"
            " border: 1px solid #dcdde1; border-radius: 6px; padding: 8px;"
        )
        layout.addWidget(txt)

        # Tombol tutup
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


# ── PageScrap ──────────────────────────────────────────────────────

class PageScrap:
    def __init__(self):
        self.ui = load_ui('page_scrap.ui')
        central = self.ui.centralWidget()
        from PySide6.QtWidgets import QFrame
        sidebar = central.findChild(QFrame, 'Sidebar')
        if sidebar:
            sidebar.hide()
        self.page = central

        # Simpan juga di _full_content untuk popup double-click: { row_index: konten_lengkap }
        self._full_content: dict[int, str] = {}

        # Referensi widget
        self.table       = self.page.findChild(QtWidgets.QTableWidget,   'tableWidget')
        self.lineEdit    = self.page.findChild(QtWidgets.QLineEdit,      'lineEdit')
        self.progressBar = self.page.findChild(QtWidgets.QProgressBar,   'progressBar')
        self.logEdit     = self.page.findChild(QtWidgets.QPlainTextEdit, 'plainTextEdit')
        self.btnStart    = self.page.findChild(QtWidgets.QPushButton,    'pushButton_4')
        self.btnExport   = self.page.findChild(QtWidgets.QPushButton,    'btn_export')

        self._setup_table()

    # ── Setup ──────────────────────────────────────────────────────

    def _setup_table(self):
        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.Fixed)    # No
        hdr.setSectionResizeMode(1, QHeaderView.Stretch)  # Judul
        hdr.setSectionResizeMode(2, QHeaderView.Fixed)    # Tanggal
        hdr.setSectionResizeMode(3, QHeaderView.Stretch)  # URL
        hdr.setSectionResizeMode(4, QHeaderView.Stretch)  # Konten Preview
        self.table.setColumnWidth(0, 40)
        self.table.setColumnWidth(2, 110)
        self.table.verticalHeader().setVisible(False)
        self.table.setWordWrap(False)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)

        # Double-click → popup konten penuh
        self.table.doubleClicked.connect(self._on_row_double_clicked)

        tip_item = self.table.horizontalHeaderItem(4)
        if tip_item:
            tip_item.setToolTip("Double-klik baris untuk membaca isi lengkap artikel")

    # ── Public API ─────────────────────────────────────────────────

    def add_row(self, data: list):
        """
        data = [no, judul, tanggal, url, konten_lengkap]
        Konten penuh langsung disimpan di sel tabel (tidak dipotong).
        """
        row = self.table.rowCount()
        self.table.insertRow(row)

        konten_full = str(data[4]) if len(data) > 4 else ""

        values = [
            str(data[0]),   # No
            str(data[1]),   # Judul
            str(data[2]),   # Tanggal
            str(data[3]),   # URL
            konten_full,    # Konten penuh
        ]

        for col, val in enumerate(values):
            item = QTableWidgetItem(val)
            if col in (0, 2):
                item.setTextAlignment(Qt.AlignCenter)
            if col == 4:
                item.setToolTip("Double-klik untuk membaca selengkapnya")
            self.table.setItem(row, col, item)

        # Simpan juga di _full_content untuk popup double-click
        self._full_content[row] = konten_full

    def clear_data(self):
        self.table.setRowCount(0)
        self._full_content.clear()

    def get_page(self):
        return self.page

    # ── Slot ───────────────────────────────────────────────────────

    def _on_row_double_clicked(self, index: QtCore.QModelIndex):
        row = index.row()

        def cell(col):
            item = self.table.item(row, col)
            return item.text() if item else ""

        judul   = cell(1)
        tanggal = cell(2)
        url     = cell(3)
        konten  = self._full_content.get(row, "")

        dlg = ArticleDialog(judul, tanggal, url, konten, parent=self.page)
        dlg.exec()