from flask import Flask, request, render_template_string, render_template, jsonify
from database import BrowserDatabase
import sys
import os

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# Set template folder to resource path
template_path = resource_path('')
app = Flask(__name__, template_folder=template_path)
db = BrowserDatabase()

# SIMPLIFIED SEARCH TEMPLATE - DIRECT RESULTS
SEARCH_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>🔍 {{ query|default('Search') }} - Go Through</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            padding: 20px;
            color: white;
        }
        .container {
            max-width: 900px;
            width: 100%;
        }
        .search-box {
            background: rgba(255,255,255,0.95);
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }
        .search-box h1 {
            color: #2c3e50;
            margin-bottom: 20px;
            font-size: 28px;
        }
        .search-box input {
            width: 100%;
            padding: 15px 20px;
            border: 2px solid #3498db;
            border-radius: 10px;
            font-size: 16px;
            margin-bottom: 20px;
        }
        .results {
            background: rgba(255,255,255,0.95);
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }
        .result-item {
            padding: 15px 0;
            border-bottom: 1px solid #eee;
            text-decoration: none;
            color: #2c3e50;
            display: block;
            transition: all 0.3s;
        }
        .result-item:hover {
            background: #f8f9fa;
            padding-left: 10px;
        }
        .result-item:last-child {
            border-bottom: none;
        }
        .result-title {
            font-size: 18px;
            font-weight: 600;
            color: #3498db;
            margin-bottom: 5px;
        }
        .result-url {
            font-size: 14px;
            color: #6c757d;
            word-break: break-all;
        }
        .no-results {
            text-align: center;
            padding: 40px;
            color: #2c3e50;
        }
        .web-search-btn {
            display: inline-block;
            background: #3498db;
            color: white;
            padding: 15px 30px;
            border-radius: 10px;
            text-decoration: none;
            font-weight: 600;
            margin-top: 20px;
            transition: all 0.3s;
        }
        .web-search-btn:hover {
            background: #2980b9;
            transform: translateY(-2px);
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="search-box">
            <h1>🔍 {{ query|default('Search') }}</h1>
            <input type="text" value="{{ query }}" onkeypress="if(event.key==='Enter'){window.location.href='/search?q='+this.value}">
        </div>
        
        {% if query %}
        <div class="results">
            {% if local_results %}
                <h3>📚 Local Results ({{ results|length }})</h3>
                {% for title, url in results %}
                <a href="{{ url }}" class="result-item">
                    <div class="result-title">{{ title }}</div>
                    <div class="result-url">{{ url }}</div>
                </a>
                {% endfor %}
            {% else %}
                <div class="no-results">
                    <h3>❌ No local results found</h3>
                    <p>Your bookmarks and history don't contain anything matching "{{ query }}"</p>
                    <a href="https://www.duckduckgo.com/?q={{ query }}" class="web-search-btn">
                        🔍 Search on the Web
                    </a>
                </div>
            {% endif %}
        </div>
        {% endif %}
    </div>
</body>
</html>
"""

@app.route('/')
def homepage():
    try:
        return render_template('homepage.html')
    except Exception as e:
        # Fallback to manual file reading if render_template fails
        homepage_path = resource_path('homepage.html')
        try:
            with open(homepage_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            return f"<h1>Homepage not found</h1><p>Error: {str(e)}</p><p>Please ensure homepage.html is in the same directory as the browser.</p>"

@app.route('/suggest')
def suggest():
    query = request.args.get('q', '').lower().strip()
    suggestions = []
    
    if len(query) >= 2:
        try:
            # Get recent history and bookmarks for suggestions
            history = db.get_history(limit=20)
            bookmarks = db.get_bookmarks()
            
            # Find matching items
            for url, title in history:
                if query in title.lower() or query in url.lower():
                    suggestions.append([title, url])
            
            for url, title in bookmarks:
                if query in title.lower() or query in url.lower():
                    suggestions.append([title, url])
            
            # Remove duplicates and limit to 5
            seen = set()
            unique_suggestions = []
            for item in suggestions:
                if item[0] not in seen:
                    seen.add(item[0])
                    unique_suggestions.append(item[0])
                    if len(unique_suggestions) >= 5:
                        break
                        
        except:
            pass
    
    return jsonify(unique_suggestions)

@app.route('/search')
def search():
    query = request.args.get('q', '').lower().strip()
    results = []
    local_results = False
    
    if len(query) >= 2:
        try:
            # Open fresh database connection to prevent connection issues
            fresh_db = BrowserDatabase()
            
            # Search bookmarks first with fuzzy matching
            bookmarks = fresh_db.get_bookmarks()
            bookmark_results = [(title, url) for url, title in bookmarks 
                              if query in title.lower() or query in url.lower()]
            
            # Search history second with fuzzy matching
            history = fresh_db.get_history(limit=50)
            history_results = [(title, url) for url, title in history 
                             if query in title.lower() or query in url.lower()]
            
            # Combine results, prioritize bookmarks
            results = bookmark_results + [h for h in history_results if h not in bookmark_results]
            
            if results:
                local_results = True
            else:
                local_results = False
                
            fresh_db.close()
        except Exception as e:
            print(f"Search error: {e}")
            pass
    
    return render_template_string(SEARCH_TEMPLATE, query=query, results=results, local_results=local_results)

if __name__ == '__main__':
    print("🚀 Go Through Server running on http://127.0.0.1:5000")
    app.run(host='127.0.0.1', port=5000, debug=False)
