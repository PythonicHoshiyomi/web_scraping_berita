import sys
import csv
import time
from datetime import datetime
from PySide6 import QtWidgets, QtCore
import os

from page_dashboard import PageDashboard
from page_scrap     import PageScrap
from page_about     import PageAbout

# ── WORKER THREAD (Selenium) ─────────────────────────────────────
class ScraperWorker(QtCore.QThread):
    progress_signal = QtCore.Signal(int)
    log_signal      = QtCore.Signal(str)
    data_signal     = QtCore.Signal(list)
    finished_signal = QtCore.Signal()

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        driver = None
        try:
            options = Options()
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

            self.log_signal.emit("[INFO] Membuka browser (headless)...")
            driver = webdriver.Chrome(options=options)

            self.log_signal.emit(f"[INFO] Mengakses URL: {self.url}")
            driver.get(self.url)

            self.log_signal.emit("[INFO] Menunggu halaman selesai dimuat...")
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            self.log_signal.emit("[INFO] Mencari elemen artikel...")

            # TODO: ganti selector sesuai website target
            articles = driver.find_elements(By.CSS_SELECTOR, "article")

            if not articles:
                self.log_signal.emit("[WARNING] Tidak ada artikel ditemukan. Cek selectornya!")
                self.finished_signal.emit()
                return

            self.log_signal.emit(f"[INFO] Menemukan {len(articles)} artikel...")
            total = len(articles)

            for i, article in enumerate(articles):
                try:
                    try:
                        judul = article.find_element(By.CSS_SELECTOR, "h2, h3, .title, .headline").text.strip()
                    except:
                        judul = "Judul tidak ditemukan"
                    try:
                        tanggal = article.find_element(By.CSS_SELECTOR, "time, .date, .pubdate").text.strip()
                        if not tanggal:
                            tanggal = article.find_element(By.CSS_SELECTOR, "time").get_attribute("datetime")[:10]
                    except:
                        tanggal = "-"
                    try:
                        ringkasan = article.find_element(By.CSS_SELECTOR, "p, .desc, .summary, .excerpt").text.strip()
                        ringkasan = ringkasan[:150] + "..." if len(ringkasan) > 150 else ringkasan
                    except:
                        ringkasan = "-"

                    if not judul or judul == "Judul tidak ditemukan":
                        continue

                    row = [str(i + 1), judul, tanggal, ringkasan]
                    self.log_signal.emit(f"[INFO] Scraping artikel {i+1}/{total}: {judul[:40]}...")
                    self.progress_signal.emit(int((i + 1) / total * 100))
                    self.data_signal.emit(row)

                except Exception as e:
                    self.log_signal.emit(f"[WARNING] Skip artikel {i+1}: {str(e)[:50]}")
                    continue

            self.log_signal.emit(f"[SUCCESS] Selesai! Total: {total} artikel.")

        except Exception as e:
            self.log_signal.emit(f"[ERROR] {str(e)}")
        finally:
            if driver:
                driver.quit()
                self.log_signal.emit("[INFO] Browser ditutup.")
            self.finished_signal.emit()


# ── MAIN WINDOW ──────────────────────────────────────────────────
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("News Scrapper")
        self.resize(912, 600)

        # Inisialisasi halaman
        self.pg_dashboard = PageDashboard()
        self.pg_scrap     = PageScrap()
        self.pg_about     = PageAbout()

        # ── Layout utama ──
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        root = QtWidgets.QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        header = QtWidgets.QFrame()
        header.setFixedHeight(60)
        header.setStyleSheet("background-color: #F3A2BE; border-bottom: 1px solid #dcdde1;")
        hl = QtWidgets.QHBoxLayout(header)
        hl.setContentsMargins(15, 0, 15, 0)
        hl.setSpacing(12)
        logo = QtWidgets.QLabel("\U0001F4F0")
        logo.setFixedSize(40, 40)
        logo.setAlignment(QtCore.Qt.AlignCenter)
        logo.setStyleSheet("background-color:#2c3e50; border-radius:20px; font-size:20px;")
        hl.addWidget(logo)
        lbl = QtWidgets.QLabel("NEWS SCRAPPER")
        lbl.setStyleSheet("font-family:'Poppins'; font-size:22px; font-weight:bold; color:#2c3e50; letter-spacing:3px; background:transparent;")
        hl.addWidget(lbl)
        hl.addStretch()
        root.addWidget(header)

        # Body
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
            QPushButton { background-color:#FFD3DD; color:#2c3e50; border-radius:8px;
                padding:10px; font-size:13px; font-weight:bold; text-align:left;
                padding-left:12px; border:none; }
            QPushButton:hover   { background-color:#4e6a85; color:white; }
            QPushButton:pressed { background-color:#2c3e50; color:white; }
            QPushButton:checked { background-color:#2c3e50; color:white; }
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

    def switch_page(self, index):
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate([self.btn_dashboard, self.btn_scrap, self.btn_about]):
            btn.setChecked(i == index)

    def start_scraping(self):
        url = self.pg_scrap.lineEdit.text().strip()
        if not url:
            QtWidgets.QMessageBox.warning(self, "Peringatan", "Masukan URL terlebih dahulu!")
            return
        self.pg_scrap.table.setRowCount(0)
        self.pg_scrap.progressBar.setValue(0)
        self.pg_scrap.logEdit.clear()
        self.pg_scrap.btnStart.setEnabled(False)
        self.pg_scrap.btnStart.setText("Loading...")
        self.pg_scrap.btnExport.setEnabled(False)

        self.worker = ScraperWorker(url)
        self.worker.progress_signal.connect(self.pg_scrap.progressBar.setValue)
        self.worker.log_signal.connect(self.append_log)
        self.worker.data_signal.connect(self.add_row)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.start()

    def append_log(self, msg):
        self.pg_scrap.logEdit.appendPlainText(msg)
        self.pg_scrap.logEdit.verticalScrollBar().setValue(
            self.pg_scrap.logEdit.verticalScrollBar().maximum()
        )

    def add_row(self, data):
        # Tambah ke tabel Scrap
        row = self.pg_scrap.table.rowCount()
        self.pg_scrap.table.insertRow(row)
        for col, val in enumerate(data):
            item = QtWidgets.QTableWidgetItem(str(val))
            if col in [0, 2]:
                item.setTextAlignment(QtCore.Qt.AlignCenter)
            self.pg_scrap.table.setItem(row, col, item)

        # Sync ke Dashboard
        self.pg_dashboard.add_row(
            judul   = data[1],
            tanggal = data[2],
            website = self.pg_scrap.lineEdit.text()
        )

    def on_finished(self):
        total = self.pg_scrap.table.rowCount()
        url   = self.pg_scrap.lineEdit.text()
        waktu = datetime.now().strftime("%d/%m/%Y %H:%M")

        self.pg_scrap.btnStart.setEnabled(True)
        self.pg_scrap.btnStart.setText("▶  Start")
        self.pg_scrap.btnExport.setEnabled(True)

        self.pg_dashboard.update_stats(
            total  = total,
            portal = url,
            waktu  = waktu
        )
        self.pg_dashboard.update_mini_cards(
            total_portal = 1,
            hari_ini     = total
        )
        self.pg_dashboard.update_filter_options([url])

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
        try:
            with open(path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                headers = [table.horizontalHeaderItem(c).text() for c in range(table.columnCount())]
                writer.writerow(headers)
                for row in range(table.rowCount()):
                    rowdata = [table.item(row, col).text() if table.item(row, col) else ""
                               for col in range(table.columnCount())]
                    writer.writerow(rowdata)
            QtWidgets.QMessageBox.information(self, "Sukses", f"Data berhasil diekspor ke:\n{path}")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Gagal ekspor:\n{str(e)}")


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
