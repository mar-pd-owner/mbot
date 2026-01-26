"""
Web Dashboard for MBOT
Provides web interface for monitoring and control
"""

from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from flask_socketio import SocketIO, emit
import json
import time
from datetime import datetime, timedelta
import threading
from typing import Dict, List
import hashlib
from database import db
from encryption import encryption

app = Flask(__name__)
app.secret_key = 'mbot_dashboard_secret_key_2024'
socketio = SocketIO(app, cors_allowed_origins="*")

# Dashboard configuration
DASHBOARD_CONFIG = {
    'enabled': True,
    'port': 8080,
    'require_auth': True,
    'admin_users': {
        'admin': hashlib.sha256('admin123'.encode()).hexdigest(),  # Change this!
        'owner': hashlib.sha256('owner123'.encode()).hexdigest()   # Change this!
    },
    'session_timeout': 3600,  # 1 hour
    'rate_limit': 60,  # requests per minute
}

class WebDashboard:
    def __init__(self):
        self.app = app
        self.socketio = socketio
        self.active_sessions = {}
        self.realtime_data = {
            'system_stats': {},
            'active_boosts': [],
            'recent_users': [],
            'security_alerts': [],
            'performance_metrics': {}
        }
        
        self.setup_routes()
        self.setup_socketio()
        
        # Start background updater
        self.background_thread = threading.Thread(target=self.update_realtime_data)
        self.background_thread.daemon = True
        self.background_thread.start()
    
    def setup_routes(self):
        """Setup web routes"""
        
        @app.before_request
        def before_request():
            """Handle authentication"""
            if not DASHBOARD_CONFIG['require_auth']:
                return
            
            if request.endpoint in ['login', 'static', 'api_login']:
                return
            
            if 'username' not in session:
                return redirect(url_for('login'))
            
            # Check session timeout
            if 'login_time' in session:
                login_time = datetime.fromtimestamp(session['login_time'])
                if datetime.now() - login_time > timedelta(seconds=DASHBOARD_CONFIG['session_timeout']):
                    session.clear()
                    return redirect(url_for('login'))
        
        @app.route('/')
        def index():
            """Main dashboard page"""
            return render_template('dashboard.html')
        
        @app.route('/login', methods=['GET', 'POST'])
        def login():
            """Login page"""
            if request.method == 'POST':
                username = request.form.get('username')
                password = request.form.get('password')
                
                if self.authenticate_user(username, password):
                    session['username'] = username
                    session['login_time'] = time.time()
                    return redirect(url_for('index'))
                else:
                    return render_template('login.html', error='Invalid credentials')
            
            return render_template('login.html')
        
        @app.route('/logout')
        def logout():
            """Logout user"""
            session.clear()
            return redirect(url_for('login'))
        
        @app.route('/api/login', methods=['POST'])
        def api_login():
            """API login endpoint"""
            data = request.json
            username = data.get('username')
            password = data.get('password')
            
            if self.authenticate_user(username, password):
                session['username'] = username
                session['login_time'] = time.time()
                return jsonify({'success': True, 'message': 'Login successful'})
            else:
                return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
        
        @app.route('/api/dashboard/stats')
        def api_dashboard_stats():
            """Get dashboard statistics"""
            if not self.check_auth():
                return jsonify({'error': 'Unauthorized'}), 401
            
            stats = self.get_dashboard_stats()
            return jsonify(stats)
        
        @app.route('/api/users')
        def api_users():
            """Get users list"""
            if not self.check_auth():
                return jsonify({'error': 'Unauthorized'}), 401
            
            limit = request.args.get('limit', 50, type=int)
            offset = request.args.get('offset', 0, type=int)
            
            users = self.get_users(limit, offset)
            return jsonify(users)
        
        @app.route('/api/boosts')
        def api_boosts():
            """Get boosts list"""
            if not self.check_auth():
                return jsonify({'error': 'Unauthorized'}), 401
            
            status = request.args.get('status', 'all')
            limit = request.args.get('limit', 50, type=int)
            
            boosts = self.get_boosts(status, limit)
            return jsonify(boosts)
        
        @app.route('/api/boost/<boost_id>')
        def api_boost_details(boost_id):
            """Get boost details"""
            if not self.check_auth():
                return jsonify({'error': 'Unauthorized'}), 401
            
            boost_data = self.get_boost_details(boost_id)
            if boost_data:
                return jsonify(boost_data)
            else:
                return jsonify({'error': 'Boost not found'}), 404
        
        @app.route('/api/system/health')
        def api_system_health():
            """Get system health"""
            if not self.check_auth():
                return jsonify({'error': 'Unauthorized'}), 401
            
            health = db.get_system_health()
            return jsonify(health)
        
        @app.route('/api/analytics')
        def api_analytics():
            """Get analytics data"""
            if not self.check_auth():
                return jsonify({'error': 'Unauthorized'}), 401
            
            metric = request.args.get('metric', 'rps')
            hours = request.args.get('hours', 24, type=int)
            
            analytics = self.get_analytics(metric, hours)
            return jsonify(analytics)
        
        @app.route('/api/security/events')
        def api_security_events():
            """Get security events"""
            if not self.check_auth():
                return jsonify({'error': 'Unauthorized'}), 401
            
            severity = request.args.get('severity')
            hours = request.args.get('hours', 24, type=int)
            
            events = db.get_security_events(hours, severity)
            return jsonify(events)
        
        @app.route('/api/actions/stop_boost', methods=['POST'])
        def api_stop_boost():
            """Stop a boost"""
            if not self.check_auth():
                return jsonify({'error': 'Unauthorized'}), 401
            
            data = request.json
            boost_id = data.get('boost_id')
            
            if self.stop_boost(boost_id):
                return jsonify({'success': True, 'message': 'Boost stopped'})
            else:
                return jsonify({'success': False, 'message': 'Failed to stop boost'})
        
        @app.route('/api/actions/ban_user', methods=['POST'])
        def api_ban_user():
            """Ban a user"""
            if not self.check_auth():
                return jsonify({'error': 'Unauthorized'}), 401
            
            data = request.json
            user_id = data.get('user_id')
            reason = data.get('reason', 'Violation of terms')
            
            if self.ban_user(user_id, reason):
                return jsonify({'success': True, 'message': 'User banned'})
            else:
                return jsonify({'success': False, 'message': 'Failed to ban user'})
        
        @app.route('/api/actions/send_message', methods=['POST'])
        def api_send_message():
            """Send message to user"""
            if not self.check_auth():
                return jsonify({'error': 'Unauthorized'}), 401
            
            data = request.json
            user_id = data.get('user_id')
            message = data.get('message')
            
            if self.send_user_message(user_id, message):
                return jsonify({'success': True, 'message': 'Message sent'})
            else:
                return jsonify({'success': False, 'message': 'Failed to send message'})
        
        @app.route('/api/config')
        def api_config():
            """Get dashboard configuration"""
            if not self.check_auth():
                return jsonify({'error': 'Unauthorized'}), 401
            
            # Return safe configuration (without sensitive data)
            safe_config = {
                'require_auth': DASHBOARD_CONFIG['require_auth'],
                'session_timeout': DASHBOARD_CONFIG['session_timeout'],
                'dashboard_version': '1.0'
            }
            return jsonify(safe_config)
    
    def setup_socketio(self):
        """Setup SocketIO events"""
        
        @socketio.on('connect')
        def handle_connect():
            """Handle client connection"""
            emit('connection_established', {'message': 'Connected to MBOT Dashboard'})
        
        @socketio.on('get_realtime_data')
        def handle_get_realtime_data():
            """Send realtime data to client"""
            emit('realtime_data', self.realtime_data)
        
        @socketio.on('subscribe_metric')
        def handle_subscribe_metric(data):
            """Subscribe to metric updates"""
            metric = data.get('metric')
            if metric:
                emit('metric_subscribed', {'metric': metric, 'message': 'Subscribed'})
    
    def authenticate_user(self, username: str, password: str) -> bool:
        """Authenticate dashboard user"""
        if username in DASHBOARD_CONFIG['admin_users']:
            stored_hash = DASHBOARD_CONFIG['admin_users'][username]
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            return stored_hash == password_hash
        
        return False
    
    def check_auth(self) -> bool:
        """Check if user is authenticated"""
        if not DASHBOARD_CONFIG['require_auth']:
            return True
        
        return 'username' in session
    
    def update_realtime_data(self):
        """Update realtime data in background"""
        while True:
            try:
                # Update system stats
                self.realtime_data['system_stats'] = self.get_system_stats()
                
                # Update active boosts
                self.realtime_data['active_boosts'] = self.get_active_boosts()
                
                # Update recent users
                self.realtime_data['recent_users'] = self.get_recent_users()
                
                # Update security alerts
                self.realtime_data['security_alerts'] = db.get_security_events(1, 'high')
                
                # Update performance metrics
                self.realtime_data['performance_metrics'] = self.get_performance_metrics()
                
                # Emit update to connected clients
                socketio.emit('realtime_update', self.realtime_data)
                
            except Exception as e:
                print(f"Error updating realtime data: {e}")
            
            time.sleep(5)  # Update every 5 seconds
    
    def get_dashboard_stats(self) -> Dict:
        """Get dashboard statistics"""
        # Get user statistics
        user_stats = db.execute_query('''
            SELECT 
                COUNT(*) as total_users,
                SUM(CASE WHEN date(last_active) = date('now') THEN 1 ELSE 0 END) as active_today,
                SUM(CASE WHEN status = 'banned' THEN 1 ELSE 0 END) as banned_users
            FROM users
        ''')[0]
        
        # Get boost statistics
        boost_stats = db.execute_query('''
            SELECT 
                COUNT(*) as total_boosts,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_boosts,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_boosts,
                SUM(CASE WHEN status = 'processing' THEN 1 ELSE 0 END) as active_boosts,
                SUM(target_count) as total_targeted,
                SUM(completed_count) as total_delivered
            FROM boosts
        ''')[0]
        
        # Get today's statistics
        today_stats = db.execute_query('''
            SELECT 
                COUNT(*) as boosts_today,
                SUM(completed_count) as delivered_today,
                AVG(average_rps) as avg_rps_today
            FROM boosts 
            WHERE date(start_time) = date('now')
        ''')[0]
        
        # Get device statistics
        device_stats = db.execute_query('''
            SELECT 
                COUNT(*) as total_devices,
                SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active_devices,
                SUM(success_count) as total_success,
                SUM(usage_count) as total_usage
            FROM devices
        ''')[0]
        
        # Calculate success rate
        success_rate = 0
        if device_stats['total_usage'] > 0:
            success_rate = (device_stats['total_success'] / device_stats['total_usage']) * 100
        
        return {
            'user_stats': user_stats,
            'boost_stats': boost_stats,
            'today_stats': today_stats,
            'device_stats': device_stats,
            'success_rate': round(success_rate, 2),
            'timestamp': datetime.now().isoformat()
        }
    
    def get_system_stats(self) -> Dict:
        """Get realtime system statistics"""
        # Get current RPS from analytics
        rps_data = db.get_metrics('rps', 1)  # Last hour
        current_rps = rps_data[-1]['metric_value'] if rps_data else 0
        
        # Get active connections
        active_connections = len(self.active_sessions)
        
        # Get memory usage (simulated)
        import psutil
        memory_usage = psutil.virtual_memory().percent
        
        # Get CPU usage (simulated)
        cpu_usage = psutil.cpu_percent(interval=1)
        
        return {
            'current_rps': round(current_rps, 2),
            'active_connections': active_connections,
            'memory_usage': round(memory_usage, 2),
            'cpu_usage': round(cpu_usage, 2),
            'uptime': self.get_uptime(),
            'timestamp': datetime.now().isoformat()
        }
    
    def get_active_boosts(self, limit: int = 10) -> List[Dict]:
        """Get active boosts"""
        boosts = db.execute_query('''
            SELECT 
                b.*,
                u.username,
                u.telegram_id
            FROM boosts b
            LEFT JOIN users u ON b.user_id = u.id
            WHERE b.status IN ('processing', 'pending')
            ORDER BY b.start_time DESC
            LIMIT ?
        ''', (limit,))
        
        return boosts
    
    def get_recent_users(self, limit: int = 10) -> List[Dict]:
        """Get recent users"""
        users = db.execute_query('''
            SELECT 
                id,
                telegram_id,
                username,
                first_name,
                last_name,
                join_date,
                last_active,
                total_boosts
            FROM users
            ORDER BY last_active DESC
            LIMIT ?
        ''', (limit,))
        
        return users
    
    def get_performance_metrics(self) -> Dict:
        """Get performance metrics"""
        # Get RPS metrics for last hour
        rps_data = db.get_metrics('rps', 1)
        rps_values = [d['metric_value'] for d in rps_data]
        
        # Get response time metrics
        rt_data = db.get_metrics('response_time', 1)
        rt_values = [d['metric_value'] for d in rt_data]
        
        # Calculate statistics
        avg_rps = sum(rps_values) / len(rps_values) if rps_values else 0
        peak_rps = max(rps_values) if rps_values else 0
        avg_response_time = sum(rt_values) / len(rt_values) if rt_values else 0
        
        return {
            'avg_rps': round(avg_rps, 2),
            'peak_rps': round(peak_rps, 2),
            'avg_response_time': round(avg_response_time, 2),
            'rps_trend': rps_values[-10:],  # Last 10 values
            'response_time_trend': rt_values[-10:]
        }
    
    def get_users(self, limit: int = 50, offset: int = 0) -> Dict:
        """Get users with pagination"""
        users = db.execute_query('''
            SELECT 
                id,
                telegram_id,
                username,
                first_name,
                last_name,
                join_date,
                last_active,
                total_boosts,
                total_likes,
                status
            FROM users
            ORDER BY id DESC
            LIMIT ? OFFSET ?
        ''', (limit, offset))
        
        total_users = db.execute_query('SELECT COUNT(*) as count FROM users')[0]['count']
        
        return {
            'users': users,
            'total': total_users,
            'limit': limit,
            'offset': offset
        }
    
    def get_boosts(self, status: str = 'all', limit: int = 50) -> Dict:
        """Get boosts with filtering"""
        query = '''
            SELECT 
                b.*,
                u.username,
                u.telegram_id
            FROM boosts b
            LEFT JOIN users u ON b.user_id = u.id
        '''
        
        params = []
        
        if status != 'all':
            query += ' WHERE b.status = ?'
            params.append(status)
        
        query += ' ORDER BY b.start_time DESC LIMIT ?'
        params.append(limit)
        
        boosts = db.execute_query(query, tuple(params))
        
        return boosts
    
    def get_boost_details(self, boost_id: str) -> Dict:
        """Get detailed boost information"""
        boost = db.execute_query('''
            SELECT 
                b.*,
                u.username,
                u.telegram_id,
                u.first_name
            FROM boosts b
            LEFT JOIN users u ON b.user_id = u.id
            WHERE b.boost_id = ?
        ''', (boost_id,))
        
        if not boost:
            return None
        
        boost_data = boost[0]
        
        # Get request statistics
        requests = db.execute_query('''
            SELECT 
                COUNT(*) as total_requests,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
                AVG(response_time) as avg_response_time,
                MIN(timestamp) as first_request,
                MAX(timestamp) as last_request
            FROM boost_requests
            WHERE boost_id = ?
        ''', (boost_id,))[0]
        
        boost_data['request_stats'] = requests
        
        return boost_data
    
    def get_analytics(self, metric: str, hours: int) -> List[Dict]:
        """Get analytics data"""
        return db.get_metrics(metric, hours)
    
    def stop_boost(self, boost_id: str) -> bool:
        """Stop a boost"""
        try:
            # This would integrate with your boost manager
            # For now, just update database
            db.execute_query('''
                UPDATE boosts 
                SET status = 'stopped', end_time = datetime('now')
                WHERE boost_id = ?
            ''', (boost_id,))
            
            return True
        except Exception as e:
            print(f"Error stopping boost: {e}")
            return False
    
    def ban_user(self, user_id: int, reason: str) -> bool:
        """Ban a user"""
        try:
            db.execute_query('''
                UPDATE users 
                SET status = 'banned'
                WHERE id = ?
            ''', (user_id,))
            
            # Log security event
            db.log_security_event(
                'user_banned',
                'high',
                '127.0.0.1',  # Dashboard IP
                user_id,
                f'User banned via dashboard: {reason}',
                {'banned_by': session.get('username'), 'reason': reason}
            )
            
            return True
        except Exception as e:
            print(f"Error banning user: {e}")
            return False
    
    def send_user_message(self, user_id: int, message: str) -> bool:
        """Send message to user"""
        try:
            # Add message to database
            db.add_message(
                user_id,
                'admin_message',
                message,
                'outgoing',
                {'sent_via': 'dashboard', 'admin': session.get('username')}
            )
            
            # This would also trigger Telegram notification
            # For now, just log it
            
            return True
        except Exception as e:
            print(f"Error sending message: {e}")
            return False
    
    def get_uptime(self) -> int:
        """Get system uptime in seconds"""
        try:
            with open('system_start_time.txt', 'r') as f:
                start_time = float(f.read())
            return int(time.time() - start_time)
        except:
            return 0
    
    def start(self):
        """Start web dashboard"""
        if not DASHBOARD_CONFIG['enabled']:
            print("Web dashboard is disabled in config")
            return
        
        print(f"Starting web dashboard on port {DASHBOARD_CONFIG['port']}")
        
        # Save system start time
        with open('system_start_time.txt', 'w') as f:
            f.write(str(time.time()))
        
        # Create templates directory if not exists
        import os
        if not os.path.exists('templates'):
            os.makedirs('templates')
        
        # Create basic templates
        self.create_templates()
        
        # Run Flask app
        socketio.run(
            app,
            host='0.0.0.0',
            port=DASHBOARD_CONFIG['port'],
            debug=False,
            allow_unsafe_werkzeug=True
        )
    
    def create_templates(self):
        """Create HTML templates"""
        
        # Create login template
        login_template = '''
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>MBOT Dashboard - Login</title>
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body { 
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }
                .login-container {
                    background: white;
                    padding: 40px;
                    border-radius: 10px;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.1);
                    width: 100%;
                    max-width: 400px;
                }
                h1 {
                    color: #333;
                    margin-bottom: 30px;
                    text-align: center;
                    font-weight: 300;
                }
                .form-group {
                    margin-bottom: 20px;
                }
                label {
                    display: block;
                    margin-bottom: 5px;
                    color: #666;
                    font-size: 14px;
                }
                input {
                    width: 100%;
                    padding: 12px;
                    border: 1px solid #ddd;
                    border-radius: 5px;
                    font-size: 16px;
                    transition: border-color 0.3s;
                }
                input:focus {
                    outline: none;
                    border-color: #667eea;
                }
                .error {
                    background: #fee;
                    color: #c33;
                    padding: 10px;
                    border-radius: 5px;
                    margin-bottom: 20px;
                    font-size: 14px;
                }
                button {
                    width: 100%;
                    padding: 12px;
                    background: #667eea;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    font-size: 16px;
                    cursor: pointer;
                    transition: background 0.3s;
                }
                button:hover {
                    background: #5a67d8;
                }
                .footer {
                    margin-top: 20px;
                    text-align: center;
                    color: #666;
                    font-size: 12px;
                }
            </style>
        </head>
        <body>
            <div class="login-container">
                <h1>MBOT Dashboard</h1>
                {% if error %}
                <div class="error">{{ error }}</div>
                {% endif %}
                <form method="POST">
                    <div class="form-group">
                        <label for="username">Username</label>
                        <input type="text" id="username" name="username" required>
                    </div>
                    <div class="form-group">
                        <label for="password">Password</label>
                        <input type="password" id="password" name="password" required>
                    </div>
                    <button type="submit">Login</button>
                </form>
                <div class="footer">
                    MBOT System © 2024
                </div>
            </div>
        </body>
        </html>
        '''
        
        # Create dashboard template
        dashboard_template = '''
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>MBOT Dashboard</title>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/socket.io-client@4.5.4/dist/socket.io.min.js"></script>
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body { 
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: #f5f5f5;
                    color: #333;
                }
                .header {
                    background: white;
                    padding: 15px 30px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }
                .header h1 {
                    font-weight: 300;
                    color: #667eea;
                }
                .user-info {
                    display: flex;
                    align-items: center;
                    gap: 15px;
                }
                .logout-btn {
                    background: #dc3545;
                    color: white;
                    border: none;
                    padding: 8px 15px;
                    border-radius: 5px;
                    cursor: pointer;
                }
                .main-content {
                    padding: 30px;
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                    gap: 20px;
                }
                .card {
                    background: white;
                    border-radius: 10px;
                    padding: 20px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }
                .card h2 {
                    font-size: 18px;
                    margin-bottom: 15px;
                    color: #555;
                    border-bottom: 1px solid #eee;
                    padding-bottom: 10px;
                }
                .stat-item {
                    display: flex;
                    justify-content: space-between;
                    padding: 10px 0;
                    border-bottom: 1px solid #f5f5f5;
                }
                .stat-value {
                    font-weight: bold;
                    color: #667eea;
                }
                .chart-container {
                    height: 300px;
                    margin-top: 20px;
                }
                .realtime-data {
                    font-size: 12px;
                    color: #666;
                    margin-top: 10px;
                }
                .status-online {
                    color: #28a745;
                    font-weight: bold;
                }
                .status-offline {
                    color: #dc3545;
                    font-weight: bold;
                }
                .table-container {
                    overflow-x: auto;
                }
                table {
                    width: 100%;
                    border-collapse: collapse;
                }
                th, td {
                    padding: 12px;
                    text-align: left;
                    border-bottom: 1px solid #eee;
                }
                th {
                    background: #f8f9fa;
                    font-weight: 600;
                }
                tr:hover {
                    background: #f8f9fa;
                }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>MBOT Dashboard</h1>
                <div class="user-info">
                    <span>Welcome, <strong>{{ username }}</strong></span>
                    <a href="/logout" class="logout-btn">Logout</a>
                </div>
            </div>
            <div class="main-content">
                <!-- Stats Cards -->
                <div class="card">
                    <h2>System Overview</h2>
                    <div id="system-stats"></div>
                </div>
                <div class="card">
                    <h2>Performance Metrics</h2>
                    <div id="performance-metrics"></div>
                </div>
                <div class="card">
                    <h2>Active Boosts</h2>
                    <div id="active-boosts"></div>
                </div>
                <div class="card">
                    <h2>Recent Users</h2>
                    <div id="recent-users"></div>
                </div>
                <!-- Charts -->
                <div class="card" style="grid-column: span 2;">
                    <h2>Requests Per Second</h2>
                    <div class="chart-container">
                        <canvas id="rpsChart"></canvas>
                    </div>
                </div>
                <!-- Tables -->
                <div class="card" style="grid-column: span 2;">
                    <h2>Security Alerts</h2>
                    <div class="table-container">
                        <div id="security-alerts"></div>
                    </div>
                </div>
            </div>
            <script>
                // Initialize SocketIO
                const socket = io();
                
                // Update realtime data
                socket.on('realtime_data', function(data) {
                    updateDashboard(data);
                });
                
                socket.on('realtime_update', function(data) {
                    updateDashboard(data);
                });
                
                // Load initial data
                fetch('/api/dashboard/stats')
                    .then(response => response.json())
                    .then(data => {
                        updateDashboard({system_stats: data});
                    });
                
                // Update dashboard with data
                function updateDashboard(data) {
                    // Update system stats
                    if (data.system_stats) {
                        const stats = data.system_stats;
                        let html = '';
                        if (stats.user_stats) {
                            html += `
                                <div class="stat-item">
                                    <span>Total Users:</span>
                                    <span class="stat-value">${stats.user_stats.total_users}</span>
                                </div>
                                <div class="stat-item">
                                    <span>Active Today:</span>
                                    <span class="stat-value">${stats.user_stats.active_today}</span>
                                </div>
                            `;
                        }
                        document.getElementById('system-stats').innerHTML = html;
                    }
                    
                    // Update performance metrics
                    if (data.performance_metrics) {
                        const metrics = data.performance_metrics;
                        let html = `
                            <div class="stat-item">
                                <span>Avg RPS:</span>
                                <span class="stat-value">${metrics.avg_rps}</span>
                            </div>
                            <div class="stat-item">
                                <span>Peak RPS:</span>
                                <span class="stat-value">${metrics.peak_rps}</span>
                            </div>
                            <div class="stat-item">
                                <span>Avg Response Time:</span>
                                <span class="stat-value">${metrics.avg_response_time}ms</span>
                            </div>
                        `;
                        document.getElementById('performance-metrics').innerHTML = html;
                    }
                    
                    // Update active boosts
                    if (data.active_boosts) {
                        let html = '';
                        data.active_boosts.slice(0, 5).forEach(boost => {
                            html += `
                                <div class="stat-item">
                                    <span>${boost.video_id.substring(0, 15)}...</span>
                                    <span class="stat-value">${boost.completed_count}/${boost.target_count}</span>
                                </div>
                            `;
                        });
                        document.getElementById('active-boosts').innerHTML = html;
                    }
                    
                    // Update recent users
                    if (data.recent_users) {
                        let html = '';
                        data.recent_users.slice(0, 5).forEach(user => {
                            html += `
                                <div class="stat-item">
                                    <span>${user.username || 'N/A'}</span>
                                    <span class="stat-value">${user.total_boosts} boosts</span>
                                </div>
                            `;
                        });
                        document.getElementById('recent-users').innerHTML = html;
                    }
                    
                    // Update security alerts
                    if (data.security_alerts) {
                        let html = '<table>';
                        html += '<tr><th>Time</th><th>Type</th><th>Description</th><th>Severity</th></tr>';
                        data.security_alerts.slice(0, 10).forEach(alert => {
                            const time = new Date(alert.timestamp).toLocaleTimeString();
                            html += `
                                <tr>
                                    <td>${time}</td>
                                    <td>${alert.log_type}</td>
                                    <td>${alert.description}</td>
                                    <td class="status-${alert.severity}">${alert.severity}</td>
                                </tr>
                            `;
                        });
                        html += '</table>';
                        document.getElementById('security-alerts').innerHTML = html;
                    }
                }
                
                // Update charts
                function updateChart(chartId, labels, data, label) {
                    const ctx = document.getElementById(chartId).getContext('2d');
                    if (window[chartId + 'Chart']) {
                        window[chartId + 'Chart'].destroy();
                    }
                    window[chartId + 'Chart'] = new Chart(ctx, {
                        type: 'line',
                        data: {
                            labels: labels,
                            datasets: [{
                                label: label,
                                data: data,
                                borderColor: '#667eea',
                                backgroundColor: 'rgba(102, 126, 234, 0.1)',
                                fill: true
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false
                        }
                    });
                }
                
                // Request realtime data
                socket.emit('get_realtime_data');
                
                // Subscribe to metrics
                socket.emit('subscribe_metric', {metric: 'rps'});
            </script>
        </body>
        </html>
        '''
        
        # Write templates to files
        with open('templates/login.html', 'w') as f:
            f.write(login_template)
        
        with open('templates/dashboard.html', 'w') as f:
            f.write(dashboard_template)

# Global instance
dashboard = WebDashboard()

def start_web_dashboard():
    """Start web dashboard in background"""
    if DASHBOARD_CONFIG['enabled']:
        dashboard_thread = threading.Thread(target=dashboard.start)
        dashboard_thread.daemon = True
        dashboard_thread.start()
        print(f"Web dashboard started on port {DASHBOARD_CONFIG['port']}")
