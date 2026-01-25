"""
Auto Update System for MBOT
Handles version updates and patches
"""

import json
import os
import sys
import time
import hashlib
import requests
from typing import Dict, Optional
import base64

class UpdateSystem:
    def __init__(self):
        self.config_file = 'config.json'
        self.update_server = "https://raw.githubusercontent.com/your-repo/mbot-updates/main/"
        self.current_version = 1
        self.real_version = 75
        self.update_available = False
        self.update_info = {}
        
        # Load update config
        self.load_update_config()
    
    def load_update_config(self):
        """Load update configuration"""
        try:
            with open('update_config.json', 'r') as f:
                self.update_config = json.load(f)
        except:
            self.update_config = {
                "auto_update": True,
                "check_interval": 3600,  # 1 hour
                "last_check": 0,
                "update_channel": "stable"
            }
    
    def check_for_updates(self) -> bool:
        """Check for available updates"""
        current_time = time.time()
        
        # Check if enough time has passed
        if current_time - self.update_config['last_check'] < self.update_config['check_interval']:
            return False
        
        try:
            # Fetch update info from server
            response = requests.get(
                f"{self.update_server}updates.json",
                timeout=10
            )
            
            if response.status_code == 200:
                updates = response.json()
                
                # Check for updates based on real version
                latest_version = updates.get('real_version', 1)
                
                if latest_version > self.real_version:
                    self.update_available = True
                    self.update_info = updates
                    
                    # Log update availability
                    self.log_update(f"Update available: v{latest_version}")
                    
                    return True
        
        except Exception as e:
            self.log_update(f"Error checking updates: {e}")
        
        self.update_config['last_check'] = current_time
        self.save_update_config()
        
        return False
    
    def apply_update(self) -> bool:
        """Apply available update"""
        if not self.update_available:
            return False
        
        try:
            update_url = self.update_info.get('download_url')
            if not update_url:
                return False
            
            # Download update
            response = requests.get(update_url, timeout=30)
            if response.status_code != 200:
                return False
            
            # Decode update (base64 encoded)
            update_data = base64.b64decode(response.content)
            
            # Verify checksum
            expected_hash = self.update_info.get('sha256')
            actual_hash = hashlib.sha256(update_data).hexdigest()
            
            if expected_hash and actual_hash != expected_hash:
                self.log_update("Checksum verification failed")
                return False
            
            # Apply update
            self.apply_update_files(update_data)
            
            # Update version info
            self.real_version = self.update_info.get('real_version', self.real_version)
            
            self.log_update(f"Successfully updated to v{self.real_version}")
            
            return True
            
        except Exception as e:
            self.log_update(f"Error applying update: {e}")
            return False
    
    def apply_update_files(self, update_data: bytes):
        """Apply update files from update data"""
        try:
            # Update data is a zip file in reality
            # For now, we'll implement a simple update
            updates = json.loads(update_data.decode())
            
            for filename, content in updates.get('files', {}).items():
                if filename.endswith('.py'):
                    # Backup original file
                    if os.path.exists(filename):
                        backup_name = f"{filename}.backup_{int(time.time())}"
                        os.rename(filename, backup_name)
                    
                    # Write updated file
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(content)
                
                elif filename.endswith('.json'):
                    # Update JSON files carefully
                    self.update_json_file(filename, content)
            
            # Update config
            if 'config_updates' in updates:
                self.update_config_file(updates['config_updates'])
            
        except Exception as e:
            self.log_update(f"Error applying files: {e}")
            raise
    
    def update_json_file(self, filename: str, updates: Dict):
        """Update JSON file with new data"""
        try:
            if os.path.exists(filename):
                with open(filename, 'r') as f:
                    current_data = json.load(f)
            else:
                current_data = {}
            
            # Merge updates
            self.merge_dict(current_data, updates)
            
            # Save updated file
            with open(filename, 'w') as f:
                json.dump(current_data, f, indent=2)
                
        except Exception as e:
            self.log_update(f"Error updating {filename}: {e}")
    
    def update_config_file(self, updates: Dict):
        """Update config file"""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
            
            # Merge updates
            self.merge_dict(config, updates)
            
            # Save updated config
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
                
        except Exception as e:
            self.log_update(f"Error updating config: {e}")
    
    def merge_dict(self, target: Dict, source: Dict):
        """Recursively merge dictionaries"""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self.merge_dict(target[key], value)
            else:
                target[key] = value
    
    def get_version_info(self) -> Dict:
        """Get complete version information"""
        return {
            "display_version": self.current_version,
            "real_version": self.real_version,
            "update_available": self.update_available,
            "latest_version": self.update_info.get('real_version', self.real_version) if self.update_available else self.real_version,
            "update_channel": self.update_config['update_channel'],
            "auto_update": self.update_config['auto_update']
        }
    
    def log_update(self, message: str):
        """Log update activities"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] UPDATE: {message}\n"
        
        with open('update.log', 'a') as f:
            f.write(log_entry)
    
    def save_update_config(self):
        """Save update configuration"""
        with open('update_config.json', 'w') as f:
            json.dump(self.update_config, f, indent=2)
    
    def run_update_check(self):
        """Run update check in background"""
        if self.update_config['auto_update']:
            if self.check_for_updates():
                if self.update_config['update_channel'] == 'stable':
                    # Apply update automatically for stable channel
                    if self.apply_update():
                        # Restart after update
                        self.restart_application()
    
    def restart_application(self):
        """Restart the application"""
        self.log_update("Restarting application after update...")
        os.execv(sys.executable, ['python'] + sys.argv)

# Global instance
update_system = UpdateSystem()

def check_and_apply_updates():
    """Check and apply updates"""
    return update_system.run_update_check()

def get_version():
    """Get version information"""
    return update_system.get_version_info()
