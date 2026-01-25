"""
Security Monitoring System for MBOT
Detects and prevents security threats
"""

import json
import time
import hashlib
import ipaddress
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
import threading
from encryption import encryption

class SecurityMonitor:
    def __init__(self):
        self.threat_log = []
        self.blocked_ips = set()
        self.suspicious_users = set()
        self.security_rules = self.load_security_rules()
        self.rate_limit_cache = {}
        self.geo_cache = {}
        
        # Load existing blocked IPs
        self.load_blocked_ips()
        
        # Start monitoring thread
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self.monitor_security)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
    
    def load_security_rules(self) -> Dict:
        """Load security rules from file"""
        try:
            with open('security_rules.json', 'r') as f:
                return json.load(f)
        except:
            # Default security rules
            return {
                "max_requests_per_minute": 60,
                "max_failed_logins": 5,
                "block_duration_minutes": 60,
                "geo_restrictions": [],
                "user_agent_blacklist": [],
                "ip_blacklist": [],
                "allowed_countries": ["BD", "US", "GB", "CA", "AU"],
                "enable_rate_limiting": True,
                "enable_geo_filtering": True,
                "enable_user_agent_check": True
            }
    
    def load_blocked_ips(self):
        """Load blocked IPs from file"""
        try:
            with open('blocked_ips.json', 'r') as f:
                self.blocked_ips = set(json.load(f))
        except:
            self.blocked_ips = set()
    
    def save_blocked_ips(self):
        """Save blocked IPs to file"""
        try:
            with open('blocked_ips.json', 'w') as f:
                json.dump(list(self.blocked_ips), f)
        except Exception as e:
            print(f"Error saving blocked IPs: {e}")
    
    def monitor_security(self):
        """Continuous security monitoring"""
        while self.monitoring:
            time.sleep(60)  # Check every minute
            
            # Clean up old rate limit cache
            current_time = time.time()
            old_keys = []
            for key, data in self.rate_limit_cache.items():
                if current_time - data['timestamp'] > 60:
                    old_keys.append(key)
            
            for key in old_keys:
                del self.rate_limit_cache[key]
            
            # Clean old threat logs
            self.cleanup_old_threats()
            
            # Save blocked IPs periodically
            self.save_blocked_ips()
    
    def check_request(self, user_id: int, ip_address: str, user_agent: str, 
                     request_type: str, details: Dict = None) -> Dict:
        """Check if request is safe"""
        result = {
            'allowed': True,
            'reason': '',
            'threat_level': 'low',
            'action': 'allow'
        }
        
        # Check if IP is blocked
        if ip_address in self.blocked_ips:
            result['allowed'] = False
            result['reason'] = 'IP blocked'
            result['threat_level'] = 'high'
            result['action'] = 'block'
            return result
        
        # Check rate limiting
        if self.security_rules['enable_rate_limiting']:
            rate_check = self.check_rate_limit(ip_address, user_id)
            if not rate_check['allowed']:
                result.update(rate_check)
                return result
        
        # Check user agent
        if self.security_rules['enable_user_agent_check']:
            ua_check = self.check_user_agent(user_agent)
            if not ua_check['allowed']:
                result.update(ua_check)
                return result
        
        # Check for suspicious patterns
        pattern_check = self.check_suspicious_patterns(
            user_id, ip_address, request_type, details
        )
        if not pattern_check['allowed']:
            result.update(pattern_check)
            return result
        
        # Check geo-location if enabled
        if self.security_rules['enable_geo_filtering']:
            geo_check = self.check_geo_location(ip_address)
            if not geo_check['allowed']:
                result.update(geo_check)
                return result
        
        return result
    
    def check_rate_limit(self, ip_address: str, user_id: int) -> Dict:
        """Check rate limiting"""
        cache_key = f"{ip_address}:{user_id}"
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
            if data['count'] > self.security_rules['max_requests_per_minute']:
                # Block IP temporarily
                self.block_ip(ip_address, 'Rate limit exceeded')
                
                return {
                    'allowed': False,
                    'reason': 'Rate limit exceeded',
                    'threat_level': 'medium',
                    'action': 'block'
                }
        
        return {'allowed': True}
    
    def check_user_agent(self, user_agent: str) -> Dict:
        """Check user agent for threats"""
        ua_lower = user_agent.lower()
        
        # Check against blacklist
        for blacklisted in self.security_rules['user_agent_blacklist']:
            if blacklisted.lower() in ua_lower:
                return {
                    'allowed': False,
                    'reason': 'Blacklisted user agent',
                    'threat_level': 'high',
                    'action': 'block'
                }
        
        # Check for common bot user agents
        bot_indicators = ['bot', 'crawler', 'spider', 'scraper', 'curl', 'wget']
        for indicator in bot_indicators:
            if indicator in ua_lower:
                return {
                    'allowed': False,
                    'reason': 'Bot user agent detected',
                    'threat_level': 'medium',
                    'action': 'warn'
                }
        
        return {'allowed': True}
    
    def check_suspicious_patterns(self, user_id: int, ip_address: str, 
                                 request_type: str, details: Dict) -> Dict:
        """Check for suspicious behavior patterns"""
        patterns = []
        
        # Multiple failed logins
        if request_type == 'login_failed':
            # Track failed logins
            pattern_key = f"failed_login:{user_id}:{ip_address}"
            if pattern_key not in self.rate_limit_cache:
                self.rate_limit_cache[pattern_key] = {'count': 1, 'timestamp': time.time()}
            else:
                self.rate_limit_cache[pattern_key]['count'] += 1
                
                if self.rate_limit_cache[pattern_key]['count'] > self.security_rules['max_failed_logins']:
                    patterns.append('multiple_failed_logins')
        
        # Rapid sequence of identical requests
        if details and 'request_hash' in details:
            request_hash = details['request_hash']
            pattern_key = f"rapid_request:{request_hash}:{ip_address}"
            
            if pattern_key not in self.rate_limit_cache:
                self.rate_limit_cache[pattern_key] = {
                    'count': 1,
                    'timestamp': time.time(),
                    'first_request': time.time()
                }
            else:
                data = self.rate_limit_cache[pattern_key]
                if time.time() - data['first_request'] < 10 and data['count'] > 5:
                    patterns.append('rapid_identical_requests')
        
        # Check for SQL injection patterns
        if details and 'input_data' in details:
            input_str = json.dumps(details['input_data']).lower()
            sql_patterns = ['union select', 'select * from', 'insert into', 
                           'drop table', 'or 1=1', "' or '"]
            
            for pattern in sql_patterns:
                if pattern in input_str:
                    patterns.append('sql_injection_attempt')
                    break
        
        # Check for XSS patterns
        xss_patterns = ['<script>', 'javascript:', 'onerror=', 'onload=']
        if details and 'input_data' in details:
            input_str = json.dumps(details['input_data'])
            for pattern in xss_patterns:
                if pattern in input_str.lower():
                    patterns.append('xss_attempt')
                    break
        
        if patterns:
            threat_level = 'high' if any(p in ['sql_injection_attempt', 'xss_attempt'] for p in patterns) else 'medium'
            
            # Log threat
            self.log_threat(
                threat_type='suspicious_pattern',
                ip_address=ip_address,
                user_id=user_id,
                details={'patterns': patterns, 'request_type': request_type},
                threat_level=threat_level
            )
            
            if threat_level == 'high':
                self.block_ip(ip_address, f"Suspicious patterns: {', '.join(patterns)}")
                return {
                    'allowed': False,
                    'reason': f'Suspicious patterns detected: {", ".join(patterns)}',
                    'threat_level': threat_level,
                    'action': 'block'
                }
            else:
                return {
                    'allowed': True,
                    'reason': f'Warning: {", ".join(patterns)}',
                    'threat_level': threat_level,
                    'action': 'warn'
                }
        
        return {'allowed': True}
    
    def check_geo_location(self, ip_address: str) -> Dict:
        """Check geo-location of IP address"""
        try:
            # This is a simplified version
            # In production, you'd use a geo-IP database
            
            # Extract country code from IP (simplified)
            # In reality, you'd use a geo-IP service
            country_code = self.get_country_from_ip(ip_address)
            
            if country_code and self.security_rules['allowed_countries']:
                if country_code not in self.security_rules['allowed_countries']:
                    return {
                        'allowed': False,
                        'reason': f'Access not allowed from {country_code}',
                        'threat_level': 'medium',
                        'action': 'block'
                    }
        
        except Exception as e:
            print(f"Geo check error: {e}")
        
        return {'allowed': True}
    
    def get_country_from_ip(self, ip_address: str) -> Optional[str]:
        """Get country code from IP (simplified)"""
        # This is a mock function
        # In production, use a proper geo-IP database
        
        # Cache results
        if ip_address in self.geo_cache:
            return self.geo_cache[ip_address]
        
        # Mock: Based on IP range
        try:
            ip = ipaddress.ip_address(ip_address)
            
            # Mock country assignments
            if isinstance(ip, ipaddress.IPv4Address):
                first_octet = str(ip).split('.')[0]
                
                if first_octet in ['103', '118', '203']:
                    country = 'BD'  # Bangladesh
                elif first_octet in ['192', '172']:
                    country = 'US'  # USA
                elif first_octet in ['193', '194']:
                    country = 'GB'  # UK
                else:
                    country = None
            else:
                country = None
            
            self.geo_cache[ip_address] = country
            return country
            
        except:
            return None
    
    def block_ip(self, ip_address: str, reason: str):
        """Block an IP address"""
        self.blocked_ips.add(ip_address)
        
        # Log the block
        self.log_threat(
            threat_type='ip_blocked',
            ip_address=ip_address,
            user_id=None,
            details={'reason': reason},
            threat_level='high'
        )
        
        # Schedule unblock
        block_duration = self.security_rules.get('block_duration_minutes', 60)
        threading.Timer(
            block_duration * 60,
            self.unblock_ip,
            args=[ip_address]
        ).start()
    
    def unblock_ip(self, ip_address: str):
        """Unblock an IP address"""
        if ip_address in self.blocked_ips:
            self.blocked_ips.remove(ip_address)
            print(f"IP {ip_address} unblocked")
    
    def log_threat(self, threat_type: str, ip_address: str, user_id: Optional[int], 
                  details: Dict, threat_level: str = 'medium'):
        """Log security threat"""
        threat_entry = {
            'timestamp': datetime.now().isoformat(),
            'threat_type': threat_type,
            'ip_address': ip_address,
            'user_id': user_id,
            'details': details,
            'threat_level': threat_level
        }
        
        self.threat_log.append(threat_entry)
        
        # Keep only last 1000 threats
        if len(self.threat_log) > 1000:
            self.threat_log = self.threat_log[-1000:]
        
        # Save to file
        self.save_threat_log()
        
        # Alert if high threat
        if threat_level == 'high':
            self.alert_admin(threat_entry)
    
    def save_threat_log(self):
        """Save threat log to file"""
        try:
            with open('threat_log.json', 'w') as f:
                json.dump(self.threat_log, f, indent=2)
        except Exception as e:
            print(f"Error saving threat log: {e}")
    
    def alert_admin(self, threat_entry: Dict):
        """Alert admin about high threat"""
        # In production, this would send notification to admin
        print(f"🚨 HIGH THREAT ALERT: {threat_entry}")
    
    def cleanup_old_threats(self, days_to_keep: int = 30):
        """Clean up old threat logs"""
        cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).isoformat()
        
        self.threat_log = [
            threat for threat in self.threat_log 
            if threat['timestamp'] > cutoff_date
        ]
    
    def get_security_report(self) -> Dict:
        """Get security status report"""
        # Analyze last 24 hours
        one_day_ago = (datetime.now() - timedelta(days=1)).isoformat()
        
        recent_threats = [threat for threat in self.threat_log 
                         if threat['timestamp'] > one_day_ago]
        
        threat_by_type = {}
        threat_by_level = {'low': 0, 'medium': 0, 'high': 0}
        
        for threat in recent_threats:
            t_type = threat['threat_type']
            t_level = threat['threat_level']
            
            threat_by_type[t_type] = threat_by_type.get(t_type, 0) + 1
            threat_by_level[t_level] = threat_by_level.get(t_level, 0) + 1
        
        return {
            'blocked_ips_count': len(self.blocked_ips),
            'recent_threats_count': len(recent_threats),
            'threats_by_type': threat_by_type,
            'threats_by_level': threat_by_level,
            'security_status': self.get_security_status(threat_by_level),
            'timestamp': datetime.now().isoformat()
        }
    
    def get_security_status(self, threat_by_level: Dict) -> str:
        """Get overall security status"""
        high_threats = threat_by_level.get('high', 0)
        medium_threats = threat_by_level.get('medium', 0)
        
        if high_threats > 10:
            return 'critical'
        elif high_threats > 5 or medium_threats > 20:
            return 'warning'
        else:
            return 'secure'

# Global instance
security_monitor = SecurityMonitor()
