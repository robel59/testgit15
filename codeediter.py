import subprocess
import sys
import os
import shutil
import http.server
import socketserver
import threading
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineProfile, QWebEnginePage
from PyQt5.QtCore import QUrl, QRegularExpression, Qt
from PyQt5.QtGui import QSyntaxHighlighter, QTextCharFormat, QBrush, QColor
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QPlainTextEdit, QVBoxLayout, QWidget,
    QFileDialog, QPushButton, QHBoxLayout, QAction, QMessageBox, QMenu,
    QGridLayout, QTextEdit, QSizePolicy, QSplitter
)
from PyQt5.QtGui import QTextCursor

class HtmlHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.highlighting_rules = []

        tag_format = QTextCharFormat()
        tag_format.setForeground(QBrush(QColor("blue")))
        tag_pattern = QRegularExpression(r"</?\w+>")
        self.highlighting_rules.append((tag_pattern, tag_format))

        attr_format = QTextCharFormat()
        attr_format.setForeground(QBrush(QColor("red")))
        attr_pattern = QRegularExpression(r"\w+=")
        self.highlighting_rules.append((attr_pattern, attr_format))

        string_format = QTextCharFormat()
        string_format.setForeground(QBrush(QColor("green")))
        string_pattern = QRegularExpression(r'".*?"')
        self.highlighting_rules.append((string_pattern, string_format))

    def highlightBlock(self, text):
        for pattern, fmt in self.highlighting_rules:
            iterator = pattern.globalMatch(text)
            while iterator.hasNext():
                match = iterator.next()
                start, length = match.capturedStart(), match.capturedLength()
                self.setFormat(start, length, fmt)

class HtmlEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HTML Code Editor with Live Preview")
        self.setGeometry(100, 100, 1200, 800)

        self.working_directory = os.getcwd()
        self.copied_folder = None

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        self.splitter = QSplitter(Qt.Horizontal)
        self.layout.addWidget(self.splitter)

        self.editor = QPlainTextEdit()
        self.editor.setStyleSheet("background-color: black; color: white;")
        self.editor.setTabStopWidth(40)
        self.editor.setPlaceholderText("Edit HTML code here...")
        self.editor.setPlainText("")
        self.splitter.addWidget(self.editor)

        self.preview = QWebEngineView()
        self.splitter.addWidget(self.preview)

        self.html_view = QTextEdit()
        self.html_view.setReadOnly(True)
        self.html_view.setVisible(False)
        self.splitter.addWidget(self.html_view)

        self.splitter.setSizes([600, 600])

        self.file_button_layout = QGridLayout()
        self.layout.addLayout(self.file_button_layout)

        self.toolbar = self.addToolBar("Toolbar")
        self.toolbar.setMovable(False)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.toolbar.addWidget(spacer)

        self.convert_button = QPushButton("Convert")
        self.convert_button.clicked.connect(self.convert_content)
        self.toolbar.addWidget(self.convert_button)

        self.view_html_button = QPushButton("Toggle HTML Code View")
        self.view_html_button.clicked.connect(self.toggle_html_view)
        self.toolbar.addWidget(self.view_html_button)

        self.create_menu()
        self.html_files = {}
        self.current_file_path = None
        self.server_thread = None
        self.is_modified = False
        self.selected_text = ""
        self.html_view_active = False

        self.highlighter = HtmlHighlighter(self.editor.document())
        self.editor.textChanged.connect(self.mark_as_modified)
        self.preview.setContextMenuPolicy(Qt.CustomContextMenu)
        self.preview.customContextMenuRequested.connect(self.show_context_menu)

        self.current_page = None
        self.current_profile = None


    def convert_content(self):
        # Check if there's a folder in the working directory
        if not self.copied_folder:
            QMessageBox.warning(self, "Error", "No folder is currently loaded.")
            return

        folder_name = os.path.basename(self.copied_folder)
        command = f"python3 {self.working_directory}/automate_web.py {folder_name}"
        
        try:
            # Run the command and capture the output
            result = subprocess.run(command, shell=True, text=True, capture_output=True)
            print(result)
            
            # Save the result to convert.txt
            with open("convert.txt", "w") as file:
                file.write(result.stdout)
            
            # Show the result in a message box
            QMessageBox.information(self, "Conversion Complete", "Conversion completed successfully. Check 'convert.txt' for details.")
        
        except subprocess.CalledProcessError as e:
            print(f"Error executing command: {e}")
            QMessageBox.warning(self, "Error", "Failed to execute conversion command.")
        except Exception as e:
            print(f"Unexpected error: {e}")
            QMessageBox.warning(self, "Error", "An unexpected error occurred during conversion.")
    def toggle_html_view(self):
        if self.html_view_active:
            self.html_view.setVisible(False)
            self.preview.setVisible(True)
            self.view_html_button.setText("View HTML Code")
            self.html_view_active = False
        else:
            change_html_path = os.path.join(self.working_directory, "change.html")  # Example path

            try:
                with open(change_html_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                    self.html_view.setPlainText(content)
                
                self.preview.setVisible(False)
                self.html_view.setVisible(True)
                self.view_html_button.setText("Back to Live Preview")
                self.html_view_active = True
            except Exception as e:
                print(f"Error loading change.html: {e}")
                QMessageBox.warning(self, "Error", "Failed to load the change.html file.")

    def create_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")

        open_action = QAction("Open Folder", self)
        open_action.triggered.connect(self.open_folder)
        open_working = QAction("Open working", self)
        open_working.triggered.connect(self.open_working)
        file_menu.addAction(open_action)
        file_menu.addAction(open_working)

    def open_working(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Open Folder")
        self.copied_folder = folder_path

        if folder_path:
            self.load_files(folder_path)
            if self.server_thread and self.server_thread.is_alive():
                self.server_thread.join()  # Ensure the old server is stopped
            self.server_thread = threading.Thread(target=self.start_server, args=(folder_path,))
            self.server_thread.start()

    def open_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Open Folder")
        if folder_path:
            self.copy_folder_to_working_directory(folder_path)
            self.load_files(self.copied_folder)
            if self.server_thread and self.server_thread.is_alive():
                self.server_thread.join()
            self.server_thread = threading.Thread(target=self.start_server, args=(self.copied_folder,))
            self.server_thread.start()

    def copy_folder_to_working_directory(self, folder_path):
        folder_name = os.path.basename(folder_path.rstrip('/\\'))
        destination_folder = os.path.join(self.working_directory, folder_name)
        self.copied_folder = destination_folder

        if os.path.exists(destination_folder):
            shutil.rmtree(destination_folder)
        shutil.copytree(folder_path, destination_folder)
        print(f"Copied folder {folder_name} to working directory.")

    def load_files(self, directory):
        for i in reversed(range(self.file_button_layout.count())):
            widget = self.file_button_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

        self.html_files = {}
        self.current_file_path = None

        try:
            row = 0
            for file_name in os.listdir(directory):
                if file_name.lower().endswith(".html"):
                    file_path = os.path.join(directory, file_name)
                    file_button = QPushButton(file_name)
                    file_button.clicked.connect(lambda checked, path=file_path: self.open_file(path))
                    
                    delete_button = QPushButton("Delete")
                    delete_button.clicked.connect(lambda checked, path=file_path: self.delete_file(path))

                    self.file_button_layout.addWidget(file_button, row, 0)
                    self.file_button_layout.addWidget(delete_button, row, 1)
                    
                    self.html_files[file_name] = file_path
                    row += 1
                    
                    print(f"Loaded file: {file_name}")
        except Exception as e:
            print(f"Error loading files: {e}")

    def open_file(self, file_path):
        if self.is_modified:
            reply = QMessageBox.question(self, 'Unsaved Changes',
                                         "You have unsaved changes. Do you want to save them?",
                                         QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)

            if reply == QMessageBox.Yes:
                self.save_file()

            elif reply == QMessageBox.Cancel:
                return

        try:
            print(f"Opening file: {file_path}")
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                print(f"File content loaded:\n{content}")
                self.editor.setPlainText(content)
                self.current_file_path = file_path
                self.is_modified = False
                self.update_preview(file_path)
        except Exception as e:
            print(f"Error opening file: {e}")

    def save_file(self):
        if self.current_file_path:
            try:
                with open(self.current_file_path, 'w', encoding='utf-8') as file:
                    content = self.editor.toPlainText()
                    print(f"Saving content:\n{content}")
                    file.write(content)
                self.is_modified = False
                self.update_preview(self.current_file_path)
                QMessageBox.information(self, "Saved", "Your changes have been saved.")
            except Exception as e:
                print(f"Error saving file: {e}")
                QMessageBox.warning(self, "Error", "Failed to save the file.")

    def mark_as_modified(self):
        self.is_modified = True

    def update_preview(self, html_file_path):
        if html_file_path:
            try:
                if self.current_page:
                    self.current_page.deleteLater()
                if self.current_profile:
                    self.current_profile.deleteLater()
                    
                self.current_profile = QWebEngineProfile()
                self.current_page = QWebEnginePage(self.current_profile, self.preview)
                self.preview.setPage(self.current_page)
                
                file_url = QUrl(f"http://localhost:8000/{os.path.basename(html_file_path)}")
                print(f"Loading URL in preview: {file_url.toString()}")
                self.current_page.setUrl(file_url)
            except Exception as e:
                print(f"Error updating preview: {e}")

    def show_context_menu(self, point):
        context_menu = QMenu(self)
        copy_action = context_menu.addAction("Copy Selected Text")
        copy_action.triggered.connect(self.copy_selected_text)
        context_menu.exec_(self.preview.mapToGlobal(point))

    def copy_selected_text(self):
        self.preview.page().runJavaScript("window.getSelection().toString();", self.handle_selected_text)

    def handle_selected_text(self, selected_text):
        self.selected_text = selected_text
        print(f"Selected text: {self.selected_text}")

        self.highlight_selected_text()

    def highlight_selected_text(self):
        if self.selected_text:
            content = self.editor.toPlainText()
            start_idx = content.find(self.selected_text)
            if start_idx != -1:
                end_idx = start_idx + len(self.selected_text)
                print(f"Text found in editor at position {start_idx} to {end_idx}")

                cursor = self.editor.textCursor()
                cursor.setPosition(start_idx)
                self.editor.setTextCursor(cursor)

                cursor.setPosition(end_idx, QTextCursor.KeepAnchor)
                self.editor.setTextCursor(cursor)
            else:
                print(f"Text not found in editor.")

    def delete_file(self, file_path):
        if QMessageBox.question(self, "Confirm Delete",
                                "Are you sure you want to delete this file?",
                                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            try:
                os.remove(file_path)
                file_name = os.path.basename(file_path)
                self.html_files.pop(file_name, None)
                self.load_files(self.copied_folder)
                QMessageBox.information(self, "Deleted", "File has been deleted.")
            except Exception as e:
                print(f"Error deleting file: {e}")
                QMessageBox.warning(self, "Error", "Failed to delete the file.")

    def start_server(self, directory):
        PORT = 8000
        Handler = http.server.SimpleHTTPRequestHandler
        os.chdir(directory)

        with socketserver.TCPServer(("", PORT), Handler) as httpd:
            print(f"Serving at port {PORT}")
            httpd.serve_forever()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    editor = HtmlEditor()
    editor.show()
    sys.exit(app.exec_())
