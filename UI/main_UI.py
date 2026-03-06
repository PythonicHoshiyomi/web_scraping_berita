# main.py
# Entry point utama — menghubungkan Dashboard, Scrap, dan About
# Sidebar pushButton / pushButton_2 / pushButton_3 mengontrol halaman mana yang tampil

import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QStackedWidget
from PySide6.QtCore import Qt

# Import UI dashboard (hasil compile dari .ui)
from ui_dashboard_v2 import Ui_MainWindow

# Import logika tiap halaman
from dashboard_window import DashboardWindow

# ── Placeholder pages (ganti dengan file aslimu nanti) ──────────────────────
# Kalau sudah punya ui_Scrap.ui dan ui_About.ui, uncomment dan sesuaikan:
# from scrap_window import ScrapWindow
# from about_window import AboutWindow

# Untuk sekarang pakai widget kosong dulu sebagai placeholder
from PySide6.QtWidgets import QLabel, QVBoxLayout


def make_placeholder(text: str, bg: str = "#C6E6E3") -> QWidget:
    """Buat halaman placeholder sementara."""
    page = QWidget()
    page.setStyleSheet(f"background-color: {bg};")
    layout = QVBoxLayout(page)
    layout.setAlignment(Qt.AlignCenter)
    label = QLabel(text)
    label.setStyleSheet("font-size: 20px; font-weight: bold; color: #2c3e50;")
    label.setAlignment(Qt.AlignCenter)
    layout.addWidget(label)
    return page


# ─────────────────────────────────────────────────────────────────────────────
class MainApp(QMainWindow):
    """
    Window utama yang mengelola navigasi antar halaman.
    Sidebar dari ui_Dashboard_v2 dipakai sebagai navigasi global.
    """

    def __init__(self):
        super().__init__()

        # ── Setup UI utama (header + sidebar dari dashboard) ──────────────
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # ── Buat QStackedWidget sebagai kontainer halaman ─────────────────
        # QStackedWidget ditaruh di area content (menggantikan contentArea)
        self.stack = QStackedWidget()

        # Ambil layout body, ganti contentArea dengan stack
        body_layout = self.ui.bodyLayout
        # Hapus widget contentArea lama (index 1 = content, index 0 = sidebar)
        old_content = body_layout.itemAt(1).widget()
        if old_content:
            body_layout.removeWidget(old_content)
            old_content.deleteLater()
        body_layout.addWidget(self.stack)

        # ── Buat halaman-halaman ──────────────────────────────────────────
        self.page_dashboard = self._build_dashboard_page()
        self.page_scrap     = make_placeholder("⚡  Halaman Scrap\n(belum diimplementasi)", "#FFF0F4")
        self.page_about     = make_placeholder("ℹ️  Halaman About\n(belum diimplementasi)", "#F0F9F8")

        # Tambahkan ke stack
        self.stack.addWidget(self.page_dashboard)   # index 0
        self.stack.addWidget(self.page_scrap)        # index 1
        self.stack.addWidget(self.page_about)        # index 2

        # Tampilkan dashboard sebagai halaman awal
        self.stack.setCurrentIndex(0)

        # ── Hubungkan tombol sidebar ke navigasi ──────────────────────────
        self.ui.pushButton.clicked.connect(lambda: self._navigate(0))
        self.ui.pushButton_2.clicked.connect(lambda: self._navigate(1))
        self.ui.pushButton_3.clicked.connect(lambda: self._navigate(2))

        # Set status bar
        self.ui.statusbar.showMessage("Siap  |  News Scrapper v1.0.0")

    # ─────────────────────────────────────────
    #  BUILD PAGES
    # ─────────────────────────────────────────
    def _build_dashboard_page(self) -> QWidget:
        """
        Bangun halaman dashboard.
        Ambil contentArea dari DashboardWindow dan pakai sebagai halaman.
        """
        # Buat instance dashboard (tidak ditampilkan sebagai window terpisah)
        self._dashboard_ctrl = DashboardWindow.__new__(DashboardWindow)
        QMainWindow.__init__(self._dashboard_ctrl)
        self._dashboard_ctrl.ui = Ui_MainWindow()

        # Kita hanya butuh widget contentArea-nya
        from PySide6.QtWidgets import QWidget, QVBoxLayout
        from PySide6.QtCore import QDate

        page = QWidget()
        page.setStyleSheet("background-color: #C6E6E3;")

        # Re-use dashboard_window logic tapi dalam widget biasa
        # Cara paling bersih: langsung pakai DashboardContent sebagai QWidget
        return page

    # ─────────────────────────────────────────
    #  NAVIGASI
    # ─────────────────────────────────────────
    def _navigate(self, index: int):
        """Pindah halaman dan update style tombol aktif di sidebar."""
        self.stack.setCurrentIndex(index)
        self._update_sidebar_style(index)

    def _update_sidebar_style(self, active_index: int):
        """
        Update tampilan tombol sidebar:
        - Tombol aktif  → background gelap (#2c3e50), teks putih
        - Tombol lainnya → background pink (#FFD3DD), teks gelap
        """
        buttons = [
            self.ui.pushButton,    # index 0 = Dashboard
            self.ui.pushButton_2,  # index 1 = Scrap
            self.ui.pushButton_3,  # index 2 = About
        ]

        active_style = """
            QPushButton {
                background-color: #2c3e50;
                color: #ffffff;
                border-radius: 6px;
                padding: 8px 10px;
                font-size: 13px;
                font-weight: 600;
                font-family: "Poppins", "Segoe UI";
                text-align: left;
                border: none;
            }
            QPushButton:hover { background-color: #3d5166; }
            QPushButton:pressed { background-color: #1a252f; }
        """

        inactive_style = """
            QPushButton {
                background-color: #FFD3DD;
                color: #2c3e50;
                border-radius: 6px;
                padding: 8px 10px;
                font-size: 13px;
                font-weight: 500;
                font-family: "Poppins", "Segoe UI";
                text-align: left;
                border: none;
            }
            QPushButton:hover { background-color: #ffc0d0; }
            QPushButton:pressed { background-color: #f0a0b8; }
        """

        for i, btn in enumerate(buttons):
            btn.setStyleSheet(active_style if i == active_index else inactive_style)


# ─────────────────────────────────────────────────────────────────────────────
#  VERSI SEDERHANA — pakai DashboardWindow langsung sebagai main window
#  (uncomment blok ini kalau cuma mau test dashboard saja tanpa navigasi)
# ─────────────────────────────────────────────────────────────────────────────
#
# def main():
#     app = QApplication(sys.argv)
#     window = DashboardWindow()
#     window.show()
#     sys.exit(app.exec())


# ─────────────────────────────────────────────────────────────────────────────
#  VERSI LENGKAP — dengan navigasi sidebar ke Scrap dan About
# ─────────────────────────────────────────────────────────────────────────────
def main():
    app = QApplication(sys.argv)
    window = MainApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
