"""
REST API Server for MBOT
Provides API endpoints for external integration
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import threading
import time
import json
import hashlib
from datetime import datetime
from typing import Dict, Optional
from encryption import encryption

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# API Configuration
API_CONFIG = {
    'enabled': True,
    'port': 5000,
    'rate_limit': 100,  # requests per minute
    'api_keys': {},  # key: {'owner': '', 'permissions': []}
    'require_auth': True
}

# Load API keys
try:
    with open('api_keys.json', 'r') as f:
        API_CONFIG['api_keys'] = json.load(f)
except:
    API_CONFIG['api_keys'] = {}

class APIServer:
    def __init__(self):
        self.app = app
        self.setup_routes()
        self.rate_limit_cache = {}
        self.active_connections = 0
        self.max_connections = 100
    
    def setup_routes(self):
        """Setup API routes"""
        
        @app.before_request
        def before_request():
            """Handle pre-request operations"""
            self.active_connections += 1
            
            # Check rate limiting
            if not self.check_rate_limit(request):
                return jsonify({
                    'error': 'Rate limit exceeded',
                    'status': 429
                }), 429
            
            # Check authentication
            if API_CONFIG['require_auth']:
                auth_result = self.authenticate_request(request)
                if not auth_result['authenticated']:
                    return jsonify({
                        'error': 'Authentication required',
                        'details': auth_result.get('reason', 'Invalid API key')
                    }), 401
        
        @app.after_request
        def after_request(response):
            """Handle post-request operations"""
            self.active_connections -= 1
            return response
        
        @app.route('/api/v1/status', methods=['GET'])
        def api_status():
            """API status endpoint"""
            return jsonify({
                'status': 'online',
                'version': '1.0',
                'timestamp': datetime.now().isoformat(),
                'active_connections': self.active_connections,
                'uptime': self.get_uptime()
            })
        
        @app.route('/api/v1/boost', methods=['POST'])
        def api_boost():
            """Boost video endpoint"""
            try:
                data = request.json
                
                # Validate required fields
                required_fields = ['video_url', 'count', 'api_key']
                for field in required_fields:
                    if field not in data:
                        return jsonify({
                            'error': f'Missing required field: {field}'
                        }), 400
                
                # Check API key permissions
                api_key = data['api_key']
                if api_key not in API_CONFIG['api_keys']:
                    return jsonify({'error': 'Invalid API key'}), 401
                
                permissions = API_CONFIG['api_keys'][api_key].get('permissions', [])
                if 'boost' not in permissions:
                    return jsonify({'error': 'Insufficient permissions'}), 403
                
                # Extract parameters
                video_url = data['video_url']
                count = int(data['count'])
                boost_type = data.get('type', 'views')
                
                # Validate count
                if count > 10000:
                    return jsonify({
                        'error': 'Count too high, maximum is 10000'
                    }), 400
                
                # Start boost (this would integrate with your boost system)
                boost_id = self.generate_boost_id()
                boost_result = {
                    'boost_id': boost_id,
                    'video_url': video_url,
                    'count': count,
                    'type': boost_type,
                    'status': 'queued',
                    'created_at': datetime.now().isoformat()
                }
                
                # Log boost request
                self.log_api_request('boost', data, boost_result)
                
                # Start boost in background
                threading.Thread(
                    target=self.process_boost,
                    args=(boost_id, video_url, count, boost_type)
                ).start()
                
                return jsonify({
                    'success': True,
                    'boost_id': boost_id,
                    'message': 'Boost queued successfully'
                })
                
            except Exception as e:
                return jsonify({
                    'error': str(e)
                }), 500
        
        @app.route('/api/v1/boost/<boost_id>', methods=['GET'])
        def get_boost_status(boost_id):
            """Get boost status"""
            try:
                # Load boost status from file
                boost_data = self.get_boost_data(boost_id)
                
                if not boost_data:
                    return jsonify({'error': 'Boost not found'}), 404
                
                return jsonify(boost_data)
                
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @app.route('/api/v1/stats', methods=['GET'])
        def api_stats():
            """Get system statistics"""
            try:
                # Load statistics
                stats = self.get_system_stats()
                
                return jsonify({
                    'success': True,
                    'stats': stats,
                    'timestamp': datetime.now().isoformat()
                })
                
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @app.route('/api/v1/users', methods=['GET'])
        def api_users():
            """Get users list (admin only)"""
            try:
                # Check admin permission
                api_key = request.args.get('api_key')
                if not self.is_admin_key(api_key):
                    return jsonify({'error': 'Admin access required'}), 403
                
                # Get users
                users = self.get_users_list()
                
                return jsonify({
                    'success': True,
                    'users': users,
                    'count': len(users)
                })
                
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @app.route('/api/v1/generate_key', methods=['POST'])
        def generate_api_key():
            """Generate new API key (admin only)"""
            try:
                data = request.json
                
                # Check admin permission
                admin_key = data.get('admin_key')
                if not self.is_admin_key(admin_key):
                    return jsonify({'error': 'Admin access required'}), 403
                
                # Generate API key
                owner = data.get('owner', 'unknown')
                permissions = data.get('permissions', ['read'])
                
                api_key = self.generate_new_api_key(owner, permissions)
                
                return jsonify({
                    'success': True,
                    'api_key': api_key,
                    'owner': owner,
                    'permissions': permissions,
                    'message': 'API key generated successfully'
                })
                
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @app.route('/api/v1/logs', methods=['GET'])
        def api_logs():
            """Get API logs (admin only)"""
            try:
                # Check admin permission
                api_key = request.args.get('api_key')
                if not self.is_admin_key(api_key):
                    return jsonify({'error': 'Admin access required'}), 403
                
                # Get logs
                logs = self.get_api_logs()
                
                return jsonify({
                    'success': True,
                    'logs': logs,
                    'count': len(logs)
                })
                
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @app.errorhandler(404)
        def not_found(error):
            return jsonify({'error': 'Endpoint not found'}), 404
        
        @app.errorhandler(500)
        def server_error(error):
            return jsonify({'error': 'Internal server error'}), 500
    
    def check_rate_limit(self, request) -> bool:
        """Check rate limiting for request"""
        if not API_CONFIG['rate_limit']:
            return True
        
        client_ip = request.remote_addr
        api_key = request.args.get('api_key') or request.json.get('api_key') if request.json else None
        
        cache_key = f"{client_ip}:{api_key}" if api_key else client_ip
        current_time = time.time()
        
        if cache_key not in self.rate_limit_cache:
            self.rate_limit_cache[cache_key] = {
                'count': 1,
                'timestamp': current_time,
                'first_request': current_time
            }
        else:
            data = self.rate_limit_cache[cache_key]
            
            # Reset if minute has passed
            if current_time - data['first_request'] > 60:
                data['count'] = 1
                data['first_request'] = current_time
            else:
                data['count'] += 1
            
            # Check limit
            if data['count'] > API_CONFIG['rate_limit']:
                return False
        
        return True
    
    def authenticate_request(self, request) -> Dict:
        """Authenticate API request"""
        api_key = None
        
        # Try to get API key from different sources
        if request.args.get('api_key'):
            api_key = request.args.get('api_key')
        elif request.json and 'api_key' in request.json:
            api_key = request.json['api_key']
        elif request.headers.get('X-API-Key'):
            api_key = request.headers.get('X-API-Key')
        
        if not api_key:
            return {
                'authenticated': False,
                'reason': 'No API key provided'
            }
        
        if api_key not in API_CONFIG['api_keys']:
            return {
                'authenticated': False,
                'reason': 'Invalid API key'
            }
        
        # Check if key is active
        key_data = API_CONFIG['api_keys'][api_key]
        if not key_data.get('active', True):
            return {
                'authenticated': False,
                'reason': 'API key inactive'
            }
        
        # Check expiration
        if 'expires' in key_data:
            expires = datetime.fromisoformat(key_data['expires'])
            if datetime.now() > expires:
                return {
                    'authenticated': False,
                    'reason': 'API key expired'
                }
        
        return {
            'authenticated': True,
            'key_data': key_data
        }
    
    def generate_boost_id(self) -> str:
        """Generate unique boost ID"""
        timestamp = int(time.time())
        random_str = hashlib.md5(str(time.time()).encode()).hexdigest()[:8]
        return f"boost_{timestamp}_{random_str}"
    
    def process_boost(self, boost_id: str, video_url: str, count: int, boost_type: str):
        """Process boost in background"""
        try:
            # Update status to processing
            boost_data = {
                'boost_id': boost_id,
                'video_url': video_url,
                'count': count,
                'type': boost_type,
                'status': 'processing',
                'started_at': datetime.now().isoformat(),
                'progress': 0,
                'delivered': 0
            }
            
            self.save_boost_data(boost_id, boost_data)
            
            # Simulate boost processing
            # In production, integrate with your boost system
            for i in range(10):
                time.sleep(1)  # Simulate work
                
                # Update progress
                boost_data['progress'] = (i + 1) * 10
                boost_data['delivered'] = count * (i + 1) // 10
                self.save_boost_data(boost_id, boost_data)
            
            # Mark as completed
            boost_data['status'] = 'completed'
            boost_data['completed_at'] = datetime.now().isoformat()
            boost_data['progress'] = 100
            boost_data['delivered'] = count
            
            self.save_boost_data(boost_id, boost_data)
            
        except Exception as e:
            # Mark as failed
            boost_data = self.get_boost_data(boost_id)
            if boost_data:
                boost_data['status'] = 'failed'
                boost_data['error'] = str(e)
                boost_data['failed_at'] = datetime.now().isoformat()
                self.save_boost_data(boost_id, boost_data)
    
    def get_boost_data(self, boost_id: str) -> Optional[Dict]:
        """Get boost data from file"""
        try:
            with open(f'boosts/{boost_id}.json', 'r') as f:
                return json.load(f)
        except:
            return None
    
    def save_boost_data(self, boost_id: str, data: Dict):
        """Save boost data to file"""
        try:
            # Create directory if not exists
            import os
            if not os.path.exists('boosts'):
                os.makedirs('boosts')
            
            with open(f'boosts/{boost_id}.json', 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving boost data: {e}")
    
    def get_system_stats(self) -> Dict:
        """Get system statistics"""
        try:
            # Load various statistics
            stats = {
                'system': {
                    'uptime': self.get_uptime(),
                    'active_connections': self.active_connections,
                    'total_api_requests': self.get_total_api_requests()
                },
                'boosts': {
                    'total': self.get_total_boosts(),
                    'today': self.get_today_boosts(),
                    'success_rate': self.get_boost_success_rate()
                },
                'users': {
                    'total': self.get_total_users(),
                    'active_today': self.get_active_users_today()
                }
            }
            
            return stats
            
        except Exception as e:
            print(f"Error getting stats: {e}")
            return {}
    
    def get_users_list(self, limit: int = 100) -> list:
        """Get users list"""
        try:
            with open('user_data.json', 'r') as f:
                users = json.load(f)
            
            # Convert to list and limit
            users_list = list(users.values())[:limit]
            
            # Remove sensitive data
            for user in users_list:
                if 'phone' in user:
                    del user['phone']
                if 'email' in user:
                    del user['email']
            
            return users_list
            
        except:
            return []
    
    def is_admin_key(self, api_key: str) -> bool:
        """Check if API key has admin permissions"""
        if not api_key or api_key not in API_CONFIG['api_keys']:
            return False
        
        key_data = API_CONFIG['api_keys'][api_key]
        permissions = key_data.get('permissions', [])
        
        return 'admin' in permissions
    
    def generate_new_api_key(self, owner: str, permissions: list) -> str:
        """Generate new API key"""
        # Generate secure API key
        import secrets
        api_key = secrets.token_urlsafe(32)
        
        # Save key data
        key_data = {
            'owner': owner,
            'permissions': permissions,
            'created_at': datetime.now().isoformat(),
            'active': True
        }
        
        API_CONFIG['api_keys'][api_key] = key_data
        
        # Save to file
        self.save_api_keys()
        
        return api_key
    
    def get_api_logs(self, limit: int = 100) -> list:
        """Get API logs"""
        try:
            with open('api_logs.json', 'r') as f:
                logs = json.load(f)
            
            return logs[-limit:]
        except:
            return []
    
    def log_api_request(self, endpoint: str, request_data: Dict, response_data: Dict):
        """Log API request"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'endpoint': endpoint,
            'request': request_data,
            'response': response_data,
            'ip_address': request.remote_addr
        }
        
        try:
            # Load existing logs
            logs = []
            try:
                with open('api_logs.json', 'r') as f:
                    logs = json.load(f)
            except:
                logs = []
            
            # Add new log
            logs.append(log_entry)
            
            # Keep only last 1000 logs
            if len(logs) > 1000:
                logs = logs[-1000:]
            
            # Save logs
            with open('api_logs.json', 'w') as f:
                json.dump(logs, f, indent=2)
                
        except Exception as e:
            print(f"Error logging API request: {e}")
    
    def save_api_keys(self):
        """Save API keys to file"""
        try:
            with open('api_keys.json', 'w') as f:
                json.dump(API_CONFIG['api_keys'], f, indent=2)
        except Exception as e:
            print(f"Error saving API keys: {e}")
    
    # Helper methods for statistics
    def get_uptime(self) -> int:
        """Get server uptime in seconds"""
        # This would read from a file where start time is stored
        try:
            with open('server_start_time.txt', 'r') as f:
                start_time = float(f.read())
            return int(time.time() - start_time)
        except:
            return 0
    
    def get_total_api_requests(self) -> int:
        """Get total API requests"""
        try:
            with open('api_logs.json', 'r') as f:
                logs = json.load(f)
            return len(logs)
        except:
            return 0
    
    def get_total_boosts(self) -> int:
        """Get total boosts"""
        try:
            import os
            if os.path.exists('boosts'):
                return len([f for f in os.listdir('boosts') if f.endswith('.json')])
            return 0
        except:
            return 0
    
    def get_today_boosts(self) -> int:
        """Get today's boosts"""
        today = datetime.now().strftime("%Y-%m-%d")
        count = 0
        
        try:
            import os
            if os.path.exists('boosts'):
                for filename in os.listdir('boosts'):
                    if filename.endswith('.json'):
                        with open(f'boosts/{filename}', 'r') as f:
                            data = json.load(f)
                            if data.get('created_at', '').startswith(today):
                                count += 1
        except:
            pass
        
        return count
    
    def get_boost_success_rate(self) -> float:
        """Get boost success rate"""
        try:
            import os
            if os.path.exists('boosts'):
                files = [f for f in os.listdir('boosts') if f.endswith('.json')]
                if not files:
                    return 0.0
                
                completed = 0
                for filename in files:
                    with open(f'boosts/{filename}', 'r') as f:
                        data = json.load(f)
                        if data.get('status') == 'completed':
                            completed += 1
                
                return (completed / len(files)) * 100
        except:
            return 0.0
    
    def get_total_users(self) -> int:
        """Get total users"""
        try:
            with open('user_data.json', 'r') as f:
                users = json.load(f)
            return len(users)
        except:
            return 0
    
    def get_active_users_today(self) -> int:
        """Get active users today"""
        today = datetime.now().strftime("%Y-%m-%d")
        count = 0
        
        try:
            with open('user_data.json', 'r') as f:
                users = json.load(f)
            
            for user_data in users.values():
                if user_data.get('last_active', '').startswith(today):
                    count += 1
        except:
            pass
        
        return count

    def start(self):
        """Start the API server"""
        if not API_CONFIG['enabled']:
            print("API server is disabled in config")
            return
        
        print(f"Starting API server on port {API_CONFIG['port']}")
        
        # Save server start time
        with open('server_start_time.txt', 'w') as f:
            f.write(str(time.time()))
        
        # Run Flask app
        self.app.run(
            host='0.0.0.0',
            port=API_CONFIG['port'],
            debug=False,
            threaded=True
        )

# Global instance
api_server = APIServer()

def start_api_server():
    """Start API server in background"""
    if API_CONFIG['enabled']:
        server_thread = threading.Thread(target=api_server.start)
        server_thread.daemon = True
        server_thread.start()
        print(f"API server started on port {API_CONFIG['port']}")
