"""
GUI Main Program (Album Play/Shuffle Edition)
"""
import sys
import os
import pygame 
import random
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QListWidget, QPushButton, QLabel, QFrame, QTableWidget, QTableWidgetItem, 
    QHeaderView, QSlider, QAbstractItemView, QStackedWidget, QLineEdit, 
    QDialog, QFormLayout, QFileDialog, QScrollArea, QGridLayout,
    QListWidgetItem
)
from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QColor, QBrush, QIcon, QPixmap

from music_library import MusicLibrary, _format_duration
from player import (load_songs_from_file, save_songs_to_file)
from audio_player import AudioPlayer

# --- Dialog (Unchanged) ---
class AddSongDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Song")
        self.resize(450, 400)
        self.setStyleSheet("""
            QDialog { background-color: #192734; color: white; font-family: 'Segoe UI'; }
            QLabel { font-weight: bold; font-size: 13px; color: #B0C0D0; }
            QLineEdit { background-color: #22303C; border: 1px solid #38444D; border-radius: 4px; padding: 6px; color: white; }
            QPushButton { background-color: #2C3E50; color: #B0C0D0; border: none; padding: 6px 12px; border-radius: 4px; }
            QPushButton:hover { background-color: #38444D; color: white; }
        """)
        layout = QFormLayout(self)
        layout.setSpacing(15)
        
        self.title_edit = QLineEdit()
        self.artist_edit = QLineEdit()
        self.album_edit = QLineEdit()
        self.track_edit = QLineEdit()
        self.genre_edit = QLineEdit()
        self.duration_edit = QLineEdit()
        self.file_path_edit = QLineEdit()
        self.img_path_edit = QLineEdit()
        
        self.btn_browse_file = QPushButton("Browse...")
        self.btn_browse_file.clicked.connect(self.browse_audio)
        self.btn_browse_img = QPushButton("Browse...")
        self.btn_browse_img.clicked.connect(self.browse_img)
        
        layout.addRow("Audio File:", self.create_file_row(self.file_path_edit, self.btn_browse_file))
        layout.addRow("Title:", self.title_edit)
        layout.addRow("Artist:", self.artist_edit)
        layout.addRow("Album:", self.album_edit)
        layout.addRow("Track #:", self.track_edit)
        layout.addRow("Genre:", self.genre_edit)
        layout.addRow("Duration (s):", self.duration_edit)
        layout.addRow("Album Art:", self.create_file_row(self.img_path_edit, self.btn_browse_img))
        
        self.btn_save = QPushButton("Save Song")
        self.btn_save.setStyleSheet("background-color: #1db954; color: #000000; font-weight: bold; padding: 10px;")
        self.btn_save.clicked.connect(self.accept)
        layout.addRow(self.btn_save)

    def create_file_row(self, line_edit, button):
        w = QWidget(); l = QHBoxLayout(w); l.setContentsMargins(0,0,0,0)
        l.addWidget(line_edit); l.addWidget(button); return w

    def browse_audio(self):
        f, _ = QFileDialog.getOpenFileName(self, "Select Audio", "", "Audio Files (*.mp3 *.wav)")
        if f: 
            self.file_path_edit.setText(f)
            try:
                if not self.title_edit.text():
                    filename = os.path.splitext(os.path.basename(f))[0]
                    parts = filename.split(' ', 1)
                    if len(parts) > 1 and parts[0].isdigit():
                        self.track_edit.setText(parts[0])
                        self.title_edit.setText(parts[1])
                    else:
                        self.title_edit.setText(filename)
                sound = pygame.mixer.Sound(f)
                self.duration_edit.setText(str(int(sound.get_length())))
            except: pass

    def browse_img(self):
        f, _ = QFileDialog.getOpenFileName(self, "Select Art", "", "Images (*.png *.jpg)")
        if f: self.img_path_edit.setText(f)

    def get_data(self):
        return (self.title_edit.text(), self.artist_edit.text(), self.album_edit.text(), self.track_edit.text(), self.duration_edit.text(), self.genre_edit.text(), self.file_path_edit.text(), self.img_path_edit.text())

class MainWindow(QMainWindow):
    def __init__(self, library, player):
        super().__init__()
        self.library = library
        self.player = player
        self.is_dragging_slider = False 
        self.current_view_songs = [] # Track songs currently in the table for Play/Shuffle buttons
        
        self.setWindowTitle("Musicify")
        self.resize(1200, 800)

        self.setup_ui()
        self.apply_gentle_blue_theme()
        self.connect_signals()
        
        self.show_all_songs_view()
        self.refresh_album_view()
        
        self.playback_timer = QTimer(self)
        self.playback_timer.timeout.connect(self.update_ui_timer) 
        self.playback_timer.start(100) 

    def setup_ui(self):
        self.main_container = QWidget()
        self.setCentralWidget(self.main_container)
        self.main_layout = QVBoxLayout(self.main_container)
        self.main_layout.setContentsMargins(0, 0, 0, 0); self.main_layout.setSpacing(0)

        self.middle_frame = QWidget()
        self.middle_layout = QHBoxLayout(self.middle_frame)
        self.middle_layout.setContentsMargins(10, 10, 10, 0); self.middle_layout.setSpacing(10)

        self.setup_left_sidebar()
        self.setup_center_content()
        self.setup_right_sidebar()

        self.middle_layout.addWidget(self.left_sidebar, 20)
        self.middle_layout.addWidget(self.center_stack, 60)
        self.middle_layout.addWidget(self.right_sidebar, 20)

        self.setup_bottom_bar()
        self.main_layout.addWidget(self.middle_frame)
        self.main_layout.addWidget(self.bottom_bar)

    def setup_left_sidebar(self):
        self.left_sidebar = QFrame()
        self.left_sidebar.setObjectName("Sidebar")
        layout = QVBoxLayout(self.left_sidebar)
        layout.setContentsMargins(15, 20, 15, 20); layout.setSpacing(10)
        
        self.btn_library = QPushButton("All Songs")
        self.btn_albums = QPushButton("Albums")
        self.btn_add_song = QPushButton("+ Add New Song")
        
        layout.addWidget(self.btn_library); layout.addWidget(self.btn_albums)
        layout.addStretch(); layout.addWidget(self.btn_add_song)

    def setup_center_content(self):
        self.center_stack = QStackedWidget()
        
        # --- Page 1: Library (Table View) ---
        self.page_library = QFrame()
        self.page_library.setObjectName("CenterPanel")
        lib_layout = QVBoxLayout(self.page_library)
        lib_layout.setContentsMargins(0, 0, 0, 0)

        # Header
        self.header_frame = QFrame()
        self.header_frame.setObjectName("HeaderFrame")
        self.header_frame.setFixedHeight(140) # Taller for buttons
        header_layout = QVBoxLayout(self.header_frame)
        header_layout.setContentsMargins(20, 20, 20, 15)
        
        # Title Row
        self.lbl_page_title = QLabel("All Songs")
        self.lbl_page_title.setObjectName("PageTitle")
        header_layout.addWidget(self.lbl_page_title)
        
        # Buttons Row (Play Album / Shuffle)
        self.header_controls = QWidget()
        hc_layout = QHBoxLayout(self.header_controls)
        hc_layout.setContentsMargins(0, 10, 0, 0); hc_layout.setSpacing(15)
        
        self.btn_play_album = QPushButton("▶") # Green Circle Play
        self.btn_play_album.setObjectName("AlbumPlayButton")
        self.btn_play_album.setFixedSize(48, 48)
        self.btn_play_album.setCursor(Qt.PointingHandCursor)
        
        self.btn_shuffle_album = QPushButton("🔀") # Shuffle Icon
        self.btn_shuffle_album.setObjectName("AlbumShuffleButton")
        self.btn_shuffle_album.setFixedSize(32, 32)
        self.btn_shuffle_album.setCursor(Qt.PointingHandCursor)
        
        hc_layout.addWidget(self.btn_play_album)
        hc_layout.addWidget(self.btn_shuffle_album)
        hc_layout.addStretch()
        
        header_layout.addWidget(self.header_controls)

        # Table
        self.song_table = QTableWidget()
        self.song_table.setColumnCount(5) 
        self.song_table.setHorizontalHeaderLabels(["#", "Title", "Artist", "Album", "🕒"])
        self.song_table.setShowGrid(False)
        self.song_table.verticalHeader().setVisible(False)
        self.song_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.song_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.song_table.setFocusPolicy(Qt.NoFocus)
        self.song_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed); self.song_table.setColumnWidth(0, 40)
        self.song_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.song_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.song_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.song_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Fixed); self.song_table.setColumnWidth(4, 60)

        lib_layout.addWidget(self.header_frame)
        lib_layout.addWidget(self.song_table)
        
        # --- Page 2: Albums Grid ---
        self.page_albums = QFrame()
        self.page_albums.setObjectName("CenterPanel")
        alb_layout = QVBoxLayout(self.page_albums)
        lbl_alb_header = QLabel("Albums"); lbl_alb_header.setStyleSheet("font-size: 32px; font-weight: bold; color: white; margin: 20px;")
        alb_layout.addWidget(lbl_alb_header)
        self.album_list_widget = QListWidget()
        self.album_list_widget.setViewMode(QListWidget.IconMode)
        self.album_list_widget.setIconSize(QSize(140, 140))
        self.album_list_widget.setResizeMode(QListWidget.Adjust)
        self.album_list_widget.setSpacing(20)
        alb_layout.addWidget(self.album_list_widget)
        
        self.center_stack.addWidget(self.page_library)
        self.center_stack.addWidget(self.page_albums)

    def setup_right_sidebar(self):
        self.right_sidebar = QFrame()
        self.right_sidebar.setObjectName("Sidebar")
        layout = QVBoxLayout(self.right_sidebar)
        layout.setContentsMargins(15, 20, 15, 20)
        lbl_queue = QLabel("Up Next"); lbl_queue.setObjectName("HeaderLabel")
        self.queue_list = QListWidget()
        self.btn_clear_queue = QPushButton("Clear Queue")
        layout.addWidget(lbl_queue); layout.addWidget(self.queue_list); layout.addWidget(self.btn_clear_queue)

    def setup_bottom_bar(self):
        self.bottom_bar = QFrame(); self.bottom_bar.setObjectName("BottomBar"); self.bottom_bar.setFixedHeight(100)
        layout = QHBoxLayout(self.bottom_bar); layout.setContentsMargins(20, 5, 20, 5)

        # Info
        info_w = QWidget(); info_l = QHBoxLayout(info_w); info_l.setContentsMargins(0,0,0,0)
        self.lbl_art = QLabel(); self.lbl_art.setFixedSize(60, 60); self.lbl_art.setStyleSheet("background-color: #333; border-radius: 4px;"); self.lbl_art.setScaledContents(True)
        txt_w = QWidget(); txt_l = QVBoxLayout(txt_w); txt_l.setAlignment(Qt.AlignmentFlag.AlignVCenter); txt_l.setSpacing(2)
        self.lbl_now_title = QLabel("Select a song"); self.lbl_now_title.setObjectName("NowPlayingTitle")
        self.lbl_now_artist = QLabel(""); self.lbl_now_artist.setObjectName("NowPlayingArtist")
        txt_l.addWidget(self.lbl_now_title); txt_l.addWidget(self.lbl_now_artist)
        info_l.addWidget(self.lbl_art); info_l.addWidget(txt_w); info_l.addStretch()
        
        # Controls
        ctrl_w = QWidget(); ctrl_l = QVBoxLayout(ctrl_w); ctrl_l.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btns_row = QWidget(); btns_l = QHBoxLayout(btns_row); btns_l.setSpacing(15)
        self.btn_prev = QPushButton("⏮"); self.btn_play = QPushButton("▶"); self.btn_play.setObjectName("PlayButton"); self.btn_play.setFixedSize(38, 38); self.btn_skip = QPushButton("⏭")
        btns_l.addWidget(self.btn_prev); btns_l.addWidget(self.btn_play); btns_l.addWidget(self.btn_skip)
        slider_row = QWidget(); sl_l = QHBoxLayout(slider_row)
        self.lbl_curr_time = QLabel("0:00"); self.lbl_curr_time.setObjectName("TimeLabel")
        self.seek_slider = QSlider(Qt.Horizontal); self.seek_slider.setCursor(Qt.PointingHandCursor)
        self.lbl_total_time = QLabel("0:00"); self.lbl_total_time.setObjectName("TimeLabel")
        sl_l.addWidget(self.lbl_curr_time); sl_l.addWidget(self.seek_slider); sl_l.addWidget(self.lbl_total_time)
        ctrl_l.addWidget(btns_row); ctrl_l.addWidget(slider_row)

        # Actions
        act_w = QWidget(); act_l = QHBoxLayout(act_w); act_l.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.btn_add_queue = QPushButton("+ Queue"); self.btn_add_queue.setFixedWidth(80)
        act_l.addWidget(self.btn_add_queue)

        layout.addWidget(info_w, 30); layout.addWidget(ctrl_w, 40); layout.addWidget(act_w, 30)

    def apply_gentle_blue_theme(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #0F171E; }
            QWidget { font-family: 'Segoe UI', sans-serif; }
            #Sidebar, #CenterPanel { background-color: #141E26; border-radius: 10px; border: 1px solid #1E2A36; }
            #BottomBar { background-color: #0F171E; border-top: 1px solid #1E2A36; }
            #HeaderFrame { background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1, stop:0 #1E2A36, stop:1 #141E26); border-top-left-radius: 10px; border-top-right-radius: 10px; }
            QLabel { color: #B0C0D0; }
            #HeaderLabel { color: #6B7D8C; font-weight: bold; font-size: 11px; letter-spacing: 1px; text-transform: uppercase;}
            #PageTitle { font-size: 36px; font-weight: bold; color: #FFFFFF; }
            #NowPlayingTitle { font-size: 14px; font-weight: bold; color: #FFFFFF; }
            #NowPlayingArtist { font-size: 12px; color: #88CCF1; }
            #TimeLabel { font-size: 11px; color: #6B7D8C; min-width: 30px; }
            QPushButton { background-color: transparent; color: #B0C0D0; border: none; font-size: 14px; font-weight: 600; padding: 10px; text-align: left; border-radius: 5px; }
            QPushButton:hover { background-color: rgba(255, 255, 255, 0.05); color: #FFFFFF; }
            QPushButton[text="+ Add New Song"] { color: #88CCF1; }
            #PlayButton { background-color: #FFFFFF; color: #0F171E; border-radius: 19px; font-size: 16px; padding: 0px; text-align: center; }
            #PlayButton:hover { background-color: #E0E0E0; }
            QPushButton[text="⏮"], QPushButton[text="⏭"] { color: #FFFFFF; font-size: 18px; text-align: center; padding: 0px; }
            #AlbumPlayButton { background-color: #1db954; color: black; border-radius: 24px; font-size: 24px; padding-bottom: 3px;}
            #AlbumPlayButton:hover { background-color: #1ed760; transform: scale(1.05); }
            #AlbumShuffleButton { color: #B0C0D0; font-size: 20px; }
            #AlbumShuffleButton:hover { color: white; }
            QTableWidget, QListWidget { background-color: transparent; border: none; color: #B0C0D0; font-size: 13px; outline: none; }
            QTableWidget::item { padding: 5px; }
            QTableWidget::item:selected, QListWidget::item:selected { background-color: rgba(136, 204, 241, 0.15); color: #88CCF1; }
            QHeaderView::section { background-color: transparent; color: #6B7D8C; border: none; border-bottom: 1px solid #22303C; padding: 5px; font-weight: bold; }
            QSlider::groove:horizontal { border: none; height: 4px; background: #2C3E50; border-radius: 2px; }
            QSlider::sub-page:horizontal { background: #88CCF1; border-radius: 2px; }
            QSlider::handle:horizontal { background: #FFFFFF; width: 10px; height: 10px; margin: -3px 0; border-radius: 5px; }
        """)

    def connect_signals(self):
        self.btn_library.clicked.connect(self.show_all_songs_view)
        self.btn_albums.clicked.connect(lambda: self.center_stack.setCurrentIndex(1))
        self.btn_add_song.clicked.connect(self.open_add_song_dialog)

        self.btn_play.clicked.connect(self.toggle_play_logic)
        self.btn_skip.clicked.connect(self.player.skip_to_next)
        self.btn_prev.clicked.connect(self.player.play_previous_song)
        self.btn_clear_queue.clicked.connect(self.player.stop)
        self.btn_add_queue.clicked.connect(self.add_table_selection_to_queue)
        
        # Header Buttons
        self.btn_play_album.clicked.connect(self.play_current_view)
        self.btn_shuffle_album.clicked.connect(self.shuffle_current_view)

        self.song_table.cellDoubleClicked.connect(self.on_table_double_click)
        self.album_list_widget.itemDoubleClicked.connect(self.on_album_double_click)

        self.seek_slider.sliderPressed.connect(self.on_slider_pressed)
        self.seek_slider.sliderReleased.connect(self.on_slider_released)

        self.player.current_song_changed.connect(self.update_now_playing_ui)
        self.player.queue_changed.connect(self.update_queue_ui)
        self.player.playback_state_changed.connect(self.update_play_button_icon)

    # --- Logic ---

    def open_add_song_dialog(self):
        dialog = AddSongDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            try:
                dur = int(data[4])
                track = int(data[3]) if data[3] else 0
                self.library.add_song(data[0], data[1], data[2], track, dur, data[5], data[6], data[7])
                if self.lbl_page_title.text() == "All Songs":
                    self.refresh_library_view()
                self.refresh_album_view()
                save_songs_to_file(self.library)
            except ValueError: print("Invalid Number")

    def update_ui_timer(self):
        self.player.check_music_status()
        if self.player.is_playing and self.player.current_song and not self.is_dragging_slider:
            pos = self.player.get_current_position() 
            total = self.player.current_song.duration
            if total > 0:
                self.seek_slider.setRange(0, total)
                self.seek_slider.setValue(int(pos))
                self.lbl_curr_time.setText(_format_duration(pos))
                self.lbl_total_time.setText(_format_duration(total))

    def on_slider_pressed(self): self.is_dragging_slider = True
    def on_slider_released(self):
        self.player.seek(self.seek_slider.value())
        self.is_dragging_slider = False

    def toggle_play_logic(self):
        if self.player.current_song: self.player.toggle_playback()
        elif self.song_table.rowCount() > 0: self.on_table_double_click(0, 0)

    def update_play_button_icon(self, is_playing):
        self.btn_play.setText("||" if is_playing else "▶")
        # Also update the big header button
        self.btn_play_album.setText("||" if is_playing else "▶")

    def show_all_songs_view(self):
        self.lbl_page_title.setText("All Songs")
        self.refresh_library_view(None)
        self.center_stack.setCurrentIndex(0)

    def refresh_library_view(self, songs_to_display=None):
        self.song_table.setRowCount(0)
        if songs_to_display is None:
            songs = self.library.get_sorted_song_list()
        else:
            songs = songs_to_display
            
        # Store current view for play/shuffle buttons
        self.current_view_songs = songs 
            
        self.song_table.setRowCount(len(songs))
        for row, song in enumerate(songs):
            track_item = QTableWidgetItem(str(song.track_number))
            track_item.setData(Qt.ItemDataRole.UserRole, song)
            track_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            title_item = QTableWidgetItem(song.title)
            title_item.setForeground(QBrush(QColor("#E3F2FD")))
            self.song_table.setItem(row, 0, track_item)
            self.song_table.setItem(row, 1, title_item)
            self.song_table.setItem(row, 2, QTableWidgetItem(song.artist))
            self.song_table.setItem(row, 3, QTableWidgetItem(song.album))
            self.song_table.setItem(row, 4, QTableWidgetItem(_format_duration(song.duration)))

    def refresh_album_view(self):
        self.album_list_widget.clear()
        albums = self.library.get_songs_by_album()
        for album_name, songs in albums.items():
            art_path = songs[0].image_path if songs else ""
            item = QListWidgetItem(album_name)
            if os.path.exists(art_path): item.setIcon(QIcon(art_path))
            item.setData(Qt.ItemDataRole.UserRole, songs)
            self.album_list_widget.addItem(item)

    def on_album_double_click(self, item):
        songs = item.data(Qt.ItemDataRole.UserRole)
        if songs:
            self.lbl_page_title.setText(item.text())
            self.refresh_library_view(songs)
            self.center_stack.setCurrentIndex(0)

    # --- NEW: Play Current View Logic ---
    def play_current_view(self):
        """Plays the songs currently visible in the table."""
        if self.current_view_songs:
            self.player.play_list(self.current_view_songs)

    def shuffle_current_view(self):
        """Plays the songs currently visible, but shuffled."""
        if self.current_view_songs:
            # Copy list so we don't mess up the table order
            shuffled = list(self.current_view_songs)
            import random
            random.shuffle(shuffled)
            self.player.play_list(shuffled)

    def get_song_from_table_row(self, row):
        return self.song_table.item(row, 0).data(Qt.ItemDataRole.UserRole)

    def on_table_double_click(self, row, col):
        song = self.get_song_from_table_row(row)
        if song: self.player.play_now(song)

    def add_table_selection_to_queue(self):
        row = self.song_table.currentRow()
        if row >= 0:
            song = self.get_song_from_table_row(row)
            if song: self.player.add_to_queue(song)

    def update_now_playing_ui(self, song):
        if song:
            self.lbl_now_title.setText(song.title)
            self.lbl_now_artist.setText(song.artist)
            self.lbl_total_time.setText(_format_duration(song.duration))
            self.btn_play.setText("||") 
            if os.path.exists(song.image_path): self.lbl_art.setPixmap(QPixmap(song.image_path))
            else: self.lbl_art.clear()
        else:
            self.lbl_now_title.setText("Select a song")
            self.lbl_now_artist.setText("")
            self.lbl_curr_time.setText("0:00")
            self.lbl_total_time.setText("0:00")
            self.seek_slider.setValue(0)
            self.btn_play.setText("▶")
            self.lbl_art.clear()

    def update_queue_ui(self, queue):
        self.queue_list.clear()
        for song in queue:
            self.queue_list.addItem(f"{song.title} • {song.artist}")

    def closeEvent(self, event):
        print(save_songs_to_file(self.library))
        event.accept()

def main():
    app = QApplication(sys.argv)
    library = MusicLibrary()
    load_songs_from_file(library)
    player = AudioPlayer()
    window = MainWindow(library, player)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()