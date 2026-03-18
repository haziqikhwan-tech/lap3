import sys
import pandas as pd
import numpy as np
import folium
import json
import io
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QFileDialog, QLabel, 
                             QLineEdit, QCheckBox, QFrame, QMessageBox)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from pyproj import Transformer

class SurveyDesktopApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sistem Survey Lot PUO - Desktop Version")
        self.setGeometry(100, 100, 1200, 800)
        
        # Simpan data
        self.df = None
        self.epsg = "4390"
        
        self.init_ui()

    def init_ui(self):
        # Main Widget & Layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)

        # --- SIDEBAR (Panel Kawalan) ---
        sidebar = QFrame()
        sidebar.setFixedWidth(300)
        sidebar.setStyleSheet("background-color: #f0f0f0; border-right: 1px solid #ccc;")
        sidebar_layout = QVBoxLayout(sidebar)

        sidebar_layout.addWidget(QLabel("<h2>SURVEY PUO</h2>"))
        sidebar_layout.addWidget(QLabel("Unit Geomatik"))
        
        # Input EPSG
        sidebar_layout.addWidget(QLabel("Kod EPSG:"))
        self.txt_epsg = QLineEdit("4390")
        sidebar_layout.addWidget(self.txt_epsg)

        # Butang Upload
        self.btn_upload = QPushButton("📂 Muat Naik CSV")
        self.btn_upload.setFixedHeight(40)
        self.btn_upload.clicked.connect(self.load_csv)
        sidebar_layout.addWidget(self.btn_upload)

        sidebar_layout.addSpacing(20)
        sidebar_layout.addWidget(QLabel("<b>Kawalan Paparan:</b>"))
        
        self.chk_sat = QCheckBox("Imej Satelit", checked=True)
        self.chk_points = QCheckBox("Paparkan Titik", checked=True)
        self.chk_label = QCheckBox("No Stesen", checked=True)
        
        for chk in [self.chk_sat, self.chk_points, self.chk_label]:
            sidebar_layout.addWidget(chk)

        sidebar_layout.addStretch()

        # Panel Analisis
        self.lbl_analysis = QLabel("📊 Keputusan Analisis:\n-\n-")
        sidebar_layout.addWidget(self.lbl_analysis)

        # Butang Export
        self.btn_export = QPushButton("📥 Export GeoJSON")
        self.btn_export.setEnabled(False)
        self.btn_export.clicked.connect(self.export_geojson)
        sidebar_layout.addWidget(self.btn_export)

        # --- MAP AREA ---
        self.web_view = QWebEngineView()
        # Set default map (Empty)
        self.update_map_display(folium.Map(location=[4.6, 101.1], zoom_start=6))

        # Add to main layout
        layout.addWidget(sidebar)
        layout.addWidget(self.web_view)

    def decimal_to_dms(self, deg):
        d = int(deg)
        m = int((deg - d) * 60)
        s = int(round((deg - d - m/60) * 3600))
        if s >= 60: s = 0; m += 1
        if m >= 60: m = 0; d += 1
        return f"{d}°{m:02d}'{s:02d}\""

    def load_csv(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Buka Fail CSV", "", "CSV Files (*csv)")
        if file_path:
            try:
                self.df = pd.read_csv(file_path)
                self.df.columns = self.df.columns.str.strip().str.upper()
                self.process_data()
                self.btn_export.setEnabled(True)
            except Exception as e:
                QMessageBox.critical(self, "Ralat", f"Gagal memproses fail: {e}")

    def process_data(self):
        epsg_val = self.txt_epsg.text()
        transformer = Transformer.from_crs(f"EPSG:{epsg_val}", "EPSG:4326", always_xy=True)
        self.df['lon'], self.df['lat'] = transformer.transform(self.df['E'].values, self.df['N'].values)

        center_lat, center_lon = self.df['lat'].mean(), self.df['lon'].mean()
        
        # Bina Folium Map
        m = folium.Map(location=[center_lat, center_lon], zoom_start=19)
        
        if self.chk_sat.isChecked():
            folium.TileLayer(
                tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}',
                attr='Google Satellite', name='Google Satellite'
            ).add_to(m)

        points_list = []
        total_dist = 0
        
        for i in range(len(self.df)):
            p1 = self.df.iloc[i]
            p2 = self.df.iloc[(i + 1) % len(self.df)]
            loc1 = [p1['lat'], p1['lon']]
            points_list.append(loc1)
            
            # Kira Jarak/Bearing (Simulasi mudah)
            dN, dE = p2['N'] - p1['N'], p2['E'] - p1['E']
            dist = np.sqrt(dN**2 + dE**2)
            total_dist += dist
            
            if self.chk_points.isChecked():
                folium.CircleMarker(loc1, radius=5, color='red', fill=True).add_to(m)
            
            if self.chk_label.isChecked():
                folium.Marker(loc1, icon=folium.DivIcon(html=f"<b>{int(p1['STN'])}</b>")).add_to(m)

        # Lukis Poligon
        folium.Polygon(points_list, color="cyan", weight=3, fill=True, fill_opacity=0.3).add_to(m)

        # Update Analysis Text
        area_m2 = 0.5 * np.abs(np.dot(self.df['E'], np.roll(self.df['N'], 1)) - np.dot(self.df['N'], np.roll(self.df['E'], 1)))
        self.lbl_analysis.setText(f"📊 Analisis:\nLuas: {area_m2:.2f} m²\nPerimeter: {total_dist:.2f} m")

        self.update_map_display(m)

    def update_map_display(self, m):
        data = io.BytesIO()
        m.save(data, close=False)
        self.web_view.setHtml(data.getvalue().decode())

    def export_geojson(self):
        # Logik export diletakkan di sini (sama seperti versi web)
        QMessageBox.information(self, "Export", "Fungsi GeoJSON sedia untuk disimpan.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SurveyDesktopApp()
    window.show()
    sys.exit(app.exec())
