# dashboard_window.py
# Khusus menangani logika tampilan Dashboard (ui_Dashboard_v2.ui)

from PySide6.QtWidgets import (
    QMainWindow, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor

# Import hasil compile dari file .ui
# Jalankan dulu: pyside6-uic ui_Dashboard_v2.ui -o ui_dashboard_v2.py
from ui_dashboard_v2 import Ui_MainWindow


class DashboardWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Setup UI dari file .ui
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # Inisialisasi komponen dashboard
        self._setup_table()
        self._setup_stats()
        self._setup_date()
        self._setup_filter()

    # ─────────────────────────────────────────
    #  TABLE
    # ─────────────────────────────────────────
    def _setup_table(self):
        """Konfigurasi ukuran kolom tabel agar memenuhi lebar."""
        header = self.ui.tableWidget.horizontalHeader()

        # Kolom Judul — stretch memenuhi sisa ruang
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        # Kolom Tanggal & Website — sesuai konten
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)

    def populate_table(self, data: list[dict]):
        """
        Isi tabel dengan data dari luar (dipanggil setelah scraping selesai).

        Parameter:
            data: list of dict, contoh:
            [
                {"judul": "Judul Artikel", "tanggal": "06 Mar 2026", "website": "Kompas.com"},
                ...
            ]
        """
        self.ui.tableWidget.setRowCount(0)  # Kosongkan dulu

        for row_idx, item in enumerate(data):
            self.ui.tableWidget.insertRow(row_idx)

            judul   = QTableWidgetItem(item.get("judul", ""))
            tanggal = QTableWidgetItem(item.get("tanggal", ""))
            website = QTableWidgetItem(item.get("website", ""))

            # Rata tengah untuk kolom Tanggal dan Website
            tanggal.setTextAlignment(Qt.AlignCenter)
            website.setTextAlignment(Qt.AlignCenter)

            self.ui.tableWidget.setItem(row_idx, 0, judul)
            self.ui.tableWidget.setItem(row_idx, 1, tanggal)
            self.ui.tableWidget.setItem(row_idx, 2, website)

    def filter_table(self, keyword: str):
        """Sembunyikan baris yang tidak cocok dengan keyword."""
        for row in range(self.ui.tableWidget.rowCount()):
            match = False
            for col in range(self.ui.tableWidget.columnCount()):
                item = self.ui.tableWidget.item(row, col)
                if item and keyword.lower() in item.text().lower():
                    match = True
                    break
            self.ui.tableWidget.setRowHidden(row, not match)

    # ─────────────────────────────────────────
    #  STAT CARDS
    # ─────────────────────────────────────────
    def _setup_stats(self):
        """Set nilai awal stat cards (bisa diupdate dari luar)."""
        self.update_stats(total_artikel=0, portal_terakhir="-", waktu_terakhir="-")

    def update_stats(self, total_artikel: int, portal_terakhir: str, waktu_terakhir: str):
        """
        Update nilai di stat cards.

        Dipanggil dari main.py setelah scraping selesai, contoh:
            self.dashboard.update_stats(
                total_artikel=1284,
                portal_terakhir="Kompas.com",
                waktu_terakhir="10:42 AM"
            )
        """
        self.ui.label_val_artikel.setText(f"{total_artikel:,}")
        self.ui.label_val_portal.setText(portal_terakhir)
        self.ui.label_val_time.setText(waktu_terakhir)

    def update_mini_cards(self, total_portal: int, hari_ini: int, status: str = "Running"):
        """Update mini cards di sidebar (Total Portal, Hari Ini, Status)."""
        self.ui.miniValue1.setText(str(total_portal))
        self.ui.miniValue2.setText(str(hari_ini))
        self.ui.miniValue3.setText(status)

    # ─────────────────────────────────────────
    #  DATE
    # ─────────────────────────────────────────
    def _setup_date(self):
        """Tampilkan tanggal hari ini di header."""
        today = QDate.currentDate()
        bulan = [
            "", "Januari", "Februari", "Maret", "April", "Mei", "Juni",
            "Juli", "Agustus", "September", "Oktober", "November", "Desember"
        ]
        tgl_str = f"📅  {today.day()} {bulan[today.month()]} {today.year()}"
        self.ui.label_date.setText(tgl_str)

    # ─────────────────────────────────────────
    #  FILTER COMBOBOX
    # ─────────────────────────────────────────
    def _setup_filter(self):
        """Hubungkan comboBox filter ke fungsi filter tabel."""
        self.ui.comboBox_filter.currentTextChanged.connect(self._on_filter_changed)

    def _on_filter_changed(self, text: str):
        """Dipanggil otomatis saat dropdown filter berubah."""
        if text == "Semua Portal":
            self.filter_table("")
        else:
            self.filter_table(text)

    def update_filter_options(self, portals: list[str]):
        """
        Update opsi dropdown filter sesuai portal yang tersedia.

        Dipanggil dari main.py setelah scraping, contoh:
            self.dashboard.update_filter_options(["Kompas.com", "Detik.com"])
        """
        self.ui.comboBox_filter.blockSignals(True)
        self.ui.comboBox_filter.clear()
        self.ui.comboBox_filter.addItem("Semua Portal")
        self.ui.comboBox_filter.addItems(portals)
        self.ui.comboBox_filter.blockSignals(False)
