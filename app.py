import streamlit as st
import json
import hashlib
from datetime import datetime, timedelta
import jwt
from config import COOKIE_NAME, COOKIE_KEY, USERS_FILE
import os

class AuthSystem:
    def __init__(self):
        self.users = self.load_users()
        
    def load_users(self):
        """تحميل بيانات المستخدمين"""
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # بيانات افتراضية
            default_users = {
                "admin": {
                    "username": "admin",
                    "password": self.hash_password("admin123"),
                    "email": "admin@example.com",
                    "role": "admin",
                    "created_at": datetime.now().isoformat()
                }
            }
            self.save_users(default_users)
            return default_users
    
    def save_users(self, users_data):
        """حفظ بيانات المستخدمين"""
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(users_data, f, ensure_ascii=False, indent=2)
    
    def hash_password(self, password):
        """تشفير كلمة المرور"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def verify_password(self, password, hashed):
        """التحقق من كلمة المرور"""
        return self.hash_password(password) == hashed
    
    def create_token(self, username, role):
        """إنشاء توكن للمستخدم"""
        payload = {
            'username': username,
            'role': role,
            'exp': datetime.utcnow() + timedelta(hours=24)
        }
        return jwt.encode(payload, COOKIE_KEY, algorithm='HS256')
    
    def verify_token(self, token):
        """التحقق من صحة التوكن"""
        try:
            payload = jwt.decode(token, COOKIE_KEY, algorithms=['HS256'])
            return payload
        except:
            return None
    
    def register_user(self, username, password, email, role="user"):
        """تسجيل مستخدم جديد"""
        if username in self.users:
            return False, "اسم المستخدم موجود مسبقاً"
        
        self.users[username] = {
            "username": username,
            "password": self.hash_password(password),
            "email": email,
            "role": role,
            "created_at": datetime.now().isoformat()
        }
        
        self.save_users(self.users)
        return True, "تم التسجيل بنجاح"
    
    def login(self, username, password):
        """تسجيل الدخول"""
        if username not in self.users:
            return False, "اسم المستخدم غير صحيح"
        
        user = self.users[username]
        if not self.verify_password(password, user['password']):
            return False, "كلمة المرور غير صحيحة"
        
        token = self.create_token(username, user['role'])
        return True, token
    
    def logout(self):
        """تسجيل الخروج"""
        st.session_state.pop('token', None)
        st.session_state.pop('user_info', None)
        st.rerun()

def check_auth():
    """التحقق من حالة المصادقة"""
    auth = AuthSystem()
    
    if 'token' not in st.session_state:
        return None
    
    payload = auth.verify_token(st.session_state.token)
    if not payload:
        st.session_state.pop('token', None)
        st.rerun()
    
    return payload
