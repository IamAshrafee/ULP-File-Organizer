import sys
import os
import re
import threading
import time
from datetime import datetime
from collections import defaultdict
from urllib.parse import urlparse

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QTextEdit, 
                             QFileDialog, QProgressBar, QGroupBox, QGridLayout,
                             QMessageBox, QSpinBox, QCheckBox)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QFont, QPalette, QColor


class SignalEmitter(QObject):
    """Custom signal emitter for thread-safe GUI updates"""
    update_progress = pyqtSignal(int, int, int, int)
    update_log = pyqtSignal(str, str, str)
    processing_complete = pyqtSignal()
    error_occurred = pyqtSignal(str)


class ULPValidator:
    """Handles ULP validation logic"""
    
    @staticmethod
    def validate_line(line, line_num):
        """Validate a single ULP line - only check for exactly 3 parts separated by colons"""
        line = line.strip()
        
        # Check for empty line
        if not line:
            return False, "Empty Line", line
        
        # Check if line has exactly 3 parts separated by colons
        parts = line.split(':', 2)  # Split into max 3 parts
        if len(parts) != 3:
            return False, "Not Enough Parts", line
        
        # All validation passed
        return True, "Valid", line


class FileProcessor:
    """Handles file processing in a separate thread"""
    
    def __init__(self, master_file, target_file, logs_folder, signal_emitter):
        self.master_file = master_file
        self.target_file = target_file
        self.logs_folder = logs_folder
        self.signal_emitter = signal_emitter
        
        self.is_running = False
        self.is_paused = False
        self.lock = threading.Lock()
        
        # Statistics
        self.total_lines = 0
        self.processed_lines = 0
        self.valid_lines = 0
        self.rejected_lines = 0
        
        # Log files dictionary
        self.log_files = {}
        
    def initialize_logs(self):
        """Initialize log files for different rejection reasons"""
        log_reasons = [
            "Not Enough Parts",
            "Empty Line",
            "Duplicate"
        ]
        
        # Create logs directory if it doesn't exist
        if not os.path.exists(self.logs_folder):
            os.makedirs(self.logs_folder)
        
        # Create log files for each reason
        for reason in log_reasons:
            log_file = os.path.join(self.logs_folder, f"{reason}.txt")
            self.log_files[reason] = open(log_file, 'w', encoding='utf-8')
    
    def close_logs(self):
        """Close all log files"""
        for log_file in self.log_files.values():
            log_file.close()
    
    def log_rejection(self, reason, line_num, line_content):
        """Log a rejected line to the appropriate file"""
        if reason in self.log_files:
            self.log_files[reason].write(f"Line {line_num}: {line_content}\n")
    
    def process_files(self):
        """Main processing method to be run in a separate thread"""
        try:
            # Initialize processing state
            with self.lock:
                self.is_running = True
                self.is_paused = False
            
            # Count total lines in target file
            with open(self.target_file, 'r', encoding='utf-8', errors='ignore') as f:
                self.total_lines = sum(1 for _ in f)
            
            # Initialize logs
            self.initialize_logs()
            
            # Read existing master file lines to check for duplicates
            existing_lines = set()
            if os.path.exists(self.master_file):
                with open(self.master_file, 'r', encoding='utf-8', errors='ignore') as f:
                    existing_lines = set(line.strip() for line in f)
            
            # Open master file for appending
            master_fd = open(self.master_file, 'a', encoding='utf-8')
            
            # Process target file line by line
            with open(self.target_file, 'r', encoding='utf-8', errors='ignore') as target_f:
                line_num = 0
                
                for line in target_f:
                    line_num += 1
                    
                    # Check if we should pause or stop
                    with self.lock:
                        if not self.is_running:
                            break
                        
                        while self.is_paused and self.is_running:
                            time.sleep(0.1)  # Sleep while paused
                    
                    # Validate the line
                    is_valid, reason, clean_line = ULPValidator.validate_line(line, line_num)
                    
                    if is_valid:
                        # Check for duplicates
                        if clean_line in existing_lines:
                            self.log_rejection("Duplicate", line_num, clean_line)
                            self.rejected_lines += 1
                        else:
                            # Write to master file
                            master_fd.write(clean_line + '\n')
                            master_fd.flush()  # Ensure immediate write
                            existing_lines.add(clean_line)
                            self.valid_lines += 1
                    else:
                        # Log rejection
                        self.log_rejection(reason, line_num, clean_line)
                        self.rejected_lines += 1
                    
                    # Update progress
                    self.processed_lines = line_num
                    
                    # Emit progress signal (throttled to avoid GUI lag)
                    if line_num % 100 == 0 or line_num == self.total_lines:
                        self.signal_emitter.update_progress.emit(
                            self.total_lines, 
                            self.processed_lines, 
                            self.valid_lines, 
                            self.rejected_lines
                        )
            
            # Close files
            master_fd.close()
            self.close_logs()
            
            # Final progress update
            self.signal_emitter.update_progress.emit(
                self.total_lines, 
                self.processed_lines, 
                self.valid_lines, 
                self.rejected_lines
            )
            
            # Signal completion
            self.signal_emitter.processing_complete.emit()
            
        except Exception as e:
            self.signal_emitter.error_occurred.emit(str(e))
        
        finally:
            with self.lock:
                self.is_running = False
    
    def pause(self):
        """Pause processing"""
        with self.lock:
            self.is_paused = True
    
    def resume(self):
        """Resume processing"""
        with self.lock:
            self.is_paused = False
    
    def stop(self):
        """Stop processing"""
        with self.lock:
            self.is_running = False


class ULPValidatorApp(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ULP Validator")
        self.setGeometry(100, 100, 800, 600)
        
        # Initialize variables
        self.master_file = ""
        self.target_file = ""
        self.logs_base_folder = "Logs"
        self.current_logs_folder = ""
        
        # File processor
        self.processor = None
        self.process_thread = None
        
        # Signal emitter
        self.signal_emitter = SignalEmitter()
        self.signal_emitter.update_progress.connect(self.update_progress)
        self.signal_emitter.update_log.connect(self.update_log)
        self.signal_emitter.processing_complete.connect(self.processing_complete)
        self.signal_emitter.error_occurred.connect(self.handle_error)
        
        # Setup UI
        self.setup_ui()
        
        # Load previous file paths if available
        self.load_settings()
    
    def setup_ui(self):
        """Setup the user interface"""
        # Central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # File selection group
        file_group = QGroupBox("File Selection")
        file_layout = QGridLayout(file_group)
        
        # Master file selection
        self.master_label = QLabel("Master File: Not selected")
        self.master_btn = QPushButton("Select Master File")
        self.master_btn.clicked.connect(self.select_master_file)
        file_layout.addWidget(QLabel("Master File:"), 0, 0)
        file_layout.addWidget(self.master_label, 0, 1)
        file_layout.addWidget(self.master_btn, 0, 2)
        
        # Target file selection
        self.target_label = QLabel("Target File: Not selected")
        self.target_btn = QPushButton("Select Target File")
        self.target_btn.clicked.connect(self.select_target_file)
        file_layout.addWidget(QLabel("Target File:"), 1, 0)
        file_layout.addWidget(self.target_label, 1, 1)
        file_layout.addWidget(self.target_btn, 1, 2)
        
        main_layout.addWidget(file_group)
        
        # Progress group
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)
        
        # Stats labels
        stats_layout = QHBoxLayout()
        self.total_label = QLabel("Total: 0")
        self.processed_label = QLabel("Processed: 0")
        self.valid_label = QLabel("Valid: 0")
        self.rejected_label = QLabel("Rejected: 0")
        
        stats_layout.addWidget(self.total_label)
        stats_layout.addWidget(self.processed_label)
        stats_layout.addWidget(self.valid_label)
        stats_layout.addWidget(self.rejected_label)
        
        progress_layout.addLayout(stats_layout)
        main_layout.addWidget(progress_group)
        
        # Control buttons
        control_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("Start")
        self.start_btn.clicked.connect(self.start_processing)
        self.start_btn.setEnabled(False)
        
        self.pause_btn = QPushButton("Pause")
        self.pause_btn.clicked.connect(self.toggle_pause)
        self.pause_btn.setEnabled(False)
        
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.stop_processing)
        self.stop_btn.setEnabled(False)
        
        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.pause_btn)
        control_layout.addWidget(self.stop_btn)
        
        main_layout.addLayout(control_layout)
        
        # Log display
        log_group = QGroupBox("Log")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        
        main_layout.addWidget(log_group)
        
        # Set styles
        self.apply_styles()
    
    def apply_styles(self):
        """Apply modern styling to the UI"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                background-color: #4CAF50;
                border: none;
                color: white;
                padding: 8px 16px;
                text-align: center;
                text-decoration: none;
                font-size: 14px;
                margin: 4px 2px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
            QPushButton:pressed {
                background-color: #367c39;
            }
            QLabel {
                padding: 4px;
            }
            QProgressBar {
                border: 1px solid #cccccc;
                border-radius: 4px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                width: 10px;
            }
            QTextEdit {
                border: 1px solid #cccccc;
                border-radius: 4px;
                font-family: monospace;
            }
        """)
    
    def select_master_file(self):
        """Select the master file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Master File", "", "Text Files (*.txt);;All Files (*)"
        )
        
        if file_path:
            self.master_file = file_path
            self.master_label.setText(f"Master File: {os.path.basename(file_path)}")
            self.save_settings()
            self.check_files_selected()
    
    def select_target_file(self):
        """Select the target file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Target File", "", "Text Files (*.txt);;All Files (*)"
        )
        
        if file_path:
            self.target_file = file_path
            self.target_label.setText(f"Target File: {os.path.basename(file_path)}")
            self.save_settings()
            self.check_files_selected()
    
    def check_files_selected(self):
        """Enable start button if both files are selected"""
        if self.master_file and self.target_file:
            self.start_btn.setEnabled(True)
        else:
            self.start_btn.setEnabled(False)
    
    def create_logs_folder(self):
        """Create a logs folder with current timestamp"""
        timestamp = datetime.now().strftime("%d-%m-%Y %I-%M-%S %p")
        self.current_logs_folder = os.path.join(self.logs_base_folder, timestamp)
        os.makedirs(self.current_logs_folder, exist_ok=True)
    
    def start_processing(self):
        """Start processing the files"""
        # Create logs folder
        self.create_logs_folder()
        
        # Initialize processor
        self.processor = FileProcessor(
            self.master_file, 
            self.target_file, 
            self.current_logs_folder,
            self.signal_emitter
        )
        
        # Create and start processing thread
        self.process_thread = threading.Thread(target=self.processor.process_files)
        self.process_thread.daemon = True
        self.process_thread.start()
        
        # Update UI state
        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        self.master_btn.setEnabled(False)
        self.target_btn.setEnabled(False)
        
        # Log start
        self.log_text.append(f"Processing started at {datetime.now().strftime('%H:%M:%S')}")
        self.log_text.append(f"Master file: {self.master_file}")
        self.log_text.append(f"Target file: {self.target_file}")
        self.log_text.append(f"Logs folder: {self.current_logs_folder}")
        self.log_text.append("=" * 50)
    
    def toggle_pause(self):
        """Toggle between pause and resume"""
        if self.processor:
            with self.processor.lock:
                if self.processor.is_paused:
                    self.processor.resume()
                    self.pause_btn.setText("Pause")
                    self.log_text.append(f"Processing resumed at {datetime.now().strftime('%H:%M:%S')}")
                else:
                    self.processor.pause()
                    self.pause_btn.setText("Resume")
                    self.log_text.append(f"Processing paused at {datetime.now().strftime('%H:%M:%S')}")
    
    def stop_processing(self):
        """Stop processing"""
        if self.processor:
            self.processor.stop()
            self.log_text.append(f"Processing stopped at {datetime.now().strftime('%H:%M:%S')}")
            
            # Wait for thread to finish
            if self.process_thread and self.process_thread.is_alive():
                self.process_thread.join(timeout=2.0)
            
            self.reset_ui_state()
    
    def update_progress(self, total, processed, valid, rejected):
        """Update progress indicators"""
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(processed)
        
        self.total_label.setText(f"Total: {total}")
        self.processed_label.setText(f"Processed: {processed}")
        self.valid_label.setText(f"Valid: {valid}")
        self.rejected_label.setText(f"Rejected: {rejected}")
    
    def update_log(self, level, message, details):
        """Update log display"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] [{level}] {message}")
        if details:
            self.log_text.append(f"    Details: {details}")
    
    def processing_complete(self):
        """Handle processing completion"""
        self.log_text.append("=" * 50)
        self.log_text.append(f"Processing completed at {datetime.now().strftime('%H:%M:%S')}")
        self.log_text.append("Results:")
        self.log_text.append(f"  Total lines: {self.progress_bar.maximum()}")
        self.log_text.append(f"  Valid lines: {self.valid_label.text()}")
        self.log_text.append(f"  Rejected lines: {self.rejected_label.text()}")
        
        self.reset_ui_state()
    
    def handle_error(self, error_message):
        """Handle processing errors"""
        self.log_text.append(f"ERROR: {error_message}")
        self.stop_processing()
        QMessageBox.critical(self, "Error", f"An error occurred:\n{error_message}")
    
    def reset_ui_state(self):
        """Reset UI to initial state"""
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setText("Pause")
        self.stop_btn.setEnabled(False)
        self.master_btn.setEnabled(True)
        self.target_btn.setEnabled(True)
        
        self.processor = None
        self.process_thread = None
    
    def load_settings(self):
        """Load previously used file paths"""
        try:
            if os.path.exists("ulp_validator_settings.txt"):
                with open("ulp_validator_settings.txt", "r") as f:
                    lines = f.readlines()
                    if len(lines) >= 2:
                        self.master_file = lines[0].strip()
                        self.target_file = lines[1].strip()
                        
                        if self.master_file and os.path.exists(self.master_file):
                            self.master_label.setText(f"Master File: {os.path.basename(self.master_file)}")
                        
                        if self.target_file and os.path.exists(self.target_file):
                            self.target_label.setText(f"Target File: {os.path.basename(self.target_file)}")
                        
                        self.check_files_selected()
        except:
            pass  # Silently fail if settings can't be loaded
    
    def save_settings(self):
        """Save current file paths for future use"""
        try:
            with open("ulp_validator_settings.txt", "w") as f:
                f.write(f"{self.master_file}\n")
                f.write(f"{self.target_file}\n")
        except:
            pass  # Silently fail if settings can't be saved
    
    def closeEvent(self, event):
        """Handle application close event"""
        if self.processor and self.processor.is_running:
            reply = QMessageBox.question(
                self, "Confirm Exit", 
                "Processing is still running. Are you sure you want to exit?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.stop_processing()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Set application style for modern look
    app.setStyle("Fusion")
    
    window = ULPValidatorApp()
    window.show()
    
    sys.exit(app.exec_())