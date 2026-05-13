import sys
import yaml
import json
import math
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QGraphicsView, QGraphicsScene, 
                             QVBoxLayout, QHBoxLayout, QPushButton, QWidget, QFileDialog, 
                             QMessageBox, QTextEdit, QGridLayout)
from PyQt5.QtGui import QPixmap, QPen, QColor, QBrush, QFont, QPainter
from PyQt5.QtCore import Qt, QPointF

class ZoomPanGraphicsView(QGraphicsView):
    def __init__(self, parent_gui):
        super().__init__()
        self.gui = parent_gui
        self.setRenderHint(QPainter.Antialiasing)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.NoDrag) 
        
        self.is_panning = False
        self.last_mouse_pos = None

    def wheelEvent(self, event):
        zoom_in_factor = 1.15
        zoom_out_factor = 1 / zoom_in_factor
        if event.angleDelta().y() > 0:
            self.scale(zoom_in_factor, zoom_in_factor)
        else:
            self.scale(zoom_out_factor, zoom_out_factor)

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton or event.button() == Qt.MiddleButton:
            self.is_panning = True
            self.last_mouse_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
        elif event.button() == Qt.LeftButton and self.gui.select_mode:
            self.gui.start_waypoint(self.mapToScene(event.pos()))
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.is_panning and self.last_mouse_pos is not None:
            delta = event.pos() - self.last_mouse_pos
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            self.last_mouse_pos = event.pos()
        elif self.gui.select_mode and self.gui.is_dragging_yaw:
            self.gui.update_waypoint_yaw(self.mapToScene(event.pos()))
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.RightButton or event.button() == Qt.MiddleButton:
            self.is_panning = False
            self.setCursor(Qt.ArrowCursor)
        elif event.button() == Qt.LeftButton and self.gui.select_mode:
            self.gui.finalize_waypoint()
        super().mouseReleaseEvent(event)

class RouteToolGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AMR Route Planning Tool Pro (With Orientation)")
        self.setGeometry(100, 100, 1200, 800)

        self.map_image = None
        self.resolution = 0.05
        self.origin = [0.0, 0.0, 0.0]
        self.image_height = 0

        self.waypoints_pixel = []
        self.waypoints_ros = []
        self.drawn_items = []
        
        self.select_mode = True 
        
        self.is_dragging_yaw = False
        self.temp_pixel = None
        self.temp_ros_xy = None
        self.temp_yaw = 0.0

        self.initUI()

    def initUI(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        self.scene = QGraphicsScene()
        self.view = ZoomPanGraphicsView(self)
        self.view.setScene(self.scene)
        main_layout.addWidget(self.view, stretch=3)

        bottom_layout = QHBoxLayout()
        grid_layout = QGridLayout()
        
        self.btn_load = QPushButton("Load Map")
        self.btn_load.clicked.connect(self.load_map)
        
        self.btn_toggle_select = QPushButton("Select Point: ON")
        self.btn_toggle_select.setStyleSheet("background-color: lightgreen; font-weight: bold;")
        self.btn_toggle_select.clicked.connect(self.toggle_select_mode)

        self.btn_zoom_out = QPushButton("Zoom Out")
        self.btn_zoom_out.clicked.connect(lambda: self.view.scale(1/1.2, 1/1.2))
        self.btn_reset_zoom = QPushButton("Reset Zoom")
        self.btn_reset_zoom.clicked.connect(self.reset_zoom)
        self.btn_zoom_in = QPushButton("Zoom In")
        self.btn_zoom_in.clicked.connect(lambda: self.view.scale(1.2, 1.2))

        self.btn_save = QPushButton("Save Route")
        self.btn_save.clicked.connect(self.save_route)
        self.btn_delete_last = QPushButton("Delete Last Point")
        self.btn_delete_last.clicked.connect(self.delete_last_point)
        self.btn_clear = QPushButton("Clear")
        self.btn_clear.clicked.connect(self.clear_route)

        grid_layout.addWidget(self.btn_load, 0, 0)
        grid_layout.addWidget(self.btn_toggle_select, 0, 1, 1, 2)
        grid_layout.addWidget(self.btn_zoom_out, 1, 0)
        grid_layout.addWidget(self.btn_reset_zoom, 1, 1)
        grid_layout.addWidget(self.btn_zoom_in, 1, 2)
        grid_layout.addWidget(self.btn_save, 2, 0)
        grid_layout.addWidget(self.btn_delete_last, 2, 1)
        grid_layout.addWidget(self.btn_clear, 2, 2)

        bottom_layout.addLayout(grid_layout, stretch=1)

        self.info_box = QTextEdit()
        self.info_box.setReadOnly(True)
        self.info_box.setFont(QFont("Consolas", 10))
        self.info_box.setText("Hướng dẫn: Click chuột trái, giữ và kéo để tạo hướng (Yaw).")
        bottom_layout.addWidget(self.info_box, stretch=1)

        main_layout.addLayout(bottom_layout)

    def load_map(self):
        yaml_file, _ = QFileDialog.getOpenFileName(self, "Open Map YAML", "", "YAML Files (*.yaml)")
        if not yaml_file: return
        try:
            with open(yaml_file, 'r') as f:
                map_data = yaml.safe_load(f)
                self.resolution = map_data['resolution']
                self.origin = map_data['origin']
                image_name = map_data['image']

            map_dir = os.path.dirname(yaml_file)
            image_path = os.path.join(map_dir, image_name)

            self.map_image = QPixmap(image_path)
            self.image_height = self.map_image.height()
            
            self.scene.clear()
            self.scene.addPixmap(self.map_image)
            self.clear_route()
            self.reset_zoom()
            self.info_box.append(f"\n[Hệ thống] Đã load map thành công.\nRes: {self.resolution}m/px")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể đọc map:\n{str(e)}")

    def toggle_select_mode(self):
        self.select_mode = not self.select_mode
        if self.select_mode:
            self.btn_toggle_select.setText("Select Point: ON")
            self.btn_toggle_select.setStyleSheet("background-color: lightgreen; font-weight: bold;")
        else:
            self.btn_toggle_select.setText("Select Point: OFF")
            self.btn_toggle_select.setStyleSheet("background-color: lightcoral; font-weight: bold;")

    def start_waypoint(self, scene_pos):
        if self.map_image is None: return
        px, py = scene_pos.x(), scene_pos.y()
        
        if 0 <= px <= self.map_image.width() and 0 <= py <= self.image_height:
            self.is_dragging_yaw = True
            self.temp_pixel = (px, py)
            self.temp_yaw = 0.0
            
            ros_x = (px * self.resolution) + self.origin[0]
            ros_y = ((self.image_height - py) * self.resolution) + self.origin[1]
            self.temp_ros_xy = (ros_x, ros_y)
            
            self.draw_elements()

    def update_waypoint_yaw(self, scene_pos):
        if not self.is_dragging_yaw or self.temp_pixel is None: return
        
        dx = scene_pos.x() - self.temp_pixel[0]
        dy = scene_pos.y() - self.temp_pixel[1]
        
        if math.hypot(dx, dy) < 5: return 
        
        self.temp_yaw = math.atan2(-dy, dx)
        self.draw_elements()

    def finalize_waypoint(self):
        if not self.is_dragging_yaw or self.temp_pixel is None: return
        
        self.waypoints_pixel.append(self.temp_pixel)
        self.waypoints_ros.append({
            "x": round(self.temp_ros_xy[0], 3), 
            "y": round(self.temp_ros_xy[1], 3), 
            "yaw": round(self.temp_yaw, 3)
        })
        
        self.is_dragging_yaw = False
        self.temp_pixel = None
        self.temp_ros_xy = None
        
        self.draw_elements()
        self.update_info_box()

    def draw_elements(self):
        for item in self.drawn_items:
            self.scene.removeItem(item)
        self.drawn_items.clear()

        pen_line = QPen(QColor(0, 150, 255), 2, Qt.SolidLine)
        brush_dot = QBrush(QColor(255, 0, 0))

        # 1. Vẽ đường xanh nối
        for i in range(1, len(self.waypoints_pixel)):
            p1, p2 = self.waypoints_pixel[i-1], self.waypoints_pixel[i]
            line = self.scene.addLine(p1[0], p1[1], p2[0], p2[1], pen_line)
            self.drawn_items.append(line)

        # 2. Vẽ điểm, đánh số và vẽ MŨI TÊN
        for i, (px, py) in enumerate(self.waypoints_pixel):
            radius = 3 # Thu nhỏ điểm một chút cho hài hòa với mũi tên nhỏ
            dot = self.scene.addEllipse(px - radius, py - radius, radius*2, radius*2, pen_line, brush_dot)
            self.drawn_items.append(dot)
            
            # Text P1, P2... đã được giảm nhỏ (Font size 8) và dịch lại vị trí
            text = self.scene.addText(f"P{i+1}")
            text.setDefaultTextColor(QColor(255, 0, 0))
            text.setFont(QFont("Arial", 8, QFont.Bold)) 
            text.setPos(px + 4, py - 15) 
            self.drawn_items.append(text)
            
            yaw_ros = self.waypoints_ros[i]['yaw']
            self.draw_arrow(px, py, yaw_ros, QColor(255, 0, 0))

        # 3. Mũi tên tạm thời
        if self.is_dragging_yaw and self.temp_pixel:
            px, py = self.temp_pixel
            radius = 3
            temp_pen = QPen(QColor(0, 255, 0), 2, Qt.SolidLine)
            temp_brush = QBrush(QColor(0, 255, 0))
            
            dot = self.scene.addEllipse(px - radius, py - radius, radius*2, radius*2, temp_pen, temp_brush)
            self.drawn_items.append(dot)
            self.draw_arrow(px, py, self.temp_yaw, QColor(0, 200, 0))

    def draw_arrow(self, px, py, yaw_ros, color):
        pen = QPen(color, 2, Qt.SolidLine)
        L = 15 # Chiều dài thân mũi tên đã giảm đi một nửa
        
        end_x = px + L * math.cos(yaw_ros)
        end_y = py - L * math.sin(yaw_ros)
        
        line = self.scene.addLine(px, py, end_x, end_y, pen)
        self.drawn_items.append(line)

        head_L = 5 # Râu mũi tên đã giảm đi một nửa
        angle1 = yaw_ros + math.pi - math.pi/6
        angle2 = yaw_ros + math.pi + math.pi/6

        hx1 = end_x + head_L * math.cos(angle1)
        hy1 = end_y - head_L * math.sin(angle1)
        
        hx2 = end_x + head_L * math.cos(angle2)
        hy2 = end_y - head_L * math.sin(angle2)

        line1 = self.scene.addLine(end_x, end_y, hx1, hy1, pen)
        line2 = self.scene.addLine(end_x, end_y, hx2, hy2, pen)
        self.drawn_items.extend([line1, line2])

    def delete_last_point(self):
        if self.waypoints_pixel:
            self.waypoints_pixel.pop()
            self.waypoints_ros.pop()
            self.draw_elements()
            self.update_info_box()

    def clear_route(self):
        self.waypoints_pixel.clear()
        self.waypoints_ros.clear()
        self.draw_elements()
        self.update_info_box()

    def update_info_box(self):
        if not self.waypoints_ros:
            self.info_box.setText("Hướng dẫn: Click chuột trái, giữ và kéo để tạo hướng (Yaw).")
            return
        
        text_lines = []
        for i, pt in enumerate(self.waypoints_ros):
            text_lines.append(f"P{i+1}: x={pt['x']:.2f}, y={pt['y']:.2f}, yaw={pt['yaw']:.2f} rad")
        self.info_box.setText("\n".join(text_lines))
        self.info_box.verticalScrollBar().setValue(self.info_box.verticalScrollBar().maximum())

    def save_route(self):
        if not self.waypoints_ros:
            QMessageBox.warning(self, "Cảnh báo", "Không có điểm nào để lưu!")
            return
        save_path, _ = QFileDialog.getSaveFileName(self, "Save Route", "route_data.json", "JSON Files (*.json)")
        if save_path:
            with open(save_path, 'w') as f:
                json.dump(self.waypoints_ros, f, indent=4)
            QMessageBox.information(self, "Thành công", f"Đã lưu lộ trình vào:\n{save_path}")

    def reset_zoom(self):
        if self.map_image:
            self.view.resetTransform()
            self.view.fitInView(self.scene.itemsBoundingRect(), Qt.KeepAspectRatio)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = RouteToolGUI()
    window.show()
    sys.exit(app.exec_())