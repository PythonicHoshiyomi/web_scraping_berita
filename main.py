import sys
import csv
from datetime import datetime
from PySide6 import QtWidgets, QtCore

from UI.page_dashboard import PageDashboard
from UI.page_scrap     import PageScrap
from UI.page_about     import PageAbout
from scrap_code.scraper import (
    create_driver,
    normalize_url,
    is_likely_article_url,
    scrap_article,
    scrap_homepage,
)


# ── WORKER THREAD ─────────────────────────────────────────────────

class ScraperWorker(QtCore.QThread):
    progress_signal = QtCore.Signal(int)
    log_signal      = QtCore.Signal(str)
    data_signal     = QtCore.Signal(list)
    finished_signal = QtCore.Signal()

    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def run(self):
        driver = None
        try:
            url = normalize_url(self.url)
            if not url:
                self.log_signal.emit("[ERROR] URL tidak valid.")
                self.finished_signal.emit()
                return

            from urllib.parse import urlparse
            parsed_path = urlparse(url).path.strip("/")
            is_article  = is_likely_article_url(url) and parsed_path != ""

            total_berhasil = 0

            # ── Kasus 1: URL terlihat seperti artikel tunggal ──
            if is_article:
                self.log_signal.emit(
                    "[INFO] URL terdeteksi sebagai artikel tunggal, scraping langsung..."
                )
                result = scrap_article(url)
                if result:
                    total_berhasil = 1
                    self.log_signal.emit(f"[OK] {result['judul'][:80]}")
                    self.progress_signal.emit(100)
                    # Kirim konten LENGKAP (bukan [:300])
                    self.data_signal.emit([
                        1,
                        result["judul"],
                        result["tanggal"],
                        result["url"],
                        result["konten"],   # <-- konten penuh
                    ])
                else:
                    self.log_signal.emit(
                        "[WARN] Artikel tunggal tidak berhasil di-scrap, "
                        "mencoba sebagai homepage..."
                    )

            # ── Kasus 2: Homepage – cari dan scrap semua artikel ──
            if total_berhasil == 0:
                self.log_signal.emit(
                    "[INFO] Membuka browser (headless) untuk homepage..."
                )
                driver = create_driver()
                total_berhasil = scrap_homepage(
                    url=url,
                    driver=driver,
                    progress_callback=self.progress_signal.emit,
                    log_callback=self.log_signal.emit,
                    data_callback=self.data_signal.emit,
                    # data_callback menerima [no, judul, tanggal, url, konten_penuh]
                )

            # ── Kasus 3: Homepage tidak menghasilkan artikel, coba scrap URL itu sendiri ──
            if total_berhasil == 0 and not is_article:
                self.log_signal.emit("[INFO] Mencoba scraping URL secara langsung...")
                result = scrap_article(url)
                if result:
                    total_berhasil = 1
                    self.log_signal.emit(f"[OK] {result['judul'][:80]}")
                    self.progress_signal.emit(100)
                    self.data_signal.emit([
                        1,
                        result["judul"],
                        result["tanggal"],
                        result["url"],
                        result["konten"],   # <-- konten penuh
                    ])

            if total_berhasil == 0:
                self.log_signal.emit("[WARN] Tidak ada artikel yang berhasil di-scrap.")
            else:
                self.log_signal.emit(
                    f"[SUCCESS] Selesai! Total: {total_berhasil} artikel berhasil di-scrap."
                )

        except Exception as e:
            self.log_signal.emit(f"[ERROR] Terjadi kesalahan: {e}")
        finally:
            if driver:
                driver.quit()
                self.log_signal.emit("[INFO] Browser ditutup.")
            self.finished_signal.emit()


# ── MAIN WINDOW ───────────────────────────────────────────────────

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("News Scrapper")
        self.resize(912, 600)

        self.pg_dashboard = PageDashboard()
        self.pg_scrap     = PageScrap()
        self.pg_about     = PageAbout()

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        root = QtWidgets.QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ──
        header = QtWidgets.QFrame()
        header.setFixedHeight(60)
        header.setStyleSheet(
            "background-color: #F3A2BE; border-bottom: 1px solid #dcdde1;"
        )
        hl = QtWidgets.QHBoxLayout(header)
        hl.setContentsMargins(15, 0, 15, 0)
        hl.setSpacing(12)

        logo = QtWidgets.QLabel("\U0001F4F0")
        logo.setFixedSize(40, 40)
        logo.setAlignment(QtCore.Qt.AlignCenter)
        logo.setStyleSheet(
            "background-color:#2c3e50; border-radius:20px; font-size:20px;"
        )
        hl.addWidget(logo)

        lbl = QtWidgets.QLabel("NEWS SCRAPPER")
        lbl.setStyleSheet(
            "font-family:'Poppins'; font-size:22px; font-weight:bold;"
            " color:#2c3e50; letter-spacing:3px; background:transparent;"
        )
        hl.addWidget(lbl)
        hl.addStretch()
        root.addWidget(header)

        # ── Body ──
        body = QtWidgets.QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        # Sidebar
        sidebar = QtWidgets.QFrame()
        sidebar.setFixedWidth(140)
        sidebar.setStyleSheet("background-color: #81BFB7; border: none;")
        sb = QtWidgets.QVBoxLayout(sidebar)
        sb.setContentsMargins(8, 10, 8, 10)
        sb.setSpacing(8)

        btn_style = """
            QPushButton {
                background-color: #FFD3DD; color: #2c3e50; border-radius: 8px;
                padding: 10px; font-size: 13px; font-weight: bold;
                text-align: left; padding-left: 12px; border: none;
            }
            QPushButton:hover   { background-color: #4e6a85; color: white; }
            QPushButton:pressed { background-color: #2c3e50; color: white; }
            QPushButton:checked { background-color: #2c3e50; color: white; }
        """
        self.btn_dashboard = QtWidgets.QPushButton("📊  Dashboard")
        self.btn_scrap     = QtWidgets.QPushButton("⚡  Scrap")
        self.btn_about     = QtWidgets.QPushButton("ℹ️  About")
        for btn in [self.btn_dashboard, self.btn_scrap, self.btn_about]:
            btn.setStyleSheet(btn_style)
            btn.setCheckable(True)
            sb.addWidget(btn)
        sb.addStretch()
        body.addWidget(sidebar)

        # Stack
        self.stack = QtWidgets.QStackedWidget()
        self.stack.addWidget(self.pg_dashboard.get_page())
        self.stack.addWidget(self.pg_scrap.get_page())
        self.stack.addWidget(self.pg_about.get_page())
        body.addWidget(self.stack)
        root.addLayout(body)

        self._connect_signals()
        self.switch_page(0)

    def _connect_signals(self):
        self.btn_dashboard.clicked.connect(lambda: self.switch_page(0))
        self.btn_scrap.clicked.connect(lambda: self.switch_page(1))
        self.btn_about.clicked.connect(lambda: self.switch_page(2))
        self.pg_scrap.btnStart.clicked.connect(self.start_scraping)
        self.pg_scrap.btnExport.clicked.connect(self.export_csv)

    def switch_page(self, index: int):
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate([self.btn_dashboard, self.btn_scrap, self.btn_about]):
            btn.setChecked(i == index)

    # ── Scraping ──────────────────────────────────────────────────

    def start_scraping(self):
        url = self.pg_scrap.lineEdit.text().strip()
        if not url:
            QtWidgets.QMessageBox.warning(self, "Peringatan", "Masukan URL terlebih dahulu!")
            return

        # Reset UI
        self.pg_scrap.clear_data()
        self.pg_scrap.progressBar.setValue(0)
        self.pg_scrap.logEdit.clear()
        self.pg_scrap.btnStart.setEnabled(False)
        self.pg_scrap.btnStart.setText("Loading...")
        self.pg_scrap.btnExport.setEnabled(False)

        self.worker = ScraperWorker(url)
        self.worker.progress_signal.connect(self.pg_scrap.progressBar.setValue)
        self.worker.log_signal.connect(self._append_log)
        self.worker.data_signal.connect(self._add_row)
        self.worker.finished_signal.connect(self._on_finished)
        self.worker.start()

    def _append_log(self, msg: str):
        self.pg_scrap.logEdit.appendPlainText(msg)
        sb = self.pg_scrap.logEdit.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _add_row(self, data: list):
        """
        data = [no, judul, tanggal, url, konten_lengkap]
        Diteruskan ke page_scrap (tampilkan preview + simpan full)
        dan page_dashboard (tampilkan preview + simpan full).
        """
        # Page Scrap
        self.pg_scrap.add_row(data)

        # Page Dashboard — kirim konten penuh juga
        konten_full = str(data[4]) if len(data) > 4 else ""
        self.pg_dashboard.add_row(
            judul   = str(data[1]),
            tanggal = str(data[2]),
            website = self.pg_scrap.lineEdit.text(),
            konten  = konten_full,
        )

    def _on_finished(self):
        total = self.pg_scrap.table.rowCount()
        url   = self.pg_scrap.lineEdit.text()
        waktu = datetime.now().strftime("%d/%m/%Y %H:%M")

        self.pg_scrap.btnStart.setEnabled(True)
        self.pg_scrap.btnStart.setText("▶  Start")
        self.pg_scrap.btnExport.setEnabled(bool(total))

        self.pg_dashboard.update_stats(total=total, portal=url, waktu=waktu)
        self.pg_dashboard.update_mini_cards(total_portal=1, hari_ini=total)
        self.pg_dashboard.update_filter_options([url])

    # ── Export ────────────────────────────────────────────────────

    def export_csv(self):
        table = self.pg_scrap.table
        if table.rowCount() == 0:
            QtWidgets.QMessageBox.warning(self, "Peringatan", "Tidak ada data untuk diekspor!")
            return

        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Simpan CSV", "hasil_scraping.csv", "CSV Files (*.csv)"
        )
        if not path:
            return

        def cell(row, col):
            item = table.item(row, col)
            return item.text() if item else ""

        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)

                # Header selalu 5 kolom — apapun jumlah kolom di tabel UI
                writer.writerow(["No", "Judul", "Tanggal", "URL", "Konten"])

                for row in range(table.rowCount()):
                    # Konten penuh sudah ada langsung di sel tabel kolom 4
                    writer.writerow([cell(row, col) for col in range(table.columnCount())])

            QtWidgets.QMessageBox.information(
                self, "Sukses", f"Data berhasil diekspor ke:\n{path}"
            )
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Gagal ekspor:\n{e}")


# ── ENTRY POINT ───────────────────────────────────────────────────

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())