"""
Audio Player Module (Pygame Version)
Updated with Shuffle functionality.
"""

import pygame
import random
from PySide6.QtCore import QObject, Signal

class AudioPlayer(QObject):
    # Signals
    current_song_changed = Signal(object) 
    queue_changed = Signal(list)
    playback_state_changed = Signal(bool)

    def __init__(self):
        super().__init__()
        try:
            pygame.mixer.init(frequency=44100) 
        except Exception as e:
            print(f"Error initializing Pygame mixer: {e}")
            
        self.queue = []
        self.history = []
        self.current_song = None
        self.is_playing = False 
        self.is_paused = False
        self.current_pos_offset = 0.0 
        
        self.SONG_END = pygame.USEREVENT + 1
        pygame.mixer.music.set_endevent(self.SONG_END)

    def play_now(self, song):
        """Clears queue and plays a single song immediately."""
        self.stop()
        self.queue = []
        self.queue.append(song)
        self.play_next_from_queue()
        self.queue_changed.emit(self.queue)

    def play_list(self, songs, start_index=0):
        """
        Clears queue, adds a LIST of songs, and plays from start_index.
        This is used for "Play Album".
        """
        self.stop()
        self.queue = list(songs) # Make a copy
        
        # If start_index is > 0, we need to pop the first few
        # But usually for "Play Album", we start at 0.
        # If we want to play track 1 immediately:
        if self.queue:
            self.play_next_from_queue()
            
        self.queue_changed.emit(self.queue)

    def add_to_queue(self, song):
        self.queue.append(song)
        self.queue_changed.emit(self.queue)
        if not self.is_playing and not self.is_paused:
            self.play_next_from_queue()

    def shuffle_queue(self):
        """Shuffles the current queue."""
        random.shuffle(self.queue)
        self.queue_changed.emit(self.queue)

    def check_music_status(self):
        for event in pygame.event.get():
            if event.type == self.SONG_END:
                print("Song finished.")
                self.is_playing = False
                self.is_paused = False
                if self.current_song:
                    self.history.append(self.current_song)
                self.current_song = None
                self.current_song_changed.emit(None)
                self.play_next_from_queue()

    def play_next_from_queue(self):
        if self.is_playing: return
        if len(self.queue) == 0: return

        song = self.queue.pop(0)
        self.current_song = song
        
        try:
            pygame.mixer.music.load(song.filepath)
            self.current_pos_offset = 0.0
            pygame.mixer.music.play()
            song.play()
            self.is_playing = True
            self.is_paused = False
            
            self.current_song_changed.emit(self.current_song)
            self.queue_changed.emit(self.queue)
            self.playback_state_changed.emit(True)
        except Exception as e:
            print(f"Error: {e}")
            self.is_playing = False

    def toggle_playback(self):
        if not self.current_song: return
        if self.is_paused:
            pygame.mixer.music.unpause()
            self.is_paused = False
            self.is_playing = True
            self.playback_state_changed.emit(True)
        elif self.is_playing:
            pygame.mixer.music.pause()
            self.is_paused = True
            self.is_playing = False
            self.playback_state_changed.emit(False)

    def seek(self, seconds):
        if self.current_song:
            try:
                pygame.mixer.music.play(start=seconds)
                self.current_pos_offset = seconds
                self.is_playing = True
                self.is_paused = False
                self.playback_state_changed.emit(True)
            except Exception as e:
                print(f"Seek error: {e}")

    def get_current_position(self):
        if not self.current_song: return 0
        pygame_pos_seconds = pygame.mixer.music.get_pos() / 1000.0
        if pygame_pos_seconds < 0: return self.current_pos_offset
        return self.current_pos_offset + pygame_pos_seconds

    def skip_to_next(self):
        self.stop()
        if self.current_song: self.history.append(self.current_song)
        self.current_song = None
        self.play_next_from_queue()

    def play_previous_song(self):
        if len(self.history) == 0: return
        self.stop()
        if self.current_song: self.queue.insert(0, self.current_song)
        self.current_song = None
        prev_song = self.history.pop()
        self.queue.insert(0, prev_song)
        self.play_next_from_queue()

    def stop(self):
        pygame.mixer.music.stop()
        self.is_playing = False
        self.is_paused = False
        self.current_pos_offset = 0.0
        self.playback_state_changed.emit(False)