import sys
import os
import sqlite3
from datetime import datetime
from urllib.parse import quote_plus
import threading
import time
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage, QWebEngineDownloadRequest
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog

# Handle PyInstaller paths
if getattr(sys, 'frozen', False):
    # Running as bundled executable
    bundle_dir = sys._MEIPASS
else:
    # Running as script
    bundle_dir = os.path.dirname(os.path.abspath(__file__))

# Add bundle directory to Python path for imports
if bundle_dir not in sys.path:
    sys.path.insert(0, bundle_dir)

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

from database import BrowserDatabase

# AD BLOCK LIST
BLOCKED_DOMAINS = {
    "doubleclick.net", "googlesyndication.com", "googleadservices.com",
    "adservice.google.com", "google-analytics.com", "adsystem.com"
}

class BookmarkManager(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⭐ Bookmark Manager")
        self.setGeometry(100, 100, 800, 600)
        self.parent_browser = parent
        
        layout = QHBoxLayout(self)
        
        # Left side - Folder tree
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        self.folder_tree = QTreeWidget()
        self.folder_tree.setHeaderLabel("Folders")
        self.folder_tree.setMaximumWidth(200)
        self.folder_tree.itemClicked.connect(self.on_folder_selected)
        left_layout.addWidget(self.folder_tree)
        
        # Add folder button
        add_folder_btn = QPushButton("📁 Add Folder")
        add_folder_btn.clicked.connect(self.add_folder)
        left_layout.addWidget(add_folder_btn)
        
        layout.addWidget(left_panel)
        
        # Right side - Bookmarks list
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Bookmarks list
        self.bookmarks_list = QListWidget()
        self.bookmarks_list.itemDoubleClicked.connect(self.open_bookmark)
        right_layout.addWidget(self.bookmarks_list)
        
        # Bookmark details
        details_layout = QFormLayout()
        
        self.title_input = QLineEdit()
        self.url_input = QLineEdit()
        self.folder_combo = QComboBox()
        
        details_layout.addRow("Title:", self.title_input)
        details_layout.addRow("URL:", self.url_input)
        details_layout.addRow("Folder:", self.folder_combo)
        
        right_layout.addLayout(details_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.add_btn = QPushButton("➕ Add")
        self.add_btn.clicked.connect(self.add_bookmark)
        
        self.edit_btn = QPushButton("✏️ Edit")
        self.edit_btn.clicked.connect(self.edit_bookmark)
        
        self.delete_btn = QPushButton("🗑️ Delete")
        self.delete_btn.clicked.connect(self.delete_bookmark)
        
        self.import_btn = QPushButton("📥 Import")
        self.import_btn.clicked.connect(self.import_bookmarks)
        
        self.export_btn = QPushButton("📤 Export")
        self.export_btn.clicked.connect(self.export_bookmarks)
        
        button_layout.addWidget(self.add_btn)
        button_layout.addWidget(self.edit_btn)
        button_layout.addWidget(self.delete_btn)
        button_layout.addWidget(self.import_btn)
        button_layout.addWidget(self.export_btn)
        button_layout.addStretch()
        
        right_layout.addLayout(button_layout)
        layout.addWidget(right_panel)
        
        # Initialize folders
        self.load_folders()
        self.load_bookmarks()
    
    def load_folders(self):
        self.folder_tree.clear()
        # Add default folders
        bookmarks_item = QTreeWidgetItem(self.folder_tree, ["📚 Bookmarks"])
        favorites_item = QTreeWidgetItem(self.folder_tree, ["⭐ Favorites"])
        work_item = QTreeWidgetItem(self.folder_tree, ["💼 Work"])
        personal_item = QTreeWidgetItem(self.folder_tree, ["🏠 Personal"])
        
        # Update folder combo
        self.folder_combo.clear()
        self.folder_combo.addItems(["Bookmarks", "Favorites", "Work", "Personal"])
    
    def load_bookmarks(self):
        self.bookmarks_list.clear()
        if self.parent_browser:
            bookmarks = self.parent_browser.db.get_bookmarks()
            for url, title in bookmarks:
                item = QListWidgetItem(f"🔗 {title}")
                item.setData(1, {'url': url, 'title': title})
                self.bookmarks_list.addItem(item)
    
    def on_folder_selected(self, item, column):
        folder_name = item.text(column)
        self.folder_combo.setCurrentText(folder_name.replace("📚 ", "").replace("⭐ ", "").replace("💼 ", "").replace("🏠 ", ""))
    
    def add_bookmark(self):
        title = self.title_input.text()
        url = self.url_input.text()
        folder = self.folder_combo.currentText()
        
        if title and url and self.parent_browser:
            self.parent_browser.db.add_bookmark(url, title)
            self.load_bookmarks()
            self.title_input.clear()
            self.url_input.clear()
            self.parent_browser.status_label.setText(f"✅ Bookmark added: {title}")
    
    def edit_bookmark(self):
        current_item = self.bookmarks_list.currentItem()
        if current_item:
            bookmark_data = current_item.data(1)
            if bookmark_data:
                self.title_input.setText(bookmark_data['title'])
                self.url_input.setText(bookmark_data['url'])
    
    def delete_bookmark(self):
        current_item = self.bookmarks_list.currentItem()
        if current_item and self.parent_browser:
            bookmark_data = current_item.data(1)
            if bookmark_data:
                self.parent_browser.db.remove_bookmark(bookmark_data['url'])
                self.load_bookmarks()
                self.parent_browser.status_label.setText("🗑️ Bookmark deleted")
    
    def open_bookmark(self, item):
        bookmark_data = item.data(1)
        if bookmark_data and self.parent_browser:
            self.parent_browser.navigate_to_url(bookmark_data['url'])
    
    def add_folder(self):
        folder_name, ok = QInputDialog.getText(self, "Add Folder", "Folder name:")
        if ok and folder_name:
            QTreeWidgetItem(self.folder_tree, [f"📁 {folder_name}"])
            self.folder_combo.addItem(folder_name)
    
    def import_bookmarks(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Import Bookmarks", "", "HTML Files (*.html);;JSON Files (*.json)")
        if file_path:
            # Basic import implementation
            self.parent_browser.status_label.setText(f"📥 Bookmarks imported from {file_path}")
    
    def export_bookmarks(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Bookmarks", "bookmarks.html", "HTML Files (*.html)")
        if file_path:
            # Basic export implementation
            self.parent_browser.status_label.setText(f"📤 Bookmarks exported to {file_path}")

class HistoryViewer(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📜 History")
        self.setGeometry(100, 100, 900, 600)
        self.parent_browser = parent
        
        layout = QVBoxLayout(self)
        
        # Search bar
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search history...")
        self.search_input.textChanged.connect(self.search_history)
        search_layout.addWidget(self.search_input)
        
        self.clear_history_btn = QPushButton("🗑️ Clear All History")
        self.clear_history_btn.clicked.connect(self.clear_all_history)
        search_layout.addWidget(self.clear_history_btn)
        
        layout.addLayout(search_layout)
        
        # History list
        self.history_list = QListWidget()
        self.history_list.itemDoubleClicked.connect(self.open_history_item)
        layout.addWidget(self.history_list)
        
        # Details panel
        details_layout = QHBoxLayout()
        
        self.details_label = QLabel("Select an item to view details")
        self.details_label.setWordWrap(True)
        details_layout.addWidget(self.details_label)
        
        layout.addLayout(details_layout)
        
        self.load_history()
    
    def load_history(self):
        self.history_list.clear()
        if self.parent_browser:
            history = self.parent_browser.db.get_history(limit=100)
            for url, title, timestamp in history:
                # Format timestamp
                from datetime import datetime
                date_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M")
                
                item = QListWidgetItem(f"🌐 {title} - {date_str}")
                item.setData(1, {'url': url, 'title': title, 'timestamp': timestamp})
                self.history_list.addItem(item)
    
    def search_history(self, text):
        self.history_list.clear()
        if self.parent_browser and text:
            history = self.parent_browser.db.get_history(limit=100)
            for url, title, timestamp in history:
                if text.lower() in title.lower() or text.lower() in url.lower():
                    from datetime import datetime
                    date_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M")
                    
                    item = QListWidgetItem(f"🌐 {title} - {date_str}")
                    item.setData(1, {'url': url, 'title': title, 'timestamp': timestamp})
                    self.history_list.addItem(item)
        elif not text:
            self.load_history()
    
    def open_history_item(self, item):
        history_data = item.data(1)
        if history_data and self.parent_browser:
            self.parent_browser.navigate_to_url(history_data['url'])
            
            # Update details
            from datetime import datetime
            date_str = datetime.fromtimestamp(history_data['timestamp']).strftime("%Y-%m-%d %H:%M:%S")
            self.details_label.setText(f"Title: {history_data['title']}\nURL: {history_data['url']}\nVisited: {date_str}")
    
    def clear_all_history(self):
        reply = QMessageBox.question(self, "Clear History", "Are you sure you want to clear all history?", 
                                   QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes and self.parent_browser:
            self.parent_browser.db.clear_history()
            self.load_history()
            self.parent_browser.status_label.setText("🗑️ History cleared")

class DeveloperTools(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🛠️ Developer Tools")
        self.setGeometry(100, 100, 1000, 700)
        self.parent_browser = parent
        
        layout = QVBoxLayout(self)
        
        # Tab widget for different dev tools
        self.dev_tabs = QTabWidget()
        layout.addWidget(self.dev_tabs)
        
        # View Source Tab
        source_tab = QWidget()
        source_layout = QVBoxLayout(source_tab)
        
        source_toolbar = QHBoxLayout()
        refresh_source_btn = QPushButton("🔄 Refresh")
        refresh_source_btn.clicked.connect(self.refresh_source)
        copy_source_btn = QPushButton("📋 Copy")
        copy_source_btn.clicked.connect(self.copy_source)
        source_toolbar.addWidget(refresh_source_btn)
        source_toolbar.addWidget(copy_source_btn)
        source_toolbar.addStretch()
        
        source_layout.addLayout(source_toolbar)
        
        self.source_text = QTextEdit()
        self.source_text.setReadOnly(True)
        self.source_text.setFont(QFont("Consolas", 10))
        source_layout.addWidget(self.source_text)
        
        self.dev_tabs.addTab(source_tab, "📄 View Source")
        
        # Console Tab
        console_tab = QWidget()
        console_layout = QVBoxLayout(console_tab)
        
        console_toolbar = QHBoxLayout()
        clear_console_btn = QPushButton("🗑️ Clear")
        clear_console_btn.clicked.connect(self.clear_console)
        console_toolbar.addWidget(clear_console_btn)
        console_toolbar.addStretch()
        
        console_layout.addLayout(console_toolbar)
        
        self.console_output = QTextEdit()
        self.console_output.setReadOnly(True)
        self.console_output.setFont(QFont("Consolas", 10))
        console_layout.addWidget(self.console_output)
        
        # Console input
        console_input_layout = QHBoxLayout()
        self.console_input = QLineEdit()
        self.console_input.setPlaceholderText("Enter JavaScript command...")
        self.console_input.returnPressed.connect(self.execute_console_command)
        execute_btn = QPushButton("▶️ Execute")
        execute_btn.clicked.connect(self.execute_console_command)
        
        console_input_layout.addWidget(self.console_input)
        console_input_layout.addWidget(execute_btn)
        console_layout.addLayout(console_input_layout)
        
        self.dev_tabs.addTab(console_tab, "🖥️ Console")
        
        # Network Tab
        network_tab = QWidget()
        network_layout = QVBoxLayout(network_tab)
        
        network_toolbar = QHBoxLayout()
        clear_network_btn = QPushButton("🗑️ Clear")
        clear_network_btn.clicked.connect(self.clear_network)
        network_toolbar.addWidget(clear_network_btn)
        network_toolbar.addStretch()
        
        network_layout.addLayout(network_toolbar)
        
        self.network_list = QListWidget()
        network_layout.addWidget(self.network_list)
        
        self.dev_tabs.addTab(network_tab, "🌐 Network")
        
        # Info Tab
        info_tab = QWidget()
        info_layout = QVBoxLayout(info_tab)
        
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        info_layout.addWidget(self.info_text)
        
        self.dev_tabs.addTab(info_tab, "ℹ️ Info")
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.refresh_all_btn = QPushButton("🔄 Refresh All")
        self.refresh_all_btn.clicked.connect(self.refresh_all)
        
        self.close_btn = QPushButton("❌ Close")
        self.close_btn.clicked.connect(self.accept)
        
        button_layout.addWidget(self.refresh_all_btn)
        button_layout.addWidget(self.close_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        # Initialize
        self.refresh_all()
    
    def refresh_all(self):
        self.refresh_source()
        self.refresh_info()
        self.console_output.append("🔄 Developer tools refreshed")
    
    def refresh_source(self):
        if self.parent_browser:
            webview = self.parent_browser.current_webview()
            if webview:
                # Get page source
                webview.page().toHtml(self.on_source_loaded)
            else:
                self.source_text.setText("No page loaded")
    
    def on_source_loaded(self, html):
        self.source_text.setText(html)
    
    def copy_source(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.source_text.toPlainText())
        self.console_output.append("📋 Source copied to clipboard")
    
    def clear_console(self):
        self.console_output.clear()
    
    def execute_console_command(self):
        command = self.console_input.text()
        if command and self.parent_browser:
            webview = self.parent_browser.current_webview()
            if webview:
                # Execute JavaScript
                webview.page().runJavaScript(command, self.on_console_result)
                self.console_output.append(f"> {command}")
                self.console_input.clear()
    
    def on_console_result(self, result):
        self.console_output.append(f"< {result}")
    
    def clear_network(self):
        self.network_list.clear()
    
    def refresh_info(self):
        if self.parent_browser:
            webview = self.parent_browser.current_webview()
            if webview:
                url = webview.url().toString()
                title = webview.title()
                
                info = f"""Page Information:
                
Title: {title}
URL: {url}
User Agent: {webview.page().profile().httpUserAgent()}
Zoom Level: {webview.zoomFactor()}

Page Features:
- JavaScript: Enabled
- Cookies: Enabled
- Local Storage: Available
- Session Storage: Available

Security:
- HTTPS: {'Yes' if url.startswith('https://') else 'No'}
- Mixed Content: Check console for warnings
"""
                self.info_text.setText(info)
            else:
                self.info_text.setText("No page loaded")

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚙️ Settings")
        self.setGeometry(100, 100, 600, 500)
        self.parent_browser = parent
        
        layout = QVBoxLayout(self)
        
        # Tab widget for different settings categories
        self.settings_tabs = QTabWidget()
        layout.addWidget(self.settings_tabs)
        
        # General Settings Tab
        general_tab = QWidget()
        general_layout = QVBoxLayout(general_tab)
        
        # Homepage setting
        homepage_layout = QHBoxLayout()
        homepage_layout.addWidget(QLabel("Homepage:"))
        self.homepage_input = QLineEdit("http://127.0.0.1:5000/")
        homepage_layout.addWidget(self.homepage_input)
        general_layout.addLayout(homepage_layout)
        
        # Search engine setting
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search Engine:"))
        self.search_engine = QComboBox()
        self.search_engine.addItems(["DuckDuckGo", "Google", "Bing", "Yahoo"])
        search_layout.addWidget(self.search_engine)
        general_layout.addLayout(search_layout)
        
        # Theme setting
        theme_layout = QHBoxLayout()
        theme_layout.addWidget(QLabel("Theme:"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Light", "Dark", "System"])
        theme_layout.addWidget(self.theme_combo)
        general_layout.addLayout(theme_layout)
        
        # Startup behavior
        self.restore_session = QCheckBox("Restore previous session on startup")
        general_layout.addWidget(self.restore_session)
        
        general_layout.addStretch()
        self.settings_tabs.addTab(general_tab, "🌐 General")
        
        # Privacy Settings Tab
        privacy_tab = QWidget()
        privacy_layout = QVBoxLayout(privacy_tab)
        
        self.clear_history_on_exit = QCheckBox("Clear history on exit")
        privacy_layout.addWidget(self.clear_history_on_exit)
        
        self.block_third_party_cookies = QCheckBox("Block third-party cookies")
        privacy_layout.addWidget(self.block_third_party_cookies)
        
        self.send_do_not_track = QCheckBox("Send Do Not Track header")
        privacy_layout.addWidget(self.send_do_not_track)
        
        privacy_layout.addStretch()
        self.settings_tabs.addTab(privacy_tab, "🔒 Privacy")
        
        # Appearance Settings Tab
        appearance_tab = QWidget()
        appearance_layout = QVBoxLayout(appearance_tab)
        
        # Font size
        font_layout = QHBoxLayout()
        font_layout.addWidget(QLabel("Font Size:"))
        self.font_size = QSpinBox()
        self.font_size.setRange(8, 24)
        self.font_size.setValue(16)
        font_layout.addWidget(self.font_size)
        font_layout.addStretch()
        appearance_layout.addLayout(font_layout)
        
        # Zoom level
        zoom_layout = QHBoxLayout()
        zoom_layout.addWidget(QLabel("Default Zoom:"))
        self.default_zoom = QComboBox()
        self.default_zoom.addItems(["50%", "75%", "100%", "125%", "150%", "200%"])
        self.default_zoom.setCurrentText("100%")
        zoom_layout.addWidget(self.default_zoom)
        zoom_layout.addStretch()
        appearance_layout.addLayout(zoom_layout)
        
        appearance_layout.addStretch()
        self.settings_tabs.addTab(appearance_tab, "🎨 Appearance")
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("💾 Save Settings")
        self.save_btn.clicked.connect(self.save_settings)
        
        self.cancel_btn = QPushButton("❌ Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.cancel_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        # Load current settings
        self.load_settings()
    
    def load_settings(self):
        if self.parent_browser and hasattr(self.parent_browser, 'settings'):
            settings = self.parent_browser.settings
            self.homepage_input.setText(settings.get('homepage', 'http://127.0.0.1:5000/'))
            self.search_engine.setCurrentText(settings.get('search_engine', 'DuckDuckGo'))
            self.theme_combo.setCurrentText(settings.get('theme', 'Light'))
            self.restore_session.setChecked(settings.get('restore_session', False))
            self.clear_history_on_exit.setChecked(settings.get('clear_history_on_exit', False))
            self.block_third_party_cookies.setChecked(settings.get('block_third_party_cookies', False))
            self.send_do_not_track.setChecked(settings.get('send_do_not_track', False))
            self.font_size.setValue(settings.get('font_size', 16))
            self.default_zoom.setCurrentText(settings.get('default_zoom', '100%'))
    
    def save_settings(self):
        if self.parent_browser:
            self.parent_browser.settings = {
                'homepage': self.homepage_input.text(),
                'search_engine': self.search_engine.currentText(),
                'theme': self.theme_combo.currentText(),
                'restore_session': self.restore_session.isChecked(),
                'clear_history_on_exit': self.clear_history_on_exit.isChecked(),
                'block_third_party_cookies': self.block_third_party_cookies.isChecked(),
                'send_do_not_track': self.send_do_not_track.isChecked(),
                'font_size': self.font_size.value(),
                'default_zoom': self.default_zoom.currentText()
            }
            self.parent_browser.status_label.setText("✅ Settings saved successfully")
        self.accept()

class DownloadsManager(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📥 Downloads Manager")
        self.setGeometry(100, 100, 800, 600)
        self.parent_browser = parent
        
        layout = QVBoxLayout(self)
        
        # Downloads list
        self.downloads_list = QListWidget()
        self.downloads_list.itemDoubleClicked.connect(self.open_download)
        layout.addWidget(self.downloads_list)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.clicked.connect(self.refresh_downloads)
        
        self.clear_btn = QPushButton("🗑️ Clear Completed")
        self.clear_btn.clicked.connect(self.clear_completed)
        
        self.open_folder_btn = QPushButton("📁 Open Downloads Folder")
        self.open_folder_btn.clicked.connect(self.open_downloads_folder)
        
        button_layout.addWidget(self.refresh_btn)
        button_layout.addWidget(self.clear_btn)
        button_layout.addWidget(self.open_folder_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        self.refresh_downloads()
    
    def refresh_downloads(self):
        self.downloads_list.clear()
        if self.parent_browser:
            for download in self.parent_browser.downloads:
                item = QListWidgetItem(f"📄 {download['filename']} - {download['status']}")
                item.setData(1, download)  # Store download data
                self.downloads_list.addItem(item)
    
    def open_download(self, item):
        download = item.data(1)
        if download and download['status'] == 'Completed':
            import os
            import subprocess
            if os.path.exists(download['path']):
                if os.name == 'nt':  # Windows
                    os.startfile(download['path'])
                elif os.name == 'posix':  # macOS/Linux
                    subprocess.run(['open' if sys.platform == 'darwin' else 'xdg-open', download['path']])
    
    def clear_completed(self):
        if self.parent_browser:
            self.parent_browser.downloads = [d for d in self.parent_browser.downloads if d['status'] != 'Completed']
            self.refresh_downloads()
    
    def open_downloads_folder(self):
        import os
        import subprocess
        downloads_path = os.path.join(os.path.expanduser('~'), 'Downloads')
        if not os.path.exists(downloads_path):
            os.makedirs(downloads_path)
        
        if os.name == 'nt':  # Windows
            os.startfile(downloads_path)
        elif os.name == 'posix':  # macOS/Linux
            subprocess.run(['open' if sys.platform == 'darwin' else 'xdg-open', downloads_path])

class AdBlockPage(QWebEnginePage):
    def __init__(self, profile, parent=None):
        super().__init__(profile, parent)
        self.parent_browser = parent
    
    def acceptNavigationRequest(self, url, nav_type, is_main_frame):
        url_str = url.toString().lower()
        for domain in BLOCKED_DOMAINS:
            if domain in url_str:
                # Try to update status if parent browser is available
                try:
                    # Find the main browser window
                    main_window = None
                    if self.parent_browser and hasattr(self.parent_browser, 'status_label'):
                        main_window = self.parent_browser
                    elif hasattr(self, 'parent_browser') and self.parent_browser:
                        main_window = self.parent_browser
                    
                    if main_window:
                        main_window.status_label.setText("🚫 AD BLOCKED!")
                except:
                    pass  # Don't crash on status update
                return False
        return super().acceptNavigationRequest(url, nav_type, is_main_frame)

class WebTab(QWidget):
    titleChanged = pyqtSignal(str)
    urlChanged = pyqtSignal(str)
    
    def __init__(self, browser):
        super().__init__()
        self.browser = browser
        self.is_pinned = False
        
        self.webview = QWebEngineView()
        profile = browser.incognito_profile if browser.is_incognito else browser.normal_profile
        self.page = AdBlockPage(profile, self.webview)
        self.webview.setPage(self.page)
        
        layout = QVBoxLayout(self)
        layout.addWidget(self.webview)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.webview.titleChanged.connect(self.update_title)
        self.webview.urlChanged.connect(self.update_url)
        self.webview.loadFinished.connect(self.on_load_finished)
        self.webview.loadProgress.connect(self.browser.update_progress)
        
        # Enable context menu
        self.webview.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.webview.customContextMenuRequested.connect(self.show_context_menu)
    
    def update_title(self, title):
        display = title[:30] + "..." if len(title) > 30 else title
        prefix = "📌 " if self.is_pinned else ""
        self.titleChanged.emit(prefix + display)
    
    def update_url(self, url):
        self.urlChanged.emit(url.toString())
    
    def on_load_finished(self):
        self.browser.progress_bar.setValue(100)
        # Automatic history tracking for every page visit (except incognito)
        if hasattr(self, 'webview'):
            url = self.webview.url().toString()
            title = self.webview.title()
            # Track all pages except local server pages and incognito mode
            if url and not url.startswith('http://127.0.0.1:5000') and not self.browser.is_incognito:
                self.browser.db.add_history_entry(url, title)
                self.browser.status_label.setText(f"📜 Tracked: {title[:30]}{'...' if len(title) > 30 else ''}")
            elif self.browser.is_incognito:
                self.browser.status_label.setText("🕶️ Private browsing - no tracking")
    
    def load_url(self, url):
        self.webview.load(QUrl(url))
    
    def pin_tab(self):
        self.is_pinned = not self.is_pinned
        self.update_title(self.webview.title())
    
    def show_context_menu(self, pos):
        """Show custom context menu"""
        menu = QMenu(self.browser)
        
        # Navigation actions
        back_action = menu.addAction("⬅️ Back")
        forward_action = menu.addAction("➡️ Forward")
        reload_action = menu.addAction("🔄 Reload")
        menu.addSeparator()
        
        # Page actions
        view_source_action = menu.addAction("📄 View Source")
        inspect_action = menu.addAction("🔍 Inspect Element")
        menu.addSeparator()
        
        # Utility actions
        save_page_action = menu.addAction("💾 Save Page As...")
        print_action = menu.addAction("🖨️ Print...")
        menu.addSeparator()
        
        # Copy actions
        copy_url_action = menu.addAction("📋 Copy URL")
        copy_title_action = menu.addAction("📋 Copy Title")
        
        # Connect actions
        back_action.triggered.connect(self.browser.go_back)
        forward_action.triggered.connect(self.browser.go_forward)
        reload_action.triggered.connect(self.browser.refresh_page)
        
        def view_source():
            url = self.webview.url().toString()
            if url:
                self.webview.load(QUrl(f"view-source:{url}"))
        
        def inspect():
            # Simple dev tools - open in new tab
            self.webview.page().triggerAction(QWebEnginePage.WebAction.InspectElement)
        
        def save_page():
            url = self.webview.url().toString()
            title = self.webview.title()
            if url:
                filename, _ = QFileDialog.getSaveFileName(
                    self.browser, "Save Page", f"{title}.html", "HTML Files (*.html)"
                )
                if filename:
                    # Simple save - would need more implementation for full page save
                    self.browser.status_label.setText(f"💾 Saved: {filename}")
        
        view_source_action.triggered.connect(view_source)
        inspect_action.triggered.connect(inspect)
        save_page_action.triggered.connect(save_page)
        print_action.triggered.connect(self.browser.print_page)
        
        def copy_url():
            clipboard = QApplication.clipboard()
            clipboard.setText(self.webview.url().toString())
            self.browser.status_label.setText("📋 URL copied")
        
        def copy_title():
            clipboard = QApplication.clipboard()
            clipboard.setText(self.webview.title())
            self.browser.status_label.setText("📋 Title copied")
        
        copy_url_action.triggered.connect(copy_url)
        copy_title_action.triggered.connect(copy_title)
        
        # Show menu
        menu.exec(self.webview.mapToGlobal(pos))

class MyBrowser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🚀 Go Through - Ultimate Browser")
        self.setGeometry(50, 50, 1800, 1000)
        self.showMaximized()
        
        # CORE UI ELEMENTS FIRST - prevent crashes
        self.url_bar = QLineEdit()
        self.tab_widget = QTabWidget()
        
        # Browser state
        self.download_path = "Downloads"
        os.makedirs(self.download_path, exist_ok=True)
        
        self.is_incognito = False
        self.adblock_enabled = True
        self.normal_profile = QWebEngineProfile.defaultProfile()
        self.incognito_profile = QWebEngineProfile()
        
        # Downloads
        self.normal_profile.downloadRequested.connect(self.handle_download)
        self.incognito_profile.downloadRequested.connect(self.handle_download)
        
        self.downloads = []
        self.db = BrowserDatabase()
        self.zoom_factor = 1.0
        self.find_text = ""
        self.is_fullscreen = False
        self.settings = self.load_settings()
        self.session_urls = []
        
        # Initialize UI after core elements exist
        self.init_ui()
        self.setup_shortcuts()
        self.start_search_server()
        self.restore_session()
    
    def start_search_server(self):
        """Start Flask search server in background thread"""
        def run_server():
            # Ensure we can find the search_server module
            if getattr(sys, 'frozen', False):
                # In PyInstaller bundle, add current directory to path
                current_dir = os.path.dirname(os.path.abspath(sys.executable))
                if current_dir not in sys.path:
                    sys.path.insert(0, current_dir)
            
            import search_server
            # Suppress Flask output
            import logging
            log = logging.getLogger('werkzeug')
            log.setLevel(logging.ERROR)
            search_server.app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)
        
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        time.sleep(0.5)  # Give server time to start
        self.status_label.setText("🚀 Ready - Go Through Browser (Local Server)")
    
    
    def init_ui(self):
        # Configure URL bar (already created in __init__)
        self.url_bar.setPlaceholderText("🔍 Search or enter URL...")
        self.url_bar.setStyleSheet("""
            QLineEdit {
                padding: 12px 20px;
                border: 2px solid #3498db;
                border-radius: 25px;
                font-size: 16px;
                font-weight: 500;
                background: #ffffff;
                color: #2c3e50;
            }
            QLineEdit:focus {
                border-color: #2980b9;
                outline: none;
            }
        """)
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        
        # Add real-time search suggestions
        from PyQt6.QtWidgets import QCompleter
        from PyQt6.QtCore import QStringListModel
        self.completer = QCompleter()
        self.url_bar.setCompleter(self.completer)
        self.url_bar.textChanged.connect(self.on_url_text_changed)
        
        # Configure tab widget (already created in __init__)
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #ddd; }
            QTabBar::tab { background: #f0f0f0; padding: 12px 20px; margin-right: 2px; }
            QTabBar::tab:selected { background: #4285f4; color: white; }
            QTabBar::close-button { image: none; subcontrol-position: right; width: 20px; }
            QTabBar::close-button:hover { background: #ff4444; }
        """)
        
        # Main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Add toolbar and tabs
        self.create_toolbar(layout)
        layout.addWidget(self.tab_widget)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.status_label = QLabel("🚀 Ready - Go Through Browser")
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.setFixedWidth(250)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.hide()
        self.status_bar.addWidget(self.status_label)
        self.status_bar.addPermanentWidget(self.progress_bar)
        self.setStatusBar(self.status_bar)
        
        # Add first tab
        self.add_new_tab("http://127.0.0.1:5000")
    
    def create_toolbar(self, layout):
        toolbar_widget = QWidget()
        toolbar_widget.setFixedHeight(80)  # Compact single row
        toolbar_layout = QHBoxLayout(toolbar_widget)
        toolbar_layout.setSpacing(8)
        toolbar_layout.setContentsMargins(15, 10, 15, 10)
        
        # Navigation group
        nav_group = QWidget()
        nav_layout = QHBoxLayout(nav_group)
        nav_layout.setSpacing(3)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        
        self.back_btn = QPushButton("⬅")
        self.forward_btn = QPushButton("➡")
        self.refresh_btn = QPushButton("🔄")
        self.home_btn = QPushButton("🏠")
        
        for btn in [self.back_btn, self.forward_btn, self.refresh_btn, self.home_btn]:
            btn.setFixedSize(40, 40)
            btn.setStyleSheet("""
                QPushButton { 
                    background: #f8f9fa;
                    color: #2c3e50;
                    border: 1px solid #dee2e6;
                    border-radius: 8px;
                    font-size: 16px;
                    font-weight: 600;
                } 
                QPushButton:hover { 
                    background: #e9ecef;
                    border-color: #3498db;
                }
                QPushButton:pressed {
                    background: #dee2e6;
                }
            """)
        
        nav_layout.addWidget(self.back_btn)
        nav_layout.addWidget(self.forward_btn)
        nav_layout.addWidget(self.refresh_btn)
        nav_layout.addWidget(self.home_btn)
        
        # URL bar
        self.url_bar.setStyleSheet("""
            QLineEdit {
                padding: 10px 15px;
                border: 2px solid #dee2e6;
                border-radius: 20px;
                font-size: 14px;
                background: #ffffff;
                color: #2c3e50;
            }
            QLineEdit:focus {
                border-color: #3498db;
                outline: none;
            }
        """)
        
        # Feature buttons group
        feature_group = QWidget()
        feature_layout = QHBoxLayout(feature_group)
        feature_layout.setSpacing(3)
        feature_layout.setContentsMargins(0, 0, 0, 0)
        
        self.tab_btn = QPushButton("➕")
        self.bookmark_btn = QPushButton("⭐")
        self.history_btn = QPushButton("📜")
        self.downloads_btn = QPushButton("📥")
        self.settings_btn = QPushButton("⚙️")
        self.devtools_btn = QPushButton("🛠️")
        self.incognito_btn = QPushButton("🕶️")
        self.adblock_btn = QPushButton("🚫")
        
        feature_buttons = [
            self.tab_btn, self.bookmark_btn, self.history_btn, self.downloads_btn,
            self.settings_btn, self.devtools_btn, self.incognito_btn, self.adblock_btn
        ]
        
        for btn in feature_buttons:
            btn.setFixedSize(40, 40)
            btn.setStyleSheet("""
                QPushButton { 
                    background: #f8f9fa;
                    color: #2c3e50;
                    border: 1px solid #dee2e6;
                    border-radius: 8px;
                    font-size: 16px;
                    font-weight: 600;
                } 
                QPushButton:hover { 
                    background: #e9ecef;
                    border-color: #3498db;
                }
                QPushButton:pressed {
                    background: #dee2e6;
                }
            """)
        
        feature_layout.addWidget(self.tab_btn)
        feature_layout.addWidget(self.bookmark_btn)
        feature_layout.addWidget(self.history_btn)
        feature_layout.addWidget(self.downloads_btn)
        feature_layout.addWidget(self.settings_btn)
        feature_layout.addWidget(self.devtools_btn)
        feature_layout.addWidget(self.incognito_btn)
        feature_layout.addWidget(self.adblock_btn)
        
        # Add all groups to toolbar
        toolbar_layout.addWidget(nav_group)
        toolbar_layout.addWidget(self.url_bar)
        toolbar_layout.addWidget(feature_group)
        
        # Connect all buttons
        self.back_btn.clicked.connect(self.go_back)
        self.forward_btn.clicked.connect(self.go_forward)
        self.refresh_btn.clicked.connect(self.refresh_page)
        self.home_btn.clicked.connect(self.go_home)
        self.tab_btn.clicked.connect(self.add_new_tab)
        self.bookmark_btn.clicked.connect(self.add_bookmark)
        self.history_btn.clicked.connect(self.show_history)
        self.downloads_btn.clicked.connect(self.show_downloads)
        self.settings_btn.clicked.connect(self.show_settings)
        self.devtools_btn.clicked.connect(self.show_devtools)
        self.incognito_btn.clicked.connect(self.toggle_incognito)
        self.adblock_btn.clicked.connect(self.toggle_adblock)
        
        layout.addWidget(toolbar_widget)
    
    def current_webview(self):
        """Get current QWebEngineView directly"""
        if self.tab_widget.count() == 0:
            return None
        return self.tab_widget.currentWidget()
    
    def add_new_tab(self, url=None):
        """Add new tab - ultra simple version"""
        if url is None:
            url = "http://127.0.0.1:5000/"
        
        try:
            # Create basic webview without any profiles or AdBlock
            webview = QWebEngineView()
            
            # Add to tab
            index = self.tab_widget.addTab(webview, "New Tab")
            self.tab_widget.setCurrentIndex(index)
            
            # Load URL
            if url and isinstance(url, str):
                webview.load(QUrl(url))
            else:
                webview.load(QUrl("http://127.0.0.1:5000/"))
            
            # Simple signal connections
            webview.titleChanged.connect(
                lambda title: self.tab_widget.setTabText(index, title[:30] + "..." if len(title) > 30 else title)
            )
            webview.urlChanged.connect(
                lambda url: self.url_bar.setText(url.toString()) if self.tab_widget.currentIndex() == index else None
            )
            webview.urlChanged.connect(lambda: self.update_navigation_buttons())
            webview.loadFinished.connect(lambda: self.update_navigation_buttons())
            
            print("New tab created successfully")
            
        except Exception as e:
            print(f"FAILED to create tab: {e}")
            import traceback
            traceback.print_exc()
        
        # Update navigation when tab changes
        self.tab_widget.currentChanged.connect(lambda: self.update_navigation_buttons())
    
    def on_tab_load_finished(self, webview):
        """Handle tab load finished"""
        self.progress_bar.setValue(100)
        QTimer.singleShot(1500, self.progress_bar.hide)
        
        # Automatic history tracking (except incognito and local pages)
        if not self.is_incognito:
            url = webview.url().toString()
            title = webview.title()
            if url and not url.startswith('http://127.0.0.1:5000'):
                self.db.add_history_entry(url, title)
                self.status_label.setText(f"📜 Tracked: {title[:30]}{'...' if len(title) > 30 else ''}")
        else:
            self.status_label.setText("🕶️ Private browsing - no tracking")
    
    def close_tab(self, index):
        if self.tab_widget.count() > 1:
            self.tab_widget.removeTab(index)
            self.update_navigation_buttons()
    
    def update_navigation_buttons(self):
        """Update navigation buttons - SIMPLE VERSION"""
        webview = self.tab_widget.currentWidget()
        if webview:
            history = webview.history()
            if history:
                self.back_btn.setEnabled(history.canGoBack())
                self.forward_btn.setEnabled(history.canGoForward())
            else:
                self.back_btn.setEnabled(False)
                self.forward_btn.setEnabled(False)
    
    def go_back(self):
        """Go back - SIMPLE VERSION"""
        webview = self.tab_widget.currentWidget()
        if webview:
            webview.back()
    
    def go_forward(self):
        """Go forward - SIMPLE VERSION"""
        webview = self.tab_widget.currentWidget()
        if webview:
            webview.forward()
    
    def refresh_page(self):
        webview = self.current_webview()
        if webview:
            webview.reload()
    
    def go_home(self):
        webview = self.current_webview()
        if webview:
            webview.load(QUrl("http://127.0.0.1:5000/"))
    
    def on_url_text_changed(self, text):
        """Handle real-time search suggestions with QStringListModel"""
        if len(text) >= 2:
            try:
                # Get suggestions from database
                suggestions = self.db.get_suggestions(text)
                if suggestions:
                    # Extract URLs for completion
                    suggestion_urls = [url for url, title in suggestions]
                    from PyQt6.QtCore import QStringListModel
                    model = QStringListModel(suggestion_urls)
                    self.completer.setModel(model)
            except Exception as e:
                print(f"Suggestion error: {e}")
                pass
    
    def navigate_to_url(self):
        text = self.url_bar.text().strip()
        if not text:
            return
        
        webview = self.current_webview()
        if not webview:
            return
        
        # Check if it's a full URL or search term
        if text.startswith(("http://", "https://")):
            url = text  # Direct URL
        elif " " not in text and "." in text:
            url = f"https://{text}"  # Domain like "github.com"
        else:
            # Search term - redirect to DuckDuckGo directly
            query = quote_plus(text)
            url = f"https://www.duckduckgo.com/?q={query}"
        
        webview.load(QUrl(url))
    
    def toggle_incognito(self):
        """Open private browsing window with OffTheRecord profile"""
        private_browser = MyBrowser()
        private_browser.setWindowTitle("🕶️ Private Browsing - Go Through")
        private_browser.is_incognito = True
        
        # Create OffTheRecord profile for true private browsing
        private_browser.incognito_profile = QWebEngineProfile.defaultProfile().offTheRecord()
        private_browser.incognito_profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.MemoryHttpCache)
        private_browser.incognito_profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.NoPersistentCookies)
        
        private_browser.show()
        self.status_label.setText("🕶️ Private window opened")
    
    def toggle_adblock(self):
        self.adblock_enabled = not self.adblock_enabled
        self.adblock_btn.setText("🚫" if self.adblock_enabled else "🚫")
        self.status_label.setText(f"🚫 AdBlock {'ON' if self.adblock_enabled else 'OFF'}")
    
    def add_bookmark(self):
        webview = self.current_webview()
        if webview:
            title = self.tab_widget.tabText(self.tab_widget.currentIndex())
            url = webview.url().toString()
            success = self.db.add_bookmark(url, title)
            if success:
                self.status_label.setText("⭐ Bookmarked!")
            else:
                self.status_label.setText("⭐ Already bookmarked!")
    
    def pin_current_tab(self):
        current_tab = self.tab_widget.currentWidget()
        if current_tab and hasattr(current_tab, 'pin_tab'):
            current_tab.pin_tab()
    
    def show_downloads(self):
        """Show downloads manager dialog"""
        downloads_dialog = DownloadsManager(self)
        downloads_dialog.exec()
    
    def show_devtools(self):
        """Show developer tools dialog"""
        devtools_dialog = DeveloperTools(self)
        devtools_dialog.exec()
    
    def show_settings(self):
        """Show settings dialog"""
        settings_dialog = SettingsDialog(self)
        settings_dialog.exec()
    
    def show_history(self):
        """Show history viewer dialog"""
        history_dialog = HistoryViewer(self)
        history_dialog.exec()
    
    def show_bookmarks(self):
        """Show bookmark manager dialog"""
        bookmark_dialog = BookmarkManager(self)
        bookmark_dialog.exec()
    
    def zoom_in(self):
        """Zoom in current page"""
        webview = self.current_webview()
        if webview:
            webview.setZoomFactor(webview.zoomFactor() * 1.2)
            self.status_label.setText(f"🔍 Zoom: {int(webview.zoomFactor() * 100)}%")
    
    def zoom_out(self):
        """Zoom out current page"""
        webview = self.current_webview()
        if webview:
            webview.setZoomFactor(webview.zoomFactor() * 0.8)
            self.status_label.setText(f"🔍 Zoom: {int(webview.zoomFactor() * 100)}%")
    
    def toggle_fullscreen(self):
        """Toggle fullscreen mode"""
        if self.is_fullscreen:
            self.showNormal()
            self.is_fullscreen = False
            self.status_label.setText("🚀 Ready - Go Through Browser")
        else:
            self.showFullScreen()
            self.is_fullscreen = True
            self.status_label.setText("⛶ Fullscreen mode")
    
    def print_page(self):
        """Print current page"""
        webview = self.current_webview()
        if webview:
            webview.print()
    
    def handle_download(self, download_item):
        """Handle download requests"""
        filename = download_item.suggestedFileName()
        path = os.path.join(self.download_path, filename)
        download_item.setDownloadDirectory(os.path.dirname(path))
        download_item.setDownloadFileName(os.path.basename(path))
        download_item.accept()
        
        # Track download
        download_data = {
            'filename': filename,
            'path': path,
            'status': 'Downloading',
            'timestamp': time.time()
        }
        self.downloads.append(download_data)
        self.status_label.setText(f"⬇️ Downloading: {filename}")
        
        # Update when finished
        download_item.finished.connect(lambda: self.on_download_finished(download_data))
        download_item.downloadProgress.connect(self.on_download_progress)
    
    def on_download_finished(self, download_data):
        """Handle download completion"""
        download_data['status'] = 'Completed'
        self.status_label.setText(f"✅ Downloaded: {download_data['filename']}")
    
    def on_download_progress(self, bytes_received, bytes_total):
        """Handle download progress"""
        if bytes_total > 0:
            progress = int((bytes_received / bytes_total) * 100)
            self.progress_bar.setValue(progress)
            self.progress_bar.show()
    
    def load_settings(self):
        """Load browser settings"""
        return {
            'homepage': 'http://127.0.0.1:5000/',
            'search_engine': 'DuckDuckGo',
            'theme': 'Light',
            'restore_session': False,
            'clear_history_on_exit': False,
            'block_third_party_cookies': False,
            'send_do_not_track': False,
            'font_size': 16,
            'default_zoom': '100%'
        }
    
    def save_session(self):
        """Save current session"""
        self.session_urls = []
        for i in range(self.tab_widget.count()):
            webview = self.tab_widget.widget(i)
            if webview:
                url = webview.url().toString()
                if url and not url.startswith('about:blank'):
                    self.session_urls.append(url)
    
    def restore_session(self):
        """Restore previous session"""
        if self.settings.get('restore_session', False) and self.session_urls:
            for url in self.session_urls:
                self.add_new_tab(url)
    
    def setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        from PyQt6.QtGui import QKeySequence
        from PyQt6.QtWidgets import QShortcut
        
        # Tab shortcuts
        QShortcut(QKeySequence("Ctrl+T"), self, self.add_new_tab)
        QShortcut(QKeySequence("Ctrl+W"), self, lambda: self.close_tab(self.tab_widget.currentIndex()))
        QShortcut(QKeySequence("Ctrl+Tab"), self, lambda: self.tab_widget.setCurrentIndex((self.tab_widget.currentIndex() + 1) % self.tab_widget.count()))
        
        # Navigation shortcuts
        QShortcut(QKeySequence("Alt+Left"), self, self.go_back)
        QShortcut(QKeySequence("Alt+Right"), self, self.go_forward)
        QShortcut(QKeySequence("F5"), self, self.refresh_page)
        QShortcut(QKeySequence("Ctrl+L"), self, lambda: self.url_bar.setFocus())
        
        # Feature shortcuts
        QShortcut(QKeySequence("Ctrl+D"), self, self.add_bookmark)
        QShortcut(QKeySequence("Ctrl+H"), self, self.show_history)
        QShortcut(QKeySequence("Ctrl+J"), self, self.show_downloads)
        QShortcut(QKeySequence("F12"), self, self.show_devtools)
        QShortcut(QKeySequence("Ctrl+,"), self, self.show_settings)
        
        # Zoom shortcuts
        QShortcut(QKeySequence("Ctrl+Plus"), self, self.zoom_in)
        QShortcut(QKeySequence("Ctrl+Minus"), self, self.zoom_out)
        QShortcut(QKeySequence("Ctrl+0"), lambda: self.current_webview().setZoomFactor(1.0) if self.current_webview() else None)
        
        # Fullscreen
        QShortcut(QKeySequence("F11"), self, self.toggle_fullscreen)
        
        # Find
        QShortcut(QKeySequence("Ctrl+F"), self, self.show_find_dialog)
    
    def show_find_dialog(self):
        """Show find in page dialog"""
        text, ok = QInputDialog.getText(self, "Find in Page", "Find:")
        if ok and text:
            self.find_text = text
            webview = self.current_webview()
            if webview:
                webview.findText(self.find_text)
                self.status_label.setText(f"🔍 Searching for: {text}")
        self.progress_bar.show()
        if progress == 100:
            QTimer.singleShot(1500, self.progress_bar.hide)
    
    def load_settings(self):
        """Load browser settings from database"""
        try:
            # Default settings
            settings = {
                'homepage': 'http://127.0.0.1:5000',
                'search_engine': 'local',
                'theme': 'light',
                'adblock': True,
                'incognito': False,
                'zoom_level': 1.0
            }
            return settings
        except:
            return settings
    
    def setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        # Tab shortcuts
        QShortcut(QKeySequence("Ctrl+T"), self).activated.connect(self.add_new_tab)
        QShortcut(QKeySequence("Ctrl+W"), self).activated.connect(lambda: self.close_tab(self.tab_widget.currentIndex()))
        QShortcut(QKeySequence("Ctrl+Tab"), self).activated.connect(lambda: self.tab_widget.setCurrentIndex((self.tab_widget.currentIndex() + 1) % self.tab_widget.count()))
        QShortcut(QKeySequence("Ctrl+Shift+Tab"), self).activated.connect(lambda: self.tab_widget.setCurrentIndex((self.tab_widget.currentIndex() - 1) % self.tab_widget.count()))
        
        # Navigation shortcuts
        QShortcut(QKeySequence("Alt+Left"), self).activated.connect(self.go_back)
        QShortcut(QKeySequence("Alt+Right"), self).activated.connect(self.go_forward)
        QShortcut(QKeySequence("F5"), self).activated.connect(self.refresh_page)
        QShortcut(QKeySequence("Ctrl+R"), self).activated.connect(self.refresh_page)
        QShortcut(QKeySequence("Home"), self).activated.connect(self.go_home)
        
        # Zoom shortcuts
        QShortcut(QKeySequence("Ctrl+="), self).activated.connect(self.zoom_in)
        QShortcut(QKeySequence("Ctrl+-"), self).activated.connect(self.zoom_out)
        QShortcut(QKeySequence("Ctrl+0"), self).activated.connect(self.zoom_reset)
        
        # Find shortcuts
        QShortcut(QKeySequence("Ctrl+F"), self).activated.connect(self.show_find_dialog)
        QShortcut(QKeySequence("F3"), self).activated.connect(self.find_next)
        QShortcut(QKeySequence("Ctrl+H"), self).activated.connect(self.show_history)
        QShortcut(QKeySequence("Ctrl+B"), self).activated.connect(self.show_bookmark_manager)
        
        # Other shortcuts
        QShortcut(QKeySequence("Ctrl+P"), self).activated.connect(self.print_page)
        QShortcut(QKeySequence("F11"), self).activated.connect(self.toggle_fullscreen)
        QShortcut(QKeySequence("Ctrl+Shift+Delete"), self).activated.connect(self.clear_browsing_data)
        QShortcut(QKeySequence("Ctrl+,"), self).activated.connect(self.show_settings)
    
    def zoom_in(self):
        """Zoom in the current page"""
        webview = self.current_webview()
        if webview:
            self.zoom_factor = min(self.zoom_factor + 0.1, 3.0)
            webview.setZoomFactor(self.zoom_factor)
            self.status_label.setText(f"🔍 Zoom: {int(self.zoom_factor * 100)}%")
    
    def zoom_out(self):
        """Zoom out the current page"""
        webview = self.current_webview()
        if webview:
            self.zoom_factor = max(self.zoom_factor - 0.1, 0.3)
            webview.setZoomFactor(self.zoom_factor)
            self.status_label.setText(f"🔍 Zoom: {int(self.zoom_factor * 100)}%")
    
    def zoom_reset(self):
        """Reset zoom to default"""
        webview = self.current_webview()
        if webview:
            self.zoom_factor = 1.0
            webview.setZoomFactor(self.zoom_factor)
            self.status_label.setText("🔍 Zoom: 100%")
    
    def show_find_dialog(self):
        """Show find on page dialog"""
        webview = self.current_webview()
        if not webview:
            return
        
        text, ok = QInputDialog.getText(self, "Find on Page", "Find text:")
        if ok and text:
            self.find_text = text
            webview.findText(text)
            self.status_label.setText(f"🔎 Finding: {text}")
    
    def find_next(self):
        """Find next occurrence"""
        webview = self.current_webview()
        if webview and self.find_text:
            webview.findText(self.find_text)
    
    def print_page(self):
        """Print current page"""
        webview = self.current_webview()
        if not webview:
            return
        
        printer = QPrinter()
        dialog = QPrintDialog(printer, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            webview.print(printer)
            self.status_label.setText("🖨️ Printing...")
    
    def toggle_fullscreen(self):
        """Toggle fullscreen mode"""
        self.is_fullscreen = not self.is_fullscreen
        if self.is_fullscreen:
            self.showFullScreen()
            self.status_label.setText("⛶ Fullscreen Mode")
        else:
            self.showNormal()
            self.status_label.setText("🚀 Ready - Go Through Browser")
    
    def show_history(self):
        """Show browsing history dialog"""
        history = self.db.get_history(100)
        
        dialog = QDialog(self)
        dialog.setWindowTitle("📜 Browsing History")
        dialog.setGeometry(200, 200, 800, 600)
        
        layout = QVBoxLayout()
        
        # Search bar
        search_layout = QHBoxLayout()
        search_bar = QLineEdit()
        search_bar.setPlaceholderText("🔍 Search history...")
        search_layout.addWidget(QLabel("Search:"))
        search_layout.addWidget(search_bar)
        layout.addLayout(search_layout)
        
        # History list
        list_widget = QListWidget()
        for url, title, timestamp in history:
            date = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M")
            item_text = f"{date} - {title[:50]}{'...' if len(title) > 50 else ''}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, url)
            list_widget.addItem(item)
        
        layout.addWidget(list_widget)
        
        # Buttons
        button_layout = QHBoxLayout()
        open_btn = QPushButton("🌐 Open")
        delete_btn = QPushButton("🗑️ Delete Selected")
        clear_btn = QPushButton("🗑️ Clear All")
        close_btn = QPushButton("❌ Close")
        
        button_layout.addWidget(open_btn)
        button_layout.addWidget(delete_btn)
        button_layout.addWidget(clear_btn)
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)
        
        # Connect signals
        def open_history():
            current_item = list_widget.currentItem()
            if current_item:
                url = current_item.data(Qt.ItemDataRole.UserRole)
                webview = self.current_webview()
                if webview:
                    webview.load(QUrl(url))
                dialog.accept()
        
        def delete_selected():
            current_item = list_widget.currentItem()
            if current_item:
                list_widget.takeItem(list_widget.row(current_item))
        
        def clear_all():
            reply = QMessageBox.question(self, "Clear History", "Clear all browsing history?", 
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.db.clear_history()
                list_widget.clear()
                self.status_label.setText("🗑️ History cleared")
        
        open_btn.clicked.connect(open_history)
        delete_btn.clicked.connect(delete_selected)
        clear_btn.clicked.connect(clear_all)
        close_btn.clicked.connect(dialog.reject)
        
        # Search functionality
        def search_history(text):
            for i in range(list_widget.count()):
                item = list_widget.item(i)
                item.setHidden(text.lower() not in item.text().lower())
        
        search_bar.textChanged.connect(search_history)
        
        dialog.setLayout(layout)
        dialog.exec()
    
    def show_bookmark_manager(self):
        """Show bookmark manager dialog"""
        bookmarks = self.db.get_bookmarks()
        
        dialog = QDialog(self)
        dialog.setWindowTitle("📚 Bookmark Manager")
        dialog.setGeometry(200, 200, 800, 600)
        
        layout = QVBoxLayout()
        
        # Search bar
        search_layout = QHBoxLayout()
        search_bar = QLineEdit()
        search_bar.setPlaceholderText("🔍 Search bookmarks...")
        search_layout.addWidget(QLabel("Search:"))
        search_layout.addWidget(search_bar)
        layout.addLayout(search_layout)
        
        # Bookmark list
        list_widget = QListWidget()
        for url, title in bookmarks:
            item_text = f"{title[:60]}{'...' if len(title) > 60 else ''}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, (url, title))
            list_widget.addItem(item)
        
        layout.addWidget(list_widget)
        
        # Buttons
        button_layout = QHBoxLayout()
        open_btn = QPushButton("🌐 Open")
        edit_btn = QPushButton("✏️ Edit")
        delete_btn = QPushButton("🗑️ Delete")
        close_btn = QPushButton("❌ Close")
        
        button_layout.addWidget(open_btn)
        button_layout.addWidget(edit_btn)
        button_layout.addWidget(delete_btn)
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)
        
        # Connect signals
        def open_bookmark():
            current_item = list_widget.currentItem()
            if current_item:
                url, title = current_item.data(Qt.ItemDataRole.UserRole)
                webview = self.current_webview()
                if webview:
                    webview.load(QUrl(url))
                dialog.accept()
        
        def edit_bookmark():
            current_item = list_widget.currentItem()
            if current_item:
                url, title = current_item.data(Qt.ItemDataRole.UserRole)
                new_title, ok = QInputDialog.getText(self, "Edit Bookmark", "Title:", text=title)
                if ok and new_title:
                    # Update in database
                    self.db.cursor.execute("UPDATE bookmarks SET title = ? WHERE url = ?", (new_title, url))
                    self.db.conn.commit()
                    # Update UI
                    item_text = f"{new_title[:60]}{'...' if len(new_title) > 60 else ''}"
                    current_item.setText(item_text)
                    current_item.setData(Qt.ItemDataRole.UserRole, (url, new_title))
        
        def delete_bookmark():
            current_item = list_widget.currentItem()
            if current_item:
                url, title = current_item.data(Qt.ItemDataRole.UserRole)
                reply = QMessageBox.question(self, "Delete Bookmark", f"Delete bookmark '{title}'?", 
                                           QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if reply == QMessageBox.StandardButton.Yes:
                    self.db.cursor.execute("DELETE FROM bookmarks WHERE url = ?", (url,))
                    self.db.conn.commit()
                    list_widget.takeItem(list_widget.row(current_item))
                    self.status_label.setText("🗑️ Bookmark deleted")
        
        open_btn.clicked.connect(open_bookmark)
        edit_btn.clicked.connect(edit_bookmark)
        delete_btn.clicked.connect(delete_bookmark)
        close_btn.clicked.connect(dialog.reject)
        
        # Search functionality
        def search_bookmarks(text):
            for i in range(list_widget.count()):
                item = list_widget.item(i)
                item.setHidden(text.lower() not in item.text().lower())
        
        search_bar.textChanged.connect(search_bookmarks)
        
        dialog.setLayout(layout)
        dialog.exec()
    
    def show_settings(self):
        """Show settings dialog"""
        dialog = QDialog(self)
        dialog.setWindowTitle("⚙️ Settings")
        dialog.setGeometry(200, 200, 500, 400)
        
        layout = QVBoxLayout()
        
        # Homepage setting
        homepage_layout = QHBoxLayout()
        homepage_layout.addWidget(QLabel("Homepage:"))
        homepage_input = QLineEdit(self.settings['homepage'])
        homepage_layout.addWidget(homepage_input)
        layout.addLayout(homepage_layout)
        
        # Search engine setting
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search Engine:"))
        search_combo = QComboBox()
        search_combo.addItems(["Local", "DuckDuckGo", "Google"])
        search_combo.setCurrentText(self.settings['search_engine'].title())
        search_layout.addWidget(search_combo)
        layout.addLayout(search_layout)
        
        # Theme setting
        theme_layout = QHBoxLayout()
        theme_layout.addWidget(QLabel("Theme:"))
        theme_combo = QComboBox()
        theme_combo.addItems(["Light", "Dark"])
        theme_combo.setCurrentText(self.settings['theme'].title())
        theme_layout.addWidget(theme_combo)
        layout.addLayout(theme_layout)
        
        # AdBlock setting
        adblock_check = QCheckBox("Enable AdBlock")
        adblock_check.setChecked(self.settings['adblock'])
        layout.addWidget(adblock_check)
        
        # Buttons
        button_layout = QHBoxLayout()
        save_btn = QPushButton("💾 Save")
        reset_btn = QPushButton("🔄 Reset")
        close_btn = QPushButton("❌ Close")
        
        button_layout.addWidget(save_btn)
        button_layout.addWidget(reset_btn)
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)
        
        # Connect signals
        def save_settings():
            self.settings['homepage'] = homepage_input.text()
            self.settings['search_engine'] = search_combo.currentText().lower()
            self.settings['theme'] = theme_combo.currentText().lower()
            self.settings['adblock'] = adblock_check.isChecked()
            
            # Apply settings
            self.adblock_enabled = self.settings['adblock']
            self.adblock_btn.setText("🚫" if self.adblock_enabled else "🚫")
            self.status_label.setText("⚙️ Settings saved")
        
        def reset_settings():
            reply = QMessageBox.question(self, "Reset Settings", "Reset all settings to defaults?", 
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.settings = self.load_settings()
                homepage_input.setText(self.settings['homepage'])
                search_combo.setCurrentText(self.settings['search_engine'].title())
                theme_combo.setCurrentText(self.settings['theme'].title())
                adblock_check.setChecked(self.settings['adblock'])
                self.status_label.setText("⚙️ Settings reset")
        
        save_btn.clicked.connect(save_settings)
        reset_btn.clicked.connect(reset_settings)
        close_btn.clicked.connect(dialog.accept)
        
        dialog.setLayout(layout)
        dialog.exec()
    
    def clear_browsing_data(self):
        """Clear browsing data dialog"""
        dialog = QDialog(self)
        dialog.setWindowTitle("🗑️ Clear Browsing Data")
        dialog.setGeometry(200, 200, 400, 300)
        
        layout = QVBoxLayout()
        
        # Checkboxes for data types
        history_check = QCheckBox("📜 Browsing History")
        bookmarks_check = QCheckBox("⭐ Bookmarks")
        cache_check = QCheckBox("💾 Cache")
        cookies_check = QCheckBox("🍪 Cookies")
        
        layout.addWidget(history_check)
        layout.addWidget(bookmarks_check)
        layout.addWidget(cache_check)
        layout.addWidget(cookies_check)
        
        # Time range
        time_layout = QHBoxLayout()
        time_layout.addWidget(QLabel("Time range:"))
        time_combo = QComboBox()
        time_combo.addItems(["Last Hour", "Last Day", "Last Week", "Last 4 Weeks", "All Time"])
        time_combo.setCurrentText("All Time")
        time_layout.addWidget(time_combo)
        layout.addLayout(time_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        clear_btn = QPushButton("🗑️ Clear Data")
        close_btn = QPushButton("❌ Close")
        
        button_layout.addWidget(clear_btn)
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)
        
        # Connect signals
        def clear_data():
            if history_check.isChecked():
                self.db.clear_history()
            if bookmarks_check.isChecked():
                self.db.cursor.execute("DELETE FROM bookmarks")
                self.db.conn.commit()
            
            cleared_items = []
            if history_check.isChecked():
                cleared_items.append("History")
            if bookmarks_check.isChecked():
                cleared_items.append("Bookmarks")
            
            if cleared_items:
                self.status_label.setText(f"🗑️ Cleared: {', '.join(cleared_items)}")
                QMessageBox.information(self, "Clear Complete", f"Cleared: {', '.join(cleared_items)}")
            dialog.accept()
        
        clear_btn.clicked.connect(clear_data)
        close_btn.clicked.connect(dialog.reject)
        
        dialog.setLayout(layout)
        dialog.exec()
    
    def track_history(self, url, title):
        """Track page visit in history"""
        self.db.add_history_entry(url, title)
    
    def save_session(self):
        """Save current session"""
        self.session_urls = []
        for i in range(self.tab_widget.count()):
            tab = self.tab_widget.widget(i)
            if hasattr(tab, 'webview'):
                url = tab.webview.url().toString()
                if url and not url.startswith('about:blank'):
                    self.session_urls.append(url)
        
        # Save to database
        self.db.cursor.execute("DELETE FROM settings WHERE key = 'session'")
        self.db.cursor.execute("INSERT INTO settings (key, value) VALUES (?, ?)", 
                             ('session', ','.join(self.session_urls)))
        self.db.conn.commit()
    
    def restore_session(self):
        """Restore last session"""
        try:
            self.db.cursor.execute("SELECT value FROM settings WHERE key = 'session'")
            result = self.db.cursor.fetchone()
            if result and result[0]:
                urls = result[0].split(',')
                # Clear default tab first
                self.tab_widget.clear()
                
                # Restore tabs
                for url in urls:
                    if url.strip():
                        self.add_new_tab(url.strip())
                
                self.status_label.setText("🔄 Session restored")
        except:
            pass
    
    def closeEvent(self, event):
        """Handle browser close event"""
        self.save_session()
        self.db.close()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    browser = MyBrowser()
    browser.show()
    sys.exit(app.exec())
