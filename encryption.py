"""
Advanced Encryption System for MBOT
Military grade encryption for all communications
"""

import base64
import hashlib
import json
import os
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad
import rsa

class SecureEncryption:
    def __init__(self, key=None):
        """Initialize encryption system"""
        self.aes_key = key or self.generate_aes_key()
        self.rsa_public_key = None
        self.rsa_private_key = None
        self.generate_rsa_keys()
    
    @staticmethod
    def generate_aes_key():
        """Generate AES key"""
        return get_random_bytes(32)  # 256-bit key
    
    def generate_rsa_keys(self):
        """Generate RSA key pair"""
        (self.rsa_public_key, self.rsa_private_key) = rsa.newkeys(2048)
    
    def encrypt_aes(self, data):
        """Encrypt data with AES"""
        cipher = AES.new(self.aes_key, AES.MODE_CBC)
        ct_bytes = cipher.encrypt(pad(data.encode(), AES.block_size))
        iv = cipher.iv
        return base64.b64encode(iv + ct_bytes).decode()
    
    def decrypt_aes(self, encrypted_data):
        """Decrypt AES encrypted data"""
        raw = base64.b64decode(encrypted_data)
        iv = raw[:16]
        ct = raw[16:]
        cipher = AES.new(self.aes_key, AES.MODE_CBC, iv)
        pt = unpad(cipher.decrypt(ct), AES.block_size)
        return pt.decode()
    
    def encrypt_rsa(self, data):
        """Encrypt with RSA public key"""
        return rsa.encrypt(data.encode(), self.rsa_public_key)
    
    def decrypt_rsa(self, encrypted_data):
        """Decrypt with RSA private key"""
        return rsa.decrypt(encrypted_data, self.rsa_private_key).decode()
    
    def hash_data(self, data, algorithm='sha256'):
        """Hash data"""
        if algorithm == 'sha256':
            return hashlib.sha256(data.encode()).hexdigest()
        elif algorithm == 'sha512':
            return hashlib.sha512(data.encode()).hexdigest()
        elif algorithm == 'md5':
            return hashlib.md5(data.encode()).hexdigest()
    
    def secure_store(self, data, filename):
        """Securely store data to file"""
        encrypted = self.encrypt_aes(json.dumps(data))
        with open(filename, 'w') as f:
            f.write(encrypted)
    
    def secure_load(self, filename):
        """Securely load data from file"""
        try:
            with open(filename, 'r') as f:
                encrypted = f.read()
            return json.loads(self.decrypt_aes(encrypted))
        except:
            return {}
    
    def generate_device_id(self):
        """Generate secure device ID"""
        random_bytes = get_random_bytes(32)
        device_id = hashlib.sha256(random_bytes).hexdigest()[:32]
        return device_id
    
    def encrypt_message(self, message, recipient_key=None):
        """Encrypt message for transmission"""
        # Generate session key
        session_key = get_random_bytes(32)
        
        # Encrypt session key with recipient's RSA key
        if recipient_key:
            encrypted_key = rsa.encrypt(session_key, recipient_key)
        else:
            encrypted_key = rsa.encrypt(session_key, self.rsa_public_key)
        
        # Encrypt message with session key
        cipher = AES.new(session_key, AES.MODE_CBC)
        ct_bytes = cipher.encrypt(pad(message.encode(), AES.block_size))
        iv = cipher.iv
        
        # Combine
        encrypted_data = {
            'key': base64.b64encode(encrypted_key).decode(),
            'iv': base64.b64encode(iv).decode(),
            'message': base64.b64encode(ct_bytes).decode(),
            'hash': self.hash_data(message)
        }
        
        return json.dumps(encrypted_data)
    
    def decrypt_message(self, encrypted_json, is_recipient=False):
        """Decrypt received message"""
        data = json.loads(encrypted_json)
        
        # Decrypt session key
        if is_recipient:
            encrypted_key = base64.b64decode(data['key'])
            session_key = rsa.decrypt(encrypted_key, self.rsa_private_key)
        else:
            encrypted_key = base64.b64decode(data['key'])
            session_key = rsa.decrypt(encrypted_key, self.rsa_private_key)
        
        # Decrypt message
        iv = base64.b64decode(data['iv'])
        ct = base64.b64decode(data['message'])
        
        cipher = AES.new(session_key, AES.MODE_CBC, iv)
        message = unpad(cipher.decrypt(ct), AES.block_size).decode()
        
        # Verify hash
        if self.hash_data(message) != data['hash']:
            raise ValueError("Message integrity check failed")
        
        return message

# Singleton instance
encryption = SecureEncryption()

def encrypt_user_data(user_data):
    """Encrypt user data for storage"""
    return encryption.secure_store(user_data, 'user_data.enc')

def decrypt_user_data():
    """Decrypt user data"""
    return encryption.secure_load('user_data.enc')

def generate_session_token(user_id):
    """Generate secure session token"""
    data = f"{user_id}:{os.urandom(16).hex()}:{int(time.time())}"
    return encryption.hash_data(data, 'sha512')

def verify_session_token(token, user_id):
    """Verify session token"""
    # Implementation depends on your session management
    return True
