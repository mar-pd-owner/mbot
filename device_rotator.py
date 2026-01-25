"""
Device Rotation System
Manage and rotate device fingerprints
"""

import time
import random
import hashlib  # ADDED THIS IMPORT
import json
from typing import Dict, List
from datetime import datetime, timedelta

class DeviceRotator:
    def __init__(self, device_file: str = "devices.txt"):
        self.device_file = device_file
        self.devices = []
        self.active_devices = {}
        self.device_history = {}
        self.load_devices()
    
    def load_devices(self):
        """Load devices from file"""
        try:
            with open(self.device_file, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if line and not line.startswith('#'):
                        try:
                            device = self.parse_device_line(line)
                            if device:
                                self.devices.append(device)
                        except:
                            continue
            
            print(f"✅ Loaded {len(self.devices)} devices from {self.device_file}")
            
            # If no devices, generate some
            if len(self.devices) == 0:
                print("⚠️ No devices found, generating 100 devices...")
                self.generate_devices(100)
                self.save_devices()
                
        except FileNotFoundError:
            print("⚠️ Device file not found, generating 100 devices...")
            self.generate_devices(100)
            self.save_devices()
    
    def parse_device_line(self, line: str) -> Dict:
        """Parse device line from devices.txt"""
        parts = line.split(':')
        
        if len(parts) >= 6:
            return {
                'device_id': parts[0].strip(),
                'install_id': parts[1].strip(),
                'openudid': parts[2].strip(),
                'device_model': parts[3].strip(),
                'os_version': parts[4].strip(),
                'version_code': parts[5].strip(),
                'added_at': time.time()
            }
        elif len(parts) == 4:  # Old format
            return {
                'device_id': parts[0].strip(),
                'install_id': parts[1].strip(),
                'openudid': parts[2].strip(),
                'device_model': 'iPhone14,2',
                'os_version': '16.5',
                'version_code': '23.6.0',
                'added_at': time.time()
            }
        return None
    
    def generate_devices(self, count: int = 100):
        """Generate random devices"""
        for i in range(count):
            device = self._generate_single_device()
            self.devices.append(device)
    
    def _generate_single_device(self) -> Dict:
        """Generate a single device"""
        timestamp = int(time.time() * 1000)
        random.seed(timestamp + random.randint(1, 1000000))
        
        models = [
            ('iPhone14,2', '16.5', '23.6.0'),  # iPhone 13 Pro
            ('SM-G998B', '13', '29.2.4'),      # Samsung S21 Ultra
            ('iPhone13,3', '15.4', '22.8.0'),  # iPhone 12 Pro
            ('22081212C', '13', '30.1.0'),     # Xiaomi 12 Pro
            ('NX729J', '12', '28.5.0'),        # OnePlus 11
            ('iPhone15,3', '17.0', '31.2.0'),  # iPhone 14 Pro
            ('SM-S918B', '14', '32.1.0'),      # Samsung S23 Ultra
        ]
        
        model, os_version, version_code = random.choice(models)
        
        device_id = str(random.randint(1000000000000000000, 9999999999999999999))
        install_id = str(random.randint(1000000000000000000, 9999999999999999999))
        
        return {
            'device_id': device_id,
            'install_id': install_id,
            'openudid': hashlib.sha256(f"{device_id}{timestamp}".encode()).hexdigest().upper()[:32],
            'device_model': model,
            'os_version': os_version,
            'version_code': version_code,
            'added_at': time.time(),
            'last_used': 0,
            'use_count': 0
        }
    
    def get_device(self, video_id: str = None) -> Dict:
        """
        Get a device for use
        Strategy: Least recently used device
        """
        if not self.devices:
            return self._generate_single_device()
        
        # Filter devices not used in last 5 minutes
        available_devices = []
        current_time = time.time()
        
        for device in self.devices:
            last_used = device.get('last_used', 0)
            if current_time - last_used > 300:  # 5 minutes cooldown
                available_devices.append(device)
        
        if not available_devices:
            # All devices used recently, use least used
            available_devices = sorted(self.devices, key=lambda x: x.get('use_count', 0))
        
        # Select device
        selected = random.choice(available_devices[:10]) if len(available_devices) > 10 else available_devices[0]
        
        # Update device info
        selected['last_used'] = current_time
        selected['use_count'] = selected.get('use_count', 0) + 1
        
        # Track history
        if video_id:
            device_key = selected['device_id']
            if device_key not in self.device_history:
                self.device_history[device_key] = []
            
            self.device_history[device_key].append({
                'video_id': video_id,
                'timestamp': current_time,
                'action': 'like'
            })
            
            # Keep only last 100 entries
            if len(self.device_history[device_key]) > 100:
                self.device_history[device_key] = self.device_history[device_key][-100:]
        
        return selected
    
    def get_batch_devices(self, count: int, video_id: str = None) -> List[Dict]:
        """Get multiple devices for batch processing"""
        devices = []
        used_ids = set()
        
        for _ in range(count):
            device = self.get_device(video_id)
            
            # Ensure unique device IDs in batch
            while device['device_id'] in used_ids:
                device = self.get_device(video_id)
            
            used_ids.add(device['device_id'])
            devices.append(device)
        
        return devices
    
    def save_devices(self):
        """Save devices to file"""
        lines = []
        for device in self.devices:
            line = f"{device['device_id']}:{device['install_id']}:{device['openudid']}:{device['device_model']}:{device['os_version']}:{device['version_code']}"
            lines.append(line)
        
        with open(self.device_file, 'w') as f:
            f.write('\n'.join(lines))
        
        print(f"💾 Saved {len(lines)} devices to {self.device_file}")
    
    def add_device(self, device: Dict):
        """Add a new device"""
        self.devices.append(device)
        self.save_devices()
    
    def remove_device(self, device_id: str):
        """Remove a device"""
        self.devices = [d for d in self.devices if d['device_id'] != device_id]
        self.save_devices()
    
    def get_stats(self) -> Dict:
        """Get device statistics"""
        total_devices = len(self.devices)
        
        if total_devices == 0:
            return {"total_devices": 0}
        
        # Calculate usage
        active_devices = sum(1 for d in self.devices if time.time() - d.get('last_used', 0) < 3600)
        avg_use_count = sum(d.get('use_count', 0) for d in self.devices) / total_devices
        
        # Device models distribution
        models = {}
        for device in self.devices:
            model = device['device_model']
            models[model] = models.get(model, 0) + 1
        
        return {
            "total_devices": total_devices,
            "active_devices": active_devices,
            "average_use_count": round(avg_use_count, 2),
            "device_models": models,
            "device_history_entries": sum(len(v) for v in self.device_history.values())
        }
    
    def cleanup_old_devices(self, days_old: int = 7):
        """Remove devices older than X days"""
        current_time = time.time()
        cutoff = current_time - (days_old * 24 * 3600)
        
        old_count = len(self.devices)
        self.devices = [d for d in self.devices if d.get('added_at', current_time) > cutoff]
        new_count = len(self.devices)
        
        removed = old_count - new_count
        if removed > 0:
            print(f"🧹 Removed {removed} old devices (older than {days_old} days)")
            self.save_devices()
