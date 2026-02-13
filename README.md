🚀 Go Through Browser
A high-performance, privacy-focused web browser built with Python, PyQt6, and a Flask-powered backend.

"Go Through" isn't just a simple web-view wrapper; it is a full-stack desktop application featuring an integrated database engine, a local search server for fuzzy-matching your history, and custom network-level ad blocking.

✨ Key Features
Engine: Powered by QtWebEngine (Chromium) for modern, fast web rendering.

Local Fuzzy Search: An internal Flask server (search_server.py) that queries your local bookmarks and history using fuzzy matching before defaulting to the web.

Integrated Ad-Blocker: Custom request interceptor that blocks tracking domains (e.g., DoubleClick) at the source.

Robust Data Management: Built with a SQLite backend to handle history, bookmarks, and downloads with a dedicated "Nuclear Option" to wipe all data instantly for privacy.

Session Persistence: Features a custom session-saver that restores all your tabs automatically when you restart.

Development Ready: Includes bundled logic for PyInstaller (sys.frozen checks) to ensure the app is portable as a standalone executable.

🛠️ Tech Stack
Frontend: PyQt6 (Desktop UI) & CSS3 (Custom Gradient Homepage)

Backend Server: Flask (Local Search API)

Database: SQLite3

Packaging: PyInstaller

📁 Project Structure
mybrowser.py: The core application, UI layout, and Tab management.

database.py: The Data Access Layer handling all SQL transactions.

search_server.py: A micro-service providing local search results via HTML templates.

homepage.html: A modern, interactive start page with CSS animations.

mybrowser.spec: Configuration for building the standalone executable.

🚀 Getting Started
1. Install Dependencies
Bash
pip install PyQt6 PyQt6-WebEngine flask
2. Run the Application
Bash
python mybrowser.py
3. Build Your Own Executable
To bundle the project into a single .exe or .app file:

Bash
pyinstaller mybrowser.spec
🧠 Development Philosophy
This project was a deep dive into Browser Architecture. The focus was on decoupling the UI from the data layer and understanding how to intercept network requests for privacy. By running a local Flask server alongside a PyQt UI, I explored how desktop applications can leverage web technologies to create a seamless user experience.
