"""
DLP Enterprise Incident Management Server & Web Dashboard
---------------------------------------------------------
Lightweight, zero-dependency, on-demand incident server.
- Built strictly with Python standard libraries (no pip dependencies required).
- Embedded SQLite database for reliable incident recording.
- Modern real-time web dashboard (HTML5 + CSS + JavaScript).
- Ready for local loopback testing (127.0.0.1) and LAN office network demo.
"""

import os
import sys
import json
import time
import socket
import sqlite3
import datetime
import urllib.parse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import csv
import io

PORT = 5000
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dlp_incidents.db")


def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            hostname TEXT,
            username TEXT,
            process TEXT,
            pid INTEGER,
            file_path TEXT,
            file_name TEXT,
            file_size_bytes INTEGER DEFAULT 0,
            file_size_str TEXT,
            reason TEXT,
            action_taken TEXT,
            sha256 TEXT
        )
    """)
    conn.commit()
    conn.close()


def format_size(bytes_val: int) -> str:
    if bytes_val <= 0:
        return "N/A"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.1f} TB"


def insert_incident(data: dict) -> int:
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    timestamp = data.get("timestamp") or datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    hostname = data.get("host") or data.get("hostname") or "Unknown-Host"
    username = data.get("user") or data.get("username") or "Unknown-User"
    process = data.get("process") or "Unknown.exe"
    pid = data.get("pid") or 0
    file_path = data.get("file") or data.get("file_path") or ""
    file_name = data.get("file_name") or os.path.basename(file_path) if file_path else "Unknown"
    size_bytes = data.get("file_size_bytes") or data.get("file_size") or 0
    try:
        size_bytes = int(size_bytes)
    except Exception:
        size_bytes = 0
    size_str = format_size(size_bytes)
    reason = data.get("reason") or "Unauthorized file access detected"
    action = data.get("action_taken") or data.get("action") or "TERMINATED"
    sha256 = data.get("partial_sha256") or data.get("sha256") or "N/A"

    cursor.execute("""
        INSERT INTO incidents (
            timestamp, hostname, username, process, pid,
            file_path, file_name, file_size_bytes, file_size_str,
            reason, action_taken, sha256
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        timestamp, hostname, username, process, pid,
        file_path, file_name, size_bytes, size_str,
        reason, action, sha256
    ))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id


def get_incidents(limit=200):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM incidents ORDER BY id DESC LIMIT ?", (limit,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def get_stats():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM incidents")
    total_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT hostname) FROM incidents")
    unique_hosts = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT username) FROM incidents")
    unique_users = cursor.fetchone()[0]

    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    cursor.execute("SELECT COUNT(*) FROM incidents WHERE timestamp LIKE ?", (f"{today_str}%",))
    today_count = cursor.fetchone()[0]

    conn.close()
    return {
        "total": total_count,
        "unique_hosts": unique_hosts,
        "unique_users": unique_users,
        "today_count": today_count
    }


def clear_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM incidents")
    conn.commit()
    conn.close()


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


# Complete, self-contained HTML Dashboard
HTML_DASHBOARD = r"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DLP Incident Management Center</title>
    <style>
        :root {
            --bg-primary: #0f172a;
            --bg-card: #1e293b;
            --bg-card-hover: #334155;
            --border-color: #334155;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --accent-red: #ef4444;
            --accent-red-bg: rgba(239, 68, 68, 0.15);
            --accent-green: #10b981;
            --accent-green-bg: rgba(16, 185, 129, 0.15);
            --accent-blue: #3b82f6;
            --accent-amber: #f59e0b;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
        body { background-color: var(--bg-primary); color: var(--text-main); padding: 24px; min-height: 100vh; }
        
        .container { max-width: 1400px; margin: 0 auto; }
        
        /* Header */
        header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; padding-bottom: 16px; border-bottom: 1px solid var(--border-color); }
        .logo-group { display: flex; align-items: center; gap: 14px; }
        .shield-icon { font-size: 32px; }
        h1 { font-size: 24px; font-weight: 700; letter-spacing: -0.5px; }
        .subtitle { font-size: 13px; color: var(--text-muted); margin-top: 2px; }
        
        .header-actions { display: flex; align-items: center; gap: 12px; }
        .status-pill { display: flex; align-items: center; gap: 8px; background: var(--accent-green-bg); color: var(--accent-green); padding: 6px 14px; border-radius: 999px; font-size: 12px; font-weight: 600; border: 1px solid rgba(16, 185, 129, 0.3); }
        .pulse-dot { width: 8px; height: 8px; background: var(--accent-green); border-radius: 50%; box-shadow: 0 0 8px var(--accent-green); animation: pulse 1.8s infinite; }
        @keyframes pulse { 0% { opacity: 0.4; } 50% { opacity: 1; } 100% { opacity: 0.4; } }

        /* Stats Cards */
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 24px; }
        .stat-card { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 12px; padding: 18px 20px; transition: transform 0.2s, border-color 0.2s; }
        .stat-card:hover { transform: translateY(-2px); border-color: var(--accent-blue); }
        .stat-label { font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-muted); margin-bottom: 6px; }
        .stat-value { font-size: 30px; font-weight: 700; color: var(--text-main); }
        .stat-value.red { color: var(--accent-red); }
        .stat-value.blue { color: var(--accent-blue); }
        .stat-value.green { color: var(--accent-green); }
        .stat-value.amber { color: var(--accent-amber); }

        /* Toolbar */
        .toolbar { display: flex; justify-content: space-between; align-items: center; gap: 16px; margin-bottom: 16px; flex-wrap: wrap; }
        .search-box { flex: 1; min-width: 260px; max-width: 450px; position: relative; }
        .search-input { width: 100%; background: var(--bg-card); border: 1px solid var(--border-color); color: var(--text-main); padding: 10px 16px 10px 38px; border-radius: 8px; font-size: 14px; outline: none; transition: border-color 0.2s; }
        .search-input:focus { border-color: var(--accent-blue); }
        .search-icon { position: absolute; left: 12px; top: 50%; transform: translateY(-50%); font-size: 14px; color: var(--text-muted); }

        .btn-group { display: flex; gap: 10px; }
        button { cursor: pointer; border: none; font-size: 13px; font-weight: 600; border-radius: 8px; padding: 10px 16px; display: inline-flex; align-items: center; gap: 8px; transition: all 0.2s; }
        .btn-primary { background: var(--accent-blue); color: white; }
        .btn-primary:hover { background: #2563eb; }
        .btn-secondary { background: var(--bg-card); color: var(--text-main); border: 1px solid var(--border-color); }
        .btn-secondary:hover { background: var(--bg-card-hover); }
        .btn-danger { background: var(--accent-red-bg); color: var(--accent-red); border: 1px solid rgba(239, 68, 68, 0.3); }
        .btn-danger:hover { background: var(--accent-red); color: white; }

        /* Table */
        .table-card { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 12px; overflow: hidden; }
        table { width: 100%; border-collapse: collapse; text-align: left; font-size: 13px; }
        thead { background: rgba(15, 23, 42, 0.6); border-bottom: 1px solid var(--border-color); }
        th { padding: 14px 16px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; font-size: 11px; letter-spacing: 0.5px; }
        td { padding: 14px 16px; border-bottom: 1px solid var(--border-color); vertical-align: middle; }
        tr:last-child td { border-bottom: none; }
        tbody tr { transition: background 0.15s; }
        tbody tr:hover { background: rgba(51, 65, 85, 0.4); }
        .new-row-flash { animation: flashRed 1.8s ease-out; }
        @keyframes flashRed { 0% { background: rgba(239, 68, 68, 0.35); } 100% { background: transparent; } }

        /* Badges & Elements */
        .badge { display: inline-block; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; }
        .badge-red { background: var(--accent-red-bg); color: var(--accent-red); border: 1px solid rgba(239, 68, 68, 0.4); }
        .badge-gray { background: #334155; color: #cbd5e1; }
        .code-pill { background: #0f172a; padding: 3px 7px; border-radius: 4px; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12px; color: #38bdf8; }
        .host-user { display: flex; flex-direction: column; }
        .host-name { font-weight: 600; color: var(--text-main); }
        .user-name { font-size: 11px; color: var(--text-muted); }
        .file-info { display: flex; flex-direction: column; }
        .file-name { font-weight: 600; color: #f43f5e; display: flex; align-items: center; gap: 6px; }
        .file-path { font-size: 11px; color: var(--text-muted); max-width: 380px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

        .empty-state { text-align: center; padding: 60px 20px; color: var(--text-muted); }
        .empty-icon { font-size: 42px; margin-bottom: 12px; opacity: 0.6; }
        
        /* Footer */
        footer { margin-top: 24px; text-align: center; font-size: 12px; color: var(--text-muted); }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo-group">
                <span class="shield-icon">🛡️</span>
                <div>
                    <h1>DLP Incident Management Center</h1>
                    <div class="subtitle">Real-Time 3D Asset Leak Protection & Endpoint Audit</div>
                </div>
            </div>
            <div class="header-actions">
                <div class="status-pill">
                    <span class="pulse-dot"></span>
                    <span>MONITOR LISTENING</span>
                </div>
            </div>
        </header>

        <!-- Stats Overview -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Total Leaks Blocked</div>
                <div class="stat-value red" id="stat-total">0</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Blocked Today</div>
                <div class="stat-value amber" id="stat-today">0</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Unique Workstations</div>
                <div class="stat-value blue" id="stat-hosts">0</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Identified Artists</div>
                <div class="stat-value green" id="stat-users">0</div>
            </div>
        </div>

        <!-- Controls Toolbar -->
        <div class="toolbar">
            <div class="search-box">
                <span class="search-icon">🔍</span>
                <input type="text" id="searchInput" class="search-input" placeholder="Filter by computer, artist, file name or reason..." oninput="filterIncidents()">
            </div>
            <div class="btn-group">
                <button class="btn-primary" onclick="triggerTestSimulation()">
                    <span>⚡</span> Simulate Test Incident
                </button>
                <button class="btn-secondary" onclick="exportCSV()">
                    <span>📥</span> Export CSV
                </button>
                <button class="btn-danger" onclick="clearLogs()">
                    <span>🗑️</span> Clear Logs
                </button>
            </div>
        </div>

        <!-- Incident Table -->
        <div class="table-card">
            <table>
                <thead>
                    <tr>
                        <th style="width: 100px;">Action</th>
                        <th style="width: 155px;">Timestamp</th>
                        <th style="width: 180px;">Workstation / User</th>
                        <th style="width: 140px;">Process</th>
                        <th>Blocked Asset</th>
                        <th style="width: 90px;">Size</th>
                        <th>Security Reason</th>
                    </tr>
                </thead>
                <tbody id="incidentTableBody">
                    <tr>
                        <td colspan="7">
                            <div class="empty-state">
                                <div class="empty-icon">🛡️</div>
                                <h3>No security violations recorded yet.</h3>
                                <p style="font-size: 13px; margin-top: 4px;">Watchdog agents will automatically report here when an unauthorized upload is terminated.</p>
                            </div>
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>

        <footer>
            DLP Server running on local endpoint • Listening for incoming agent reports on <code>/api/report</code>
        </footer>
    </div>

    <script>
        let allIncidents = [];
        let highestKnownId = 0;

        async function fetchStats() {
            try {
                const res = await fetch('/api/stats');
                if (!res.ok) return;
                const stats = await res.json();
                document.getElementById('stat-total').innerText = stats.total;
                document.getElementById('stat-today').innerText = stats.today_count;
                document.getElementById('stat-hosts').innerText = stats.unique_hosts;
                document.getElementById('stat-users').innerText = stats.unique_users;
            } catch (e) {
                console.error("Failed to fetch stats", e);
            }
        }

        async function fetchIncidents() {
            try {
                const res = await fetch('/api/events');
                if (!res.ok) return;
                const data = await res.json();
                
                let isNewData = false;
                if (data.length > 0 && data[0].id > highestKnownId && highestKnownId !== 0) {
                    isNewData = true;
                }
                
                if (data.length > 0) {
                    highestKnownId = data[0].id;
                }

                allIncidents = data;
                renderIncidents(isNewData);
                fetchStats();
            } catch (e) {
                console.error("Failed to fetch incidents", e);
            }
        }

        function renderIncidents(highlightTop = false) {
            const query = document.getElementById('searchInput').value.toLowerCase().trim();
            const tbody = document.getElementById('incidentTableBody');

            const filtered = allIncidents.filter(item => {
                if (!query) return true;
                return (
                    (item.hostname && item.hostname.toLowerCase().includes(query)) ||
                    (item.username && item.username.toLowerCase().includes(query)) ||
                    (item.file_name && item.file_name.toLowerCase().includes(query)) ||
                    (item.file_path && item.file_path.toLowerCase().includes(query)) ||
                    (item.process && item.process.toLowerCase().includes(query)) ||
                    (item.reason && item.reason.toLowerCase().includes(query))
                );
            });

            if (filtered.length === 0) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="7">
                            <div class="empty-state">
                                <div class="empty-icon">🛡️</div>
                                <h3>${allIncidents.length === 0 ? "No security violations recorded yet." : "No matching incidents found."}</h3>
                                <p style="font-size: 13px; margin-top: 4px;">Ready and listening for endpoint reports.</p>
                            </div>
                        </td>
                    </tr>
                `;
                return;
            }

            let html = "";
            filtered.forEach((item, index) => {
                const isFlash = highlightTop && index === 0;
                html += `
                    <tr class="${isFlash ? 'new-row-flash' : ''}">
                        <td><span class="badge badge-red">BLOCKED</span></td>
                        <td style="color: #cbd5e1; font-family: ui-monospace, monospace;">${escapeHtml(item.timestamp)}</td>
                        <td>
                            <div class="host-user">
                                <span class="host-name">💻 ${escapeHtml(item.hostname || 'Unknown')}</span>
                                <span class="user-name">👤 ${escapeHtml(item.username || 'Unknown')}</span>
                            </div>
                        </td>
                        <td>
                            <span class="code-pill">${escapeHtml(item.process)}</span>
                            ${item.pid ? `<span style="font-size: 11px; color: #64748b; margin-left: 4px;">#${item.pid}</span>` : ''}
                        </td>
                        <td>
                            <div class="file-info">
                                <span class="file-name">📦 ${escapeHtml(item.file_name || 'N/A')}</span>
                                <span class="file-path" title="${escapeHtml(item.file_path)}">${escapeHtml(item.file_path)}</span>
                            </div>
                        </td>
                        <td><span class="badge badge-gray">${escapeHtml(item.file_size_str || 'N/A')}</span></td>
                        <td style="color: #cbd5e1; font-size: 12px;">${escapeHtml(item.reason || 'DLP Policy Breach')}</td>
                    </tr>
                `;
            });
            tbody.innerHTML = html;
        }

        function filterIncidents() {
            renderIncidents(false);
        }

        function escapeHtml(text) {
            if (!text) return "";
            return String(text)
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;")
                .replace(/'/g, "&#039;");
        }

        async function triggerTestSimulation() {
            try {
                const testPayload = {
                    hostname: "TEST-WORKSTATION-01",
                    username: "artist.demo",
                    process: "Telegram.exe",
                    pid: Math.floor(Math.random() * 9000) + 1000,
                    file_path: "D:\\3D_Projects\\Characters\\Hero_Dragon_Model.fbx",
                    file_name: "Hero_Dragon_Model.fbx",
                    file_size_bytes: 48500000,
                    reason: "Detected 3D binary signature: Kaydara FBX Binary",
                    action_taken: "kill"
                };

                const res = await fetch('/api/report', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(testPayload)
                });

                if (res.ok) {
                    fetchIncidents();
                }
            } catch (e) {
                alert("Failed to send test simulation: " + e);
            }
        }

        async function clearLogs() {
            if (!confirm("Are you sure you want to clear all recorded DLP incident logs?")) return;
            try {
                await fetch('/api/clear', { method: 'POST' });
                highestKnownId = 0;
                fetchIncidents();
            } catch (e) {
                alert("Error clearing logs: " + e);
            }
        }

        function exportCSV() {
            window.location.href = '/api/export';
        }

        // Initialize and start live polling (every 2.5s)
        fetchIncidents();
        setInterval(fetchIncidents, 2500);
    </script>
</body>
</html>
"""


class DLPRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress noisy standard HTTP logs; only print meaningful activity
        return

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_DASHBOARD.encode("utf-8"))

        elif path == "/api/events":
            incidents = get_incidents(200)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(incidents).encode("utf-8"))

        elif path == "/api/stats":
            stats = get_stats()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(stats).encode("utf-8"))

        elif path == "/api/export":
            incidents = get_incidents(1000)
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow([
                "ID", "Timestamp", "Hostname", "Username", "Process",
                "PID", "File_Name", "File_Path", "Size_Bytes", "Reason", "Action"
            ])
            for inc in incidents:
                writer.writerow([
                    inc.get("id"), inc.get("timestamp"), inc.get("hostname"),
                    inc.get("username"), inc.get("process"), inc.get("pid"),
                    inc.get("file_name"), inc.get("file_path"), inc.get("file_size_bytes"),
                    inc.get("reason"), inc.get("action_taken")
                ])

            csv_data = output.getvalue().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", 'attachment; filename="dlp_incident_report.csv"')
            self.end_headers()
            self.wfile.write(csv_data)

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/report":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                data = json.loads(body)
                new_id = insert_incident(data)
                
                # Friendly console notification
                host = data.get("host") or data.get("hostname") or "Unknown"
                user = data.get("user") or data.get("username") or "Unknown"
                fname = data.get("file_name") or os.path.basename(data.get("file", ""))
                print(f"[🚨 DLP ALERT RECEIVED] ID #{new_id} | Host: {host} | User: {user} | Blocked: {fname}")

                self.send_response(201)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "recorded", "id": new_id}).encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))

        elif path == "/api/clear":
            clear_db()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "cleared"}).encode("utf-8"))

        else:
            self.send_response(404)
            self.end_headers()


def run_server():
    init_db()
    local_ip = get_local_ip()

    server_address = ("0.0.0.0", PORT)
    httpd = ThreadingHTTPServer(server_address, DLPRequestHandler)

    print("=" * 68)
    print("  🛡️  DLP INCIDENT MANAGEMENT CENTER (LOCAL TEST & AUDIT SERVER)")
    print("=" * 68)
    print(f"  [+] Local Dashboard:       http://localhost:{PORT}")
    print(f"  [+] Localhost Loopback:    http://127.0.0.1:{PORT}")
    print(f"  [+] Office LAN Network IP: http://{local_ip}:{PORT}")
    print(f"  [+] SQLite Database:       {DB_FILE}")
    print("=" * 68)
    print("  Ready! Open http://127.0.0.1:5000 in your browser.")
    print("  To stop the server at any time, press Ctrl+C.")
    print("=" * 68 + "\n")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Shutting down DLP Dashboard Server. Clean exit.")
        httpd.server_close()


if __name__ == "__main__":
    run_server()

