import streamlit as st
import pandas as pd
import json
import os
import io
import requests
import shutil
import re
from datetime import datetime, timedelta
from base64 import b64decode
import uuid

# محاولة استيراد PyGithub (لرفع التعديلات)
try:
    from github import Github
    GITHUB_AVAILABLE = True
except Exception:
    GITHUB_AVAILABLE = False

# ===============================
# ⚙ إعدادات التطبيق - يمكن تعديلها بسهولة
# ===============================
APP_CONFIG = {
    # إعدادات التطبيق العامة
    "APP_TITLE": "CMMS - نظام إدارة الصيانة المرن",
    "APP_ICON": "🏭",
    
    # إعدادات GitHub
    "REPO_NAME": "mahmedabdallh123/BELYARN",
    "BRANCH": "main",
    "FILE_PATH": "machines_database.xlsx",  # تغيير الاسم ليكون أكثر دلالة
    "LOCAL_FILE": "machines_database.xlsx",
    
    # إعدادات الأمان
    "MAX_ACTIVE_USERS": 5,  # زيادة عدد المستخدمين
    "SESSION_DURATION_MINUTES": 60,  # زيادة وقت الجلسة
    
    # إعدادات الواجهة
    "SHOW_TECH_SUPPORT_TO_ALL": True,
    "CUSTOM_TABS": ["📋 البحث في الماكينات", "🛠 إدارة الماكينات", "➕ إضافة نوع مكن", "👥 إدارة المستخدمين", "⚙️ الإعدادات", "📞 الدعم الفني"],
    
    # إعدادات الصور
    "IMAGES_FOLDER": "machine_images",
    "ALLOWED_IMAGE_TYPES": ["jpg", "jpeg", "png", "gif", "bmp", "webp"],
    "MAX_IMAGE_SIZE_MB": 10,  # زيادة حجم الصور
    
    # إعدادات الشيتات
    "ALLOW_ANY_SHEET_NAME": True,
    
    # إعدادات الماكينات
    "MACHINE_TYPES_FILE": "machine_types.json",
    "MACHINE_CATEGORIES": ["معدات إنتاج", "ماكينات تصنيع", "أجهزة قياس", "معدات مساعدة", "أخرى"],
    
    # إعدادات البحث
    "SEARCH_HISTORY_SIZE": 20,
    "FAVORITE_MACHINES_LIMIT": 50
}

# ===============================
# 🗂 إعدادات الملفات
# ===============================
USERS_FILE = "users.json"
STATE_FILE = "state.json"
NOTIFICATIONS_FILE = "notifications.json"
MACHINE_TYPES_FILE = APP_CONFIG["MACHINE_TYPES_FILE"]
SEARCH_HISTORY_FILE = "search_history.json"
FAVORITES_FILE = "favorites.json"

SESSION_DURATION = timedelta(minutes=APP_CONFIG["SESSION_DURATION_MINUTES"])
MAX_ACTIVE_USERS = APP_CONFIG["MAX_ACTIVE_USERS"]
IMAGES_FOLDER = APP_CONFIG["IMAGES_FOLDER"]

# إنشاء رابط GitHub تلقائياً من الإعدادات
GITHUB_EXCEL_URL = f"https://github.com/{APP_CONFIG['REPO_NAME'].split('/')[0]}/{APP_CONFIG['REPO_NAME'].split('/')[1]}/raw/{APP_CONFIG['BRANCH']}/{APP_CONFIG['FILE_PATH']}"

# -------------------------------
# 🔔 دوال جديدة للإشعارات
# -------------------------------
def load_notifications():
    """تحميل الإشعارات من ملف"""
    if not os.path.exists(NOTIFICATIONS_FILE):
        with open(NOTIFICATIONS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, indent=4, ensure_ascii=False)
        return []
    
    try:
        with open(NOTIFICATIONS_FILE, "r", encoding="utf-8") as f:
            notifications = json.load(f)
        return notifications
    except Exception as e:
        st.error(f"❌ خطأ في تحميل الإشعارات: {e}")
        return []

def save_notifications(notifications):
    """حفظ الإشعارات إلى ملف"""
    try:
        with open(NOTIFICATIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(notifications, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        st.error(f"❌ خطأ في حفظ الإشعارات: {e}")
        return False

def add_notification(username, action, details, target_sheet=None, target_row=None, machine_id=None):
    """إضافة إشعار جديد"""
    notifications = load_notifications()
    
    new_notification = {
        "id": str(uuid.uuid4()),
        "username": username,
        "action": action,
        "details": details,
        "target_sheet": target_sheet,
        "target_row": target_row,
        "machine_id": machine_id,
        "timestamp": datetime.now().isoformat(),
        "read_by_admin": False
    }
    
    notifications.insert(0, new_notification)  # إضافة في البداية
    save_notifications(notifications)
    return new_notification

def mark_notifications_as_read():
    """تحديد الإشعارات كمقروءة"""
    notifications = load_notifications()
    for notification in notifications:
        notification["read_by_admin"] = True
    save_notifications(notifications)

def clear_all_notifications():
    """حذف جميع الإشعارات"""
    save_notifications([])

def show_notifications_ui():
    """عرض واجهة الإشعارات"""
    if st.session_state.get("user_role") != "admin":
        return
    
    notifications = load_notifications()
    unread_count = sum(1 for n in notifications if not n.get("read_by_admin", False))
    
    with st.sidebar:
        st.markdown("---")
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"### 🔔 الإشعارات")
        with col2:
            if unread_count > 0:
                st.markdown(f"<span style='color:red; font-weight:bold;'>{unread_count} جديد</span>", unsafe_allow_html=True)
        
        if notifications:
            # زر لتصفية الإشعارات
            filter_option = st.selectbox(
                "تصفية الإشعارات:",
                ["جميع الإشعارات", "غير المقروءة فقط", "المقروءة فقط"],
                key="notifications_filter"
            )
            
            # تطبيق التصفية
            if filter_option == "غير المقروءة فقط":
                filtered_notifications = [n for n in notifications if not n.get("read_by_admin", False)]
            elif filter_option == "المقروءة فقط":
                filtered_notifications = [n for n in notifications if n.get("read_by_admin", False)]
            else:
                filtered_notifications = notifications
            
            # عرض الإشعارات
            for i, notification in enumerate(filtered_notifications[:10]):  # عرض أول 10 إشعارات
                with st.expander(f"{notification['action']} - {notification['username']}", expanded=(i < 3 and not notification.get('read_by_admin', False))):
                    st.markdown(f"**المستخدم:** {notification['username']}")
                    st.markdown(f"**الإجراء:** {notification['action']}")
                    st.markdown(f"**التفاصيل:** {notification['details']}")
                    if notification.get('target_sheet'):
                        st.markdown(f"**الشيت:** {notification['target_sheet']}")
                    if notification.get('machine_id'):
                        st.markdown(f"**رقم الماكينة:** {notification['machine_id']}")
                    st.markdown(f"**الوقت:** {datetime.fromisoformat(notification['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}")
                    
                    if not notification.get('read_by_admin', False):
                        if st.button("✅ تحديد كمقروء", key=f"mark_read_{notification['id']}"):
                            notification['read_by_admin'] = True
                            save_notifications(notifications)
                            st.rerun()
            
            # أزرار التحكم
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("✅ تحديد الكل كمقروء", key="mark_all_read"):
                    mark_notifications_as_read()
                    st.rerun()
            with col_btn2:
                if st.button("🗑️ حذف جميع الإشعارات", key="clear_all_notifs"):
                    clear_all_notifications()
                    st.rerun()
            
            if len(filtered_notifications) > 10:
                st.caption(f"... و {len(filtered_notifications) - 10} إشعارات أخرى")
        else:
            st.info("📭 لا توجد إشعارات جديدة")

# -------------------------------
# 📁 دوال إدارة أنواع الماكينات
# -------------------------------
def load_machine_types():
    """تحميل أنواع الماكينات من ملف"""
    if not os.path.exists(MACHINE_TYPES_FILE):
        # إنشاء أنواع افتراضية
        default_types = {
            "spinning_machine": {
                "name": "ماكينة غزل",
                "category": "معدات إنتاج",
                "description": "ماكينات الغزل والإنتاج",
                "fields": {
                    "machine_id": {"type": "text", "required": True, "label": "رقم الماكينة"},
                    "machine_name": {"type": "text", "required": True, "label": "اسم الماكينة"},
                    "model": {"type": "text", "required": False, "label": "الموديل"},
                    "serial_number": {"type": "text", "required": False, "label": "الرقم التسلسلي"},
                    "installation_date": {"type": "date", "required": False, "label": "تاريخ التركيب"},
                    "location": {"type": "text", "required": False, "label": "الموقع"},
                    "status": {"type": "select", "required": True, "label": "الحالة", 
                             "options": ["نشطة", "متوقفة", "تحت الصيانة", "معطلة"]},
                    "last_maintenance": {"type": "date", "required": False, "label": "آخر صيانة"},
                    "next_maintenance": {"type": "date", "required": False, "label": "الصيانة القادمة"},
                    "notes": {"type": "textarea", "required": False, "label": "ملاحظات"}
                },
                "default_columns": ["machine_id", "machine_name", "model", "serial_number", "status", "last_maintenance"],
                "created_at": datetime.now().isoformat(),
                "created_by": "system"
            },
            "weaving_machine": {
                "name": "ماكينة نسيج",
                "category": "معدات إنتاج",
                "description": "ماكينات النسيج والحياكة",
                "fields": {
                    "machine_id": {"type": "text", "required": True, "label": "رقم الماكينة"},
                    "machine_name": {"type": "text", "required": True, "label": "اسم الماكينة"},
                    "type": {"type": "select", "required": True, "label": "النوع", 
                            "options": ["نسيج", "حياكة", "تريكو"]},
                    "speed": {"type": "number", "required": False, "label": "السرعة (دورة/دقيقة)"},
                    "width": {"type": "number", "required": False, "label": "العرض (سم)"},
                    "status": {"type": "select", "required": True, "label": "الحالة", 
                             "options": ["نشطة", "متوقفة", "تحت الصيانة", "معطلة"]},
                    "maintenance_history": {"type": "textarea", "required": False, "label": "سجل الصيانة"},
                    "images": {"type": "images", "required": False, "label": "صور الماكينة"}
                },
                "default_columns": ["machine_id", "machine_name", "type", "speed", "width", "status"],
                "created_at": datetime.now().isoformat(),
                "created_by": "system"
            }
        }
        
        with open(MACHINE_TYPES_FILE, "w", encoding="utf-8") as f:
            json.dump(default_types, f, indent=4, ensure_ascii=False)
        
        return default_types
    
    try:
        with open(MACHINE_TYPES_FILE, "r", encoding="utf-8") as f:
            machine_types = json.load(f)
        return machine_types
    except Exception as e:
        st.error(f"❌ خطأ في تحميل أنواع الماكينات: {e}")
        return {}

def save_machine_types(machine_types):
    """حفظ أنواع الماكينات إلى ملف"""
    try:
        with open(MACHINE_TYPES_FILE, "w", encoding="utf-8") as f:
            json.dump(machine_types, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        st.error(f"❌ خطأ في حفظ أنواع الماكينات: {e}")
        return False

def get_machine_type_fields(machine_type_id):
    """الحصول على حقول نوع معين من الماكينات"""
    machine_types = load_machine_types()
    if machine_type_id in machine_types:
        return machine_types[machine_type_id].get("fields", {})
    return {}

def add_machine_type(machine_type_id, machine_type_data):
    """إضافة نوع مكن جديد"""
    machine_types = load_machine_types()
    
    if machine_type_id in machine_types:
        return False, "نوع الماكينة موجود بالفعل"
    
    machine_types[machine_type_id] = machine_type_data
    if save_machine_types(machine_types):
        return True, "تم إضافة نوع الماكينة بنجاح"
    return False, "حدث خطأ أثناء الحفظ"

def update_machine_type(machine_type_id, machine_type_data):
    """تحديث نوع مكن"""
    machine_types = load_machine_types()
    
    if machine_type_id not in machine_types:
        return False, "نوع الماكينة غير موجود"
    
    machine_types[machine_type_id] = machine_type_data
    if save_machine_types(machine_types):
        return True, "تم تحديث نوع الماكينة بنجاح"
    return False, "حدث خطأ أثناء الحفظ"

def delete_machine_type(machine_type_id):
    """حذف نوع مكن"""
    machine_types = load_machine_types()
    
    if machine_type_id not in machine_types:
        return False, "نوع الماكينة غير موجود"
    
    # التحقق من عدم وجود ماكينات من هذا النوع في قاعدة البيانات
    all_sheets = load_all_sheets()
    for sheet_name, df in all_sheets.items():
        if sheet_name == machine_type_id:
            return False, "لا يمكن حذف النوع لأنه يحتوي على ماكينات مسجلة"
    
    del machine_types[machine_type_id]
    if save_machine_types(machine_types):
        return True, "تم حذف نوع الماكينة بنجاح"
    return False, "حدث خطأ أثناء الحذف"

# -------------------------------
# 🔍 دوال البحث والتاريخ
# -------------------------------
def load_search_history():
    """تحميل سجل البحث"""
    if not os.path.exists(SEARCH_HISTORY_FILE):
        with open(SEARCH_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, indent=4, ensure_ascii=False)
        return []
    
    try:
        with open(SEARCH_HISTORY_FILE, "r", encoding="utf-8") as f:
            history = json.load(f)
        return history
    except Exception as e:
        st.error(f"❌ خطأ في تحميل سجل البحث: {e}")
        return []

def save_search_history(history):
    """حفظ سجل البحث"""
    try:
        # حفظ آخر 20 عملية بحث فقط
        if len(history) > APP_CONFIG["SEARCH_HISTORY_SIZE"]:
            history = history[:APP_CONFIG["SEARCH_HISTORY_SIZE"]]
        
        with open(SEARCH_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        st.error(f"❌ خطأ في حفظ سجل البحث: {e}")
        return False

def add_to_search_history(search_params):
    """إضافة بحث إلى السجل"""
    history = load_search_history()
    
    # إضافة الطابع الزمني
    search_params["timestamp"] = datetime.now().isoformat()
    search_params["user"] = st.session_state.get("username", "غير معروف")
    
    # إضافة في البداية
    history.insert(0, search_params)
    save_search_history(history)

def load_favorites():
    """تحميل المفضلة"""
    if not os.path.exists(FAVORITES_FILE):
        with open(FAVORITES_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=4, ensure_ascii=False)
        return {}
    
    try:
        with open(FAVORITES_FILE, "r", encoding="utf-8") as f:
            favorites = json.load(f)
        return favorites
    except Exception as e:
        st.error(f"❌ خطأ في تحميل المفضلة: {e}")
        return {}

def save_favorites(favorites):
    """حفظ المفضلة"""
    try:
        with open(FAVORITES_FILE, "w", encoding="utf-8") as f:
            json.dump(favorites, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        st.error(f"❌ خطأ في حفظ المفضلة: {e}")
        return False

def toggle_favorite(machine_type, machine_id):
    """إضافة/إزالة ماكينة من المفضلة"""
    favorites = load_favorites()
    username = st.session_state.get("username", "unknown")
    
    if username not in favorites:
        favorites[username] = []
    
    # إنشاء مفتاح الماكينة
    machine_key = f"{machine_type}:{machine_id}"
    
    if machine_key in favorites[username]:
        favorites[username].remove(machine_key)
        is_favorite = False
    else:
        # التحقق من الحد الأقصى
        if len(favorites[username]) >= APP_CONFIG["FAVORITE_MACHINES_LIMIT"]:
            return False, "تم الوصول إلى الحد الأقصى للمفضلة"
        favorites[username].append(machine_key)
        is_favorite = True
    
    save_favorites(favorites)
    return True, "تم التحديث" if is_favorite else "تمت الإزالة"

def is_favorite(machine_type, machine_id):
    """التحقق إذا كانت الماكينة في المفضلة"""
    favorites = load_favorites()
    username = st.session_state.get("username", "unknown")
    
    if username not in favorites:
        return False
    
    machine_key = f"{machine_type}:{machine_id}"
    return machine_key in favorites[username]

def get_favorites_for_user():
    """الحصول على المفضلة للمستخدم الحالي"""
    favorites = load_favorites()
    username = st.session_state.get("username", "unknown")
    
    if username not in favorites:
        return []
    
    return favorites[username]

# -------------------------------
# 🧩 دوال مساعدة للصور
# -------------------------------
def setup_images_folder():
    """إنشاء وإعداد مجلد الصور"""
    if not os.path.exists(IMAGES_FOLDER):
        os.makedirs(IMAGES_FOLDER)
        # إنشاء ملف .gitkeep لجعل المجلد فارغاً في GitHub
        with open(os.path.join(IMAGES_FOLDER, ".gitkeep"), "w") as f:
            pass

def save_uploaded_images(uploaded_files):
    """حفظ الصور المرفوعة وإرجاع أسماء الملفات"""
    if not uploaded_files:
        return []
    
    saved_files = []
    for uploaded_file in uploaded_files:
        # التحقق من نوع الملف
        file_extension = uploaded_file.name.split('.')[-1].lower()
        if file_extension not in APP_CONFIG["ALLOWED_IMAGE_TYPES"]:
            st.warning(f"⚠ تم تجاهل الملف {uploaded_file.name} لأن نوعه غير مدعوم")
            continue
        
        # التحقق من حجم الملف
        file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
        if file_size_mb > APP_CONFIG["MAX_IMAGE_SIZE_MB"]:
            st.warning(f"⚠ تم تجاهل الملف {uploaded_file.name} لأن حجمه ({file_size_mb:.2f}MB) يتجاوز الحد المسموح ({APP_CONFIG['MAX_IMAGE_SIZE_MB']}MB)")
            continue
        
        # إنشاء اسم فريد للملف
        unique_id = str(uuid.uuid4())[:8]
        original_name = uploaded_file.name.split('.')[0]
        safe_name = re.sub(r'[^\w\-_]', '_', original_name)
        new_filename = f"{safe_name}_{unique_id}.{file_extension}"
        
        # حفظ الملف
        file_path = os.path.join(IMAGES_FOLDER, new_filename)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        saved_files.append(new_filename)
    
    return saved_files

def delete_image_file(image_filename):
    """حذف ملف صورة"""
    try:
        file_path = os.path.join(IMAGES_FOLDER, image_filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
    except Exception as e:
        st.error(f"❌ خطأ في حذف الصورة {image_filename}: {e}")
    return False

def get_image_url(image_filename):
    """الحصول على رابط الصورة للعرض"""
    if not image_filename:
        return None
    
    file_path = os.path.join(IMAGES_FOLDER, image_filename)
    if os.path.exists(file_path):
        # في Streamlit Cloud، نستخدم absolute path
        return file_path
    return None

def display_images(image_filenames, caption="الصور المرفقة"):
    """عرض الصور في واجهة المستخدم"""
    if not image_filenames:
        return
    
    st.markdown(f"**{caption}:**")
    
    # تقسيم الصور إلى أعمدة
    images_per_row = 3
    images = image_filenames.split(',') if isinstance(image_filenames, str) else image_filenames
    
    for i in range(0, len(images), images_per_row):
        cols = st.columns(images_per_row)
        for j in range(images_per_row):
            idx = i + j
            if idx < len(images):
                image_filename = images[idx].strip()
                with cols[j]:
                    image_path = get_image_url(image_filename)
                    if image_path and os.path.exists(image_path):
                        try:
                            st.image(image_path, caption=image_filename, use_column_width=True)
                        except:
                            st.write(f"📷 {image_filename}")
                    else:
                        st.write(f"📷 {image_filename} (غير موجود)")

# -------------------------------
# 🧩 دوال مساعدة للملفات والحالة
# -------------------------------
def load_users():
    """تحميل بيانات المستخدمين من ملف JSON"""
    if not os.path.exists(USERS_FILE):
        # إنشاء مستخدمين افتراضيين
        default_users = {
            "admin": {
                "password": "admin123", 
                "role": "admin", 
                "created_at": datetime.now().isoformat(),
                "permissions": ["all"],
                "full_name": "المسؤول الرئيسي",
                "email": "admin@company.com",
                "department": "الإدارة"
            },
            "viewer": {
                "password": "viewer123", 
                "role": "viewer", 
                "created_at": datetime.now().isoformat(),
                "permissions": ["view"],
                "full_name": "مستخدم للعرض فقط",
                "email": "viewer@company.com",
                "department": "المراقبة"
            }
        }
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(default_users, f, indent=4, ensure_ascii=False)
        return default_users
    
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            users = json.load(f)
        
        # التأكد من وجود المستخدم admin
        if "admin" not in users:
            users["admin"] = {
                "password": "admin123", 
                "role": "admin", 
                "created_at": datetime.now().isoformat(),
                "permissions": ["all"],
                "full_name": "المسؤول الرئيسي",
                "email": "admin@company.com",
                "department": "الإدارة"
            }
            save_users(users)
        
        return users
    except Exception as e:
        st.error(f"❌ خطأ في ملف users.json: {e}")
        # إرجاع المستخدمين الافتراضيين في حالة الخطأ
        return {
            "admin": {
                "password": "admin123", 
                "role": "admin", 
                "created_at": datetime.now().isoformat(),
                "permissions": ["all"],
                "full_name": "المسؤول الرئيسي",
                "email": "admin@company.com",
                "department": "الإدارة"
            }
        }

def save_users(users):
    """حفظ بيانات المستخدمين إلى ملف JSON"""
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        st.error(f"❌ خطأ في حفظ ملف users.json: {e}")
        return False

def load_state():
    """تحميل حالة الجلسات"""
    if not os.path.exists(STATE_FILE):
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=4, ensure_ascii=False)
        return {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_state(state):
    """حفظ حالة الجلسات"""
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=4, ensure_ascii=False)

def cleanup_sessions(state):
    """تنظيف الجلسات المنتهية"""
    now = datetime.now()
    changed = False
    for user, info in list(state.items()):
        if info.get("active") and "login_time" in info:
            try:
                login_time = datetime.fromisoformat(info["login_time"])
                if now - login_time > SESSION_DURATION:
                    info["active"] = False
                    info.pop("login_time", None)
                    changed = True
            except:
                info["active"] = False
                changed = True
    if changed:
        save_state(state)
    return state

def remaining_time(state, username):
    """حساب الوقت المتبقي للجلسة"""
    if not username or username not in state:
        return None
    info = state.get(username)
    if not info or not info.get("active"):
        return None
    try:
        lt = datetime.fromisoformat(info["login_time"])
        remaining = SESSION_DURATION - (datetime.now() - lt)
        if remaining.total_seconds() <= 0:
            return None
        return remaining
    except:
        return None

# -------------------------------
# 🔐 تسجيل الخروج
# -------------------------------
def logout_action():
    """تنفيذ تسجيل الخروج"""
    state = load_state()
    username = st.session_state.get("username")
    if username and username in state:
        state[username]["active"] = False
        state[username].pop("login_time", None)
        save_state(state)
    keys = list(st.session_state.keys())
    for k in keys:
        st.session_state.pop(k, None)
    st.rerun()

# -------------------------------
# 🧠 واجهة تسجيل الدخول
# -------------------------------
def login_ui():
    """عرض واجهة تسجيل الدخول"""
    users = load_users()
    state = cleanup_sessions(load_state())
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.user_role = None
        st.session_state.user_permissions = []

    st.title(f"{APP_CONFIG['APP_ICON']} تسجيل الدخول - {APP_CONFIG['APP_TITLE']}")

    # تحميل قائمة المستخدمين
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            current_users = json.load(f)
        user_list = list(current_users.keys())
    except:
        user_list = list(users.keys())

    # اختيار المستخدم
    username_input = st.selectbox("👤 اختر المستخدم", user_list)
    password = st.text_input("🔑 كلمة المرور", type="password")

    active_users = [u for u, v in state.items() if v.get("active")]
    active_count = len(active_users)
    st.caption(f"🔒 المستخدمون النشطون الآن: {active_count} / {MAX_ACTIVE_USERS}")

    if not st.session_state.logged_in:
        if st.button("تسجيل الدخول"):
            # تحميل المستخدمين من جديد
            current_users = load_users()
            
            if username_input in current_users and current_users[username_input]["password"] == password:
                if username_input == "admin":
                    pass
                elif username_input in active_users:
                    st.warning("⚠ هذا المستخدم مسجل دخول بالفعل.")
                    return False
                elif active_count >= MAX_ACTIVE_USERS:
                    st.error("🚫 الحد الأقصى للمستخدمين المتصلين حالياً.")
                    return False
                
                state[username_input] = {"active": True, "login_time": datetime.now().isoformat()}
                save_state(state)
                
                st.session_state.logged_in = True
                st.session_state.username = username_input
                st.session_state.user_role = current_users[username_input].get("role", "viewer")
                st.session_state.user_permissions = current_users[username_input].get("permissions", ["view"])
                
                # تحميل بيانات المستخدم الإضافية
                st.session_state.user_full_name = current_users[username_input].get("full_name", "")
                st.session_state.user_email = current_users[username_input].get("email", "")
                st.session_state.user_department = current_users[username_input].get("department", "")
                
                st.success(f"✅ تم تسجيل الدخول: {username_input} ({st.session_state.user_role})")
                st.rerun()
            else:
                st.error("❌ كلمة المرور غير صحيحة.")
        return False
    else:
        username = st.session_state.username
        user_role = st.session_state.user_role
        st.success(f"✅ مسجل الدخول كـ: {username} ({user_role})")
        rem = remaining_time(state, username)
        if rem:
            mins, secs = divmod(int(rem.total_seconds()), 60)
            st.info(f"⏳ الوقت المتبقي: {mins:02d}:{secs:02d}")
        else:
            st.warning("⏰ انتهت الجلسة، سيتم تسجيل الخروج.")
            logout_action()
        if st.button("🚪 تسجيل الخروج"):
            logout_action()
        return True

# -------------------------------
# 🔄 طرق جلب الملف من GitHub
# -------------------------------
def fetch_from_github_requests():
    """تحميل بإستخدام رابط RAW (requests)"""
    try:
        response = requests.get(GITHUB_EXCEL_URL, stream=True, timeout=30)
        response.raise_for_status()
        with open(APP_CONFIG["LOCAL_FILE"], "wb") as f:
            shutil.copyfileobj(response.raw, f)
        # امسح الكاش
        try:
            st.cache_data.clear()
        except:
            pass
        return True
    except Exception as e:
        st.error(f"⚠ فشل التحديث من GitHub: {e}")
        return False

def fetch_from_github_api():
    """تحميل عبر GitHub API"""
    if not GITHUB_AVAILABLE:
        return fetch_from_github_requests()
    
    try:
        token = st.secrets.get("github", {}).get("token", None)
        if not token:
            return fetch_from_github_requests()
        
        g = Github(token)
        repo = g.get_repo(APP_CONFIG["REPO_NAME"])
        file_content = repo.get_contents(APP_CONFIG["FILE_PATH"], ref=APP_CONFIG["BRANCH"])
        content = b64decode(file_content.content)
        with open(APP_CONFIG["LOCAL_FILE"], "wb") as f:
            f.write(content)
        try:
            st.cache_data.clear()
        except:
            pass
        return True
    except Exception as e:
        st.error(f"⚠ فشل تحميل الملف من GitHub: {e}")
        return False

# -------------------------------
# 📂 تحميل الشيتات
# -------------------------------
@st.cache_data(show_spinner=False)
def load_all_sheets():
    """تحميل جميع الشيتات من ملف Excel"""
    if not os.path.exists(APP_CONFIG["LOCAL_FILE"]):
        return None
    
    try:
        # قراءة جميع الشيتات
        sheets = pd.read_excel(APP_CONFIG["LOCAL_FILE"], sheet_name=None)
        
        if not sheets:
            return None
        
        # تنظيف أسماء الأعمدة لكل شيت
        for name, df in sheets.items():
            df.columns = df.columns.astype(str).str.strip()
        
        return sheets
    except Exception as e:
        st.error(f"❌ خطأ في تحميل الملف: {e}")
        return None

# نسخة مع dtype=object لواجهة التحرير
@st.cache_data(show_spinner=False)
def load_sheets_for_edit():
    """تحميل جميع الشيتات للتحرير"""
    if not os.path.exists(APP_CONFIG["LOCAL_FILE"]):
        return None
    
    try:
        # قراءة جميع الشيتات مع dtype=object
        sheets = pd.read_excel(APP_CONFIG["LOCAL_FILE"], sheet_name=None, dtype=object)
        
        if not sheets:
            return None
        
        # تنظيف أسماء الأعمدة لكل شيت
        for name, df in sheets.items():
            df.columns = df.columns.astype(str).str.strip()
        
        return sheets
    except Exception as e:
        st.error(f"❌ خطأ في تحميل الملف للتحرير: {e}")
        return None

# -------------------------------
# 🔁 حفظ محلي + رفع على GitHub
# -------------------------------
def save_local_excel_and_push(sheets_dict, commit_message="Update from CMMS"):
    """حفظ تلقائي محلي والرفع إلى GitHub"""
    # احفظ محلياً
    try:
        with pd.ExcelWriter(APP_CONFIG["LOCAL_FILE"], engine="openpyxl") as writer:
            for name, sh in sheets_dict.items():
                try:
                    sh.to_excel(writer, sheet_name=name, index=False)
                except Exception:
                    sh.astype(object).to_excel(writer, sheet_name=name, index=False)
    except Exception as e:
        st.error(f"⚠ خطأ أثناء الحفظ المحلي: {e}")
        return None

    # امسح الكاش
    try:
        st.cache_data.clear()
    except:
        pass

    # حاول الرفع عبر PyGithub
    token = st.secrets.get("github", {}).get("token", None)
    if not token:
        st.warning("⚠ لم يتم العثور على GitHub token. سيتم الحفظ محلياً فقط.")
        return load_sheets_for_edit()

    if not GITHUB_AVAILABLE:
        st.warning("⚠ PyGithub غير متوفر. سيتم الحفظ محلياً فقط.")
        return load_sheets_for_edit()

    try:
        g = Github(token)
        repo = g.get_repo(APP_CONFIG["REPO_NAME"])
        with open(APP_CONFIG["LOCAL_FILE"], "rb") as f:
            content = f.read()

        try:
            contents = repo.get_contents(APP_CONFIG["FILE_PATH"], ref=APP_CONFIG["BRANCH"])
            result = repo.update_file(path=APP_CONFIG["FILE_PATH"], message=commit_message, content=content, sha=contents.sha, branch=APP_CONFIG["BRANCH"])
            st.success(f"✅ تم الحفظ والرفع إلى GitHub بنجاح: {commit_message}")
            return load_sheets_for_edit()
        except Exception as e:
            # حاول رفع كملف جديد
            try:
                result = repo.create_file(path=APP_CONFIG["FILE_PATH"], message=commit_message, content=content, branch=APP_CONFIG["BRANCH"])
                st.success(f"✅ تم إنشاء ملف جديد على GitHub: {commit_message}")
                return load_sheets_for_edit()
            except Exception as create_error:
                st.error(f"❌ فشل إنشاء ملف جديد على GitHub: {create_error}")
                return None

    except Exception as e:
        st.error(f"❌ فشل الرفع إلى GitHub: {e}")
        return None

def auto_save_to_github(sheets_dict, operation_description):
    """دالة الحفظ التلقائي"""
    username = st.session_state.get("username", "unknown")
    commit_message = f"{operation_description} by {username} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    # إضافة إشعار للإدارة إذا لم يكن المستخدم أدمن
    if st.session_state.get("user_role") != "admin":
        add_notification(
            username=username,
            action="تعديل بيانات",
            details=operation_description,
            target_sheet=operation_description
        )
    
    result = save_local_excel_and_push(sheets_dict, commit_message)
    if result is not None:
        st.success("✅ تم حفظ التغييرات تلقائياً في GitHub")
        return result
    else:
        st.error("❌ فشل الحفظ التلقائي")
        return sheets_dict

# -------------------------------
# 🧰 دوال مساعدة للمعالجة والنصوص
# -------------------------------
def normalize_name(s):
    """تطبيع النصوص للبحث"""
    if s is None: return ""
    s = str(s).replace("\n", "+")
    s = re.sub(r"[^0-9a-zA-Z\u0600-\u06FF\+\s_/.-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s

def split_needed_services(needed_service_str):
    """تقسيم سلسلة الخدمات المطلوبة"""
    if not isinstance(needed_service_str, str) or needed_service_str.strip() == "":
        return []
    parts = re.split(r"\+|,|\n|;", needed_service_str)
    return [p.strip() for p in parts if p.strip() != ""]

def get_user_permissions(user_role, user_permissions):
    """الحصول على صلاحيات المستخدم"""
    # إذا كان الدور admin، يعطى جميع الصلاحيات
    if user_role == "admin":
        return {
            "can_view": True,
            "can_edit": True,
            "can_manage_users": True,
            "can_see_tech_support": True,
            "can_export_data": True,
            "can_see_notifications": True,
            "can_add_machines": True,
            "can_delete_machines": True,
            "can_manage_machine_types": True
        }
    
    # إذا كان الدور editor
    elif user_role == "editor":
        return {
            "can_view": True,
            "can_edit": True,
            "can_manage_users": False,
            "can_see_tech_support": True,
            "can_export_data": False,
            "can_see_notifications": False,
            "can_add_machines": True,
            "can_delete_machines": False,
            "can_manage_machine_types": False
        }
    
    # إذا كان الدور viewer
    else:
        return {
            "can_view": "view" in user_permissions or "edit" in user_permissions or "all" in user_permissions,
            "can_edit": "edit" in user_permissions or "all" in user_permissions,
            "can_manage_users": False,
            "can_see_tech_support": APP_CONFIG["SHOW_TECH_SUPPORT_TO_ALL"],
            "can_export_data": False,
            "can_see_notifications": False,
            "can_add_machines": "add_machines" in user_permissions or "all" in user_permissions,
            "can_delete_machines": False,
            "can_manage_machine_types": False
        }

# -------------------------------
# 🔍 البحث في الماكينات
# -------------------------------
def search_machines_ui(all_sheets):
    """واجهة البحث في جميع الماكينات"""
    st.header("🔍 البحث في الماكينات")
    
    if not all_sheets:
        st.error("❌ لم يتم تحميل أي بيانات.")
        return
    
    # تهيئة معايير البحث
    if "search_params" not in st.session_state:
        st.session_state.search_params = {
            "search_text": "",
            "machine_type": "جميع الأنواع",
            "machine_id": "",
            "status": "جميع الحالات",
            "location": "",
            "date_from": "",
            "date_to": "",
            "advanced_search": False
        }
    
    # قسم البحث الأساسي
    with st.container():
        st.markdown("### 🔎 بحث سريع")
        
        col1, col2, col3 = st.columns([3, 2, 2])
        
        with col1:
            search_text = st.text_input(
                "ابحث في جميع الحقول:",
                value=st.session_state.search_params.get("search_text", ""),
                placeholder="أدخل أي نص للبحث...",
                key="search_text_input"
            )
        
        with col2:
            # أنواع الماكينات المتاحة
            machine_types = list(load_machine_types().keys())
            machine_type_names = {k: v.get("name", k) for k, v in load_machine_types().items()}
            all_types = ["جميع الأنواع"] + list(machine_type_names.values())
            
            selected_type_name = st.selectbox(
                "نوع الماكينة:",
                all_types,
                index=all_types.index(st.session_state.search_params.get("machine_type", "جميع الأنواع")),
                key="machine_type_select"
            )
        
        with col3:
            machine_id = st.text_input(
                "رقم الماكينة:",
                value=st.session_state.search_params.get("machine_id", ""),
                placeholder="رقم الماكينة...",
                key="machine_id_input"
            )
        
        # البحث المتقدم
        with st.expander("🔍 خيارات البحث المتقدم", expanded=st.session_state.search_params.get("advanced_search", False)):
            col_adv1, col_adv2, col_adv3 = st.columns(3)
            
            with col_adv1:
                status_options = ["جميع الحالات", "نشطة", "متوقفة", "تحت الصيانة", "معطلة"]
                status = st.selectbox(
                    "الحالة:",
                    status_options,
                    index=status_options.index(st.session_state.search_params.get("status", "جميع الحالات")),
                    key="status_select"
                )
            
            with col_adv2:
                location = st.text_input(
                    "الموقع:",
                    value=st.session_state.search_params.get("location", ""),
                    placeholder="الموقع...",
                    key="location_input"
                )
            
            with col_adv3:
                st.caption("نطاق التاريخ:")
                date_from = st.text_input(
                    "من:",
                    value=st.session_state.search_params.get("date_from", ""),
                    placeholder="YYYY-MM-DD",
                    key="date_from_input"
                )
                date_to = st.text_input(
                    "إلى:",
                    value=st.session_state.search_params.get("date_to", ""),
                    placeholder="YYYY-MM-DD",
                    key="date_to_input"
                )
        
        # أزرار البحث
        col_btn1, col_btn2, col_btn3 = st.columns([2, 1, 1])
        with col_btn1:
            search_clicked = st.button(
                "🔍 **بدء البحث**",
                type="primary",
                use_container_width=True,
                key="main_search_btn"
            )
        with col_btn2:
            if st.button("🗑 **مسح البحث**", use_container_width=True, key="clear_search"):
                st.session_state.search_params = {
                    "search_text": "",
                    "machine_type": "جميع الأنواع",
                    "machine_id": "",
                    "status": "جميع الحالات",
                    "location": "",
                    "date_from": "",
                    "date_to": "",
                    "advanced_search": False
                }
                st.rerun()
        with col_btn3:
            advanced_toggle = st.session_state.search_params.get("advanced_search", False)
            if st.button("⚙ **بحث متقدم**" if not advanced_toggle else "⚙ **إخفاء المتقدم**", 
                        use_container_width=True, key="toggle_advanced"):
                st.session_state.search_params["advanced_search"] = not advanced_toggle
                st.rerun()
    
    # تحديث معايير البحث
    st.session_state.search_params.update({
        "search_text": search_text,
        "machine_type": selected_type_name,
        "machine_id": machine_id,
        "status": status,
        "location": location,
        "date_from": date_from,
        "date_to": date_to
    })
    
    # معالجة البحث
    if search_clicked:
        # حفظ البحث في التاريخ
        add_to_search_history(st.session_state.search_params.copy())
        
        # عرض نتائج البحث
        search_results = perform_search(all_sheets, st.session_state.search_params)
        display_search_results(search_results, st.session_state.search_params)
    
    # عرض سجل البحث الأخير
    show_recent_searches()

def perform_search(all_sheets, search_params):
    """تنفيذ البحث في جميع الماكينات"""
    results = []
    machine_types = load_machine_types()
    
    # تحديد نوع الماكينة المطلوب
    target_type = None
    if search_params["machine_type"] != "جميع الأنواع":
        for type_id, type_info in machine_types.items():
            if type_info.get("name") == search_params["machine_type"]:
                target_type = type_id
                break
    
    # البحث في كل شيت
    for sheet_name, df in all_sheets.items():
        # تخطي إذا كان هناك نوع محدد ولا يتطابق
        if target_type and sheet_name != target_type:
            continue
        
        # الحصول على معلومات نوع الماكينة
        machine_type_info = machine_types.get(sheet_name, {})
        machine_type_name = machine_type_info.get("name", sheet_name)
        
        # البحث في كل صف
        for idx, row in df.iterrows():
            if matches_search_criteria(row, search_params, machine_type_info):
                result = {
                    "machine_type": sheet_name,
                    "machine_type_name": machine_type_name,
                    "row_index": idx,
                    "data": row.to_dict(),
                    "sheet_name": sheet_name
                }
                results.append(result)
    
    return results

def matches_search_criteria(row, search_params, machine_type_info):
    """التحقق من تطابق الصف مع معايير البحث"""
    # البحث النصي العام
    if search_params["search_text"]:
        search_text = search_params["search_text"].lower()
        text_match = False
        for value in row.values:
            if search_text in str(value).lower():
                text_match = True
                break
        if not text_match:
            return False
    
    # رقم الماكينة
    if search_params["machine_id"]:
        machine_id_found = False
        for col_name in row.index:
            if "machine_id" in col_name.lower() or "رقم" in col_name or "id" in col_name.lower():
                if search_params["machine_id"] in str(row[col_name]):
                    machine_id_found = True
                    break
        if not machine_id_found:
            return False
    
    # الحالة
    if search_params["status"] != "جميع الحالات":
        status_found = False
        for col_name in row.index:
            if "status" in col_name.lower() or "حالة" in col_name:
                if search_params["status"] == str(row[col_name]):
                    status_found = True
                    break
        if not status_found:
            return False
    
    # الموقع
    if search_params["location"]:
        location_found = False
        for col_name in row.index:
            if "location" in col_name.lower() or "موقع" in col_name:
                if search_params["location"].lower() in str(row[col_name]).lower():
                    location_found = True
                    break
        if not location_found:
            return False
    
    # التاريخ (إذا كان هناك حقل تاريخ)
    if search_params["date_from"] or search_params["date_to"]:
        date_fields = [col for col in row.index if "date" in col.lower() or "تاريخ" in col]
        if date_fields:
            # هذا يحتاج إلى تحسين لمعالجة التواريخ بشكل صحيح
            pass
    
    return True

def display_search_results(results, search_params):
    """عرض نتائج البحث"""
    if not results:
        st.warning("⚠ لم يتم العثور على نتائج تطابق معايير البحث.")
        return
    
    st.success(f"✅ تم العثور على {len(results)} نتيجة.")
    
    # تبويبات لعرض النتائج
    tabs = st.tabs(["📊 عرض جدولي", "📋 عرض تفصيلي", "📍 على الخريطة"])
    
    with tabs[0]:
        display_results_table(results)
    
    with tabs[1]:
        display_results_detailed(results)
    
    with tabs[2]:
        display_results_map(results)

def display_results_table(results):
    """عرض النتائج في جدول"""
    # تحويل النتائج إلى DataFrame
    table_data = []
    for result in results:
        row_data = result["data"].copy()
        row_data["نوع الماكينة"] = result["machine_type_name"]
        row_data["رقم التسجيل"] = result.get("row_index", "")
        table_data.append(row_data)
    
    if table_data:
        df = pd.DataFrame(table_data)
        st.dataframe(df, use_container_width=True, height=500)
        
        # خيارات التصدير
        if st.session_state.get("user_role") == "admin":
            export_options(df)

def display_results_detailed(results):
    """عرض النتائج بشكل تفصيلي"""
    for result in results:
        with st.expander(f"{result['machine_type_name']} - {get_machine_id(result['data'])}", expanded=False):
            display_machine_details(result)

def display_results_map(results):
    """عرض النتائج على خريطة (إن أمكن)"""
    st.info("🗺️ ميزة الخريطة تتطلب إضافة حقول إحداثيات (latitude, longitude) للماكينات.")
    
    # محاولة استخراج المواقع
    locations = []
    for result in results:
        machine_data = result["data"]
        machine_id = get_machine_id(machine_data)
        machine_name = machine_data.get("machine_name", f"ماكينة {machine_id}")
        
        # البحث عن موقع
        location = None
        for key in machine_data.keys():
            if "location" in key.lower() or "موقع" in key:
                location = machine_data[key]
                break
        
        if location:
            locations.append({
                "name": machine_name,
                "location": location,
                "type": result["machine_type_name"],
                "status": machine_data.get("status", "غير محدد")
            })
    
    if locations:
        st.markdown("### 📍 المواقع:")
        for loc in locations:
            st.markdown(f"- **{loc['name']}**: {loc['location']} ({loc['type']}) - {loc['status']}")
    else:
        st.warning("⚠ لا توجد معلومات مواقع في البيانات.")

def get_machine_id(machine_data):
    """استخراج رقم الماكينة من البيانات"""
    for key in machine_data.keys():
        if "machine_id" in key.lower() or "رقم" in key or "id" in key.lower():
            return str(machine_data[key])
    return "غير معروف"

def display_machine_details(result):
    """عرض تفاصيل الماكينة"""
    machine_data = result["data"]
    machine_type_info = load_machine_types().get(result["machine_type"], {})
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("#### 📋 المعلومات الأساسية")
        for field_id, field_info in machine_type_info.get("fields", {}).items():
            if field_id in machine_data:
                value = machine_data[field_id]
                if value and str(value).strip():
                    field_label = field_info.get("label", field_id)
                    st.markdown(f"**{field_label}:** {value}")
        
        # عرض الصور إذا كانت موجودة
        if "images" in machine_data and machine_data["images"]:
            display_images(machine_data["images"], "صور الماكينة")
    
    with col2:
        st.markdown("#### ⚡ الإجراءات")
        
        # زر التعديل
        permissions = get_user_permissions(
            st.session_state.get("user_role", "viewer"),
            st.session_state.get("user_permissions", ["view"])
        )
        
        if permissions["can_edit"]:
            if st.button("✏️ تعديل", key=f"edit_{result['machine_type']}_{result['row_index']}"):
                st.session_state["edit_machine"] = {
                    "type": result["machine_type"],
                    "row_index": result["row_index"],
                    "data": machine_data
                }
                st.rerun()
        
        # زر المفضلة
        machine_id = get_machine_id(machine_data)
        favorite = is_favorite(result["machine_type"], machine_id)
        
        if st.button("⭐ إضافة للمفضلة" if not favorite else "★ إزالة من المفضلة", 
                    key=f"fav_{result['machine_type']}_{machine_id}"):
            success, message = toggle_favorite(result["machine_type"], machine_id)
            if success:
                st.success(message)
                st.rerun()
            else:
                st.warning(message)
        
        # زر النسخ
        if st.button("📋 نسخ المعلومات", key=f"copy_{result['machine_type']}_{result['row_index']}"):
            info_text = f"ماكينة {machine_type_info.get('name', result['machine_type'])}\n"
            for key, value in machine_data.items():
                if value and str(value).strip():
                    info_text += f"{key}: {value}\n"
            
            st.code(info_text, language="text")
            st.success("✅ تم نسخ المعلومات")

def export_options(df):
    """خيارات تصدير البيانات"""
    st.markdown("### 💾 خيارات التصدير")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📊 تصدير Excel", use_container_width=True):
            buffer = io.BytesIO()
            df.to_excel(buffer, index=False, engine="openpyxl")
            st.download_button(
                label="📥 تنزيل Excel",
                data=buffer.getvalue(),
                file_name=f"نتائج_البحث_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
    
    with col2:
        if st.button("📄 تصدير CSV", use_container_width=True):
            buffer = io.BytesIO()
            df.to_csv(buffer, index=False, encoding="utf-8-sig")
            st.download_button(
                label="📥 تنزيل CSV",
                data=buffer.getvalue(),
                file_name=f"نتائج_البحث_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
    
    with col3:
        if st.button("📋 نسخ كجدول", use_container_width=True):
            df_str = df.to_string(index=False)
            st.code(df_str, language="text")
            st.success("✅ تم نسخ البيانات")

def show_recent_searches():
    """عرض عمليات البحث الأخيرة"""
    history = load_search_history()
    if history:
        st.markdown("---")
        st.markdown("### 📜 عمليات البحث الأخيرة")
        
        # عرض آخر 5 عمليات بحث
        for i, search in enumerate(history[:5]):
            with st.expander(f"بحث {i+1}: {search.get('search_text', 'بدون نص')}", expanded=False):
                st.markdown(f"**المستخدم:** {search.get('user', 'غير معروف')}")
                st.markdown(f"**الوقت:** {datetime.fromisoformat(search['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}")
                st.markdown(f"**نوع الماكينة:** {search.get('machine_type', 'جميع الأنواع')}")
                
                # زر إعادة استخدام البحث
                if st.button("🔄 استخدام هذا البحث", key=f"reuse_search_{i}"):
                    st.session_state.search_params = search
                    st.rerun()

# -------------------------------
# 🛠 إدارة الماكينات
# -------------------------------
def manage_machines_ui(sheets_edit):
    """واجهة إدارة الماكينات"""
    st.header("🛠 إدارة الماكينات")
    
    if not sheets_edit:
        st.error("❌ لم يتم تحميل أي بيانات.")
        return
    
    machine_types = load_machine_types()
    
    # تبويبات الإدارة
    tabs = st.tabs(["➕ إضافة ماكينة جديدة", "✏️ تعديل ماكينة", "🗑️ حذف ماكينة", "📊 عرض الكل"])
    
    with tabs[0]:
        add_machine_ui(machine_types, sheets_edit)
    
    with tabs[1]:
        edit_machine_ui(machine_types, sheets_edit)
    
    with tabs[2]:
        delete_machine_ui(machine_types, sheets_edit)
    
    with tabs[3]:
        view_all_machines_ui(machine_types, sheets_edit)

def add_machine_ui(machine_types, sheets_edit):
    """إضافة ماكينة جديدة"""
    st.markdown("### ➕ إضافة ماكينة جديدة")
    
    if not machine_types:
        st.warning("⚠ لا توجد أنواع مكن محددة. الرجاء إضافة أنواع الماكينات أولاً.")
        return
    
    # اختيار نوع الماكينة
    type_options = {k: v.get("name", k) for k, v in machine_types.items()}
    selected_type_name = st.selectbox(
        "اختر نوع الماكينة:",
        list(type_options.values()),
        key="add_machine_type_select"
    )
    
    # العثور على نوع الماكينة المحدد
    selected_type = None
    for type_id, type_info in machine_types.items():
        if type_info.get("name") == selected_type_name:
            selected_type = type_id
            break
    
    if not selected_type:
        st.error("❌ نوع الماكينة غير موجود.")
        return
    
    # عرض حقول الإدخال
    type_info = machine_types[selected_type]
    fields = type_info.get("fields", {})
    
    st.markdown(f"#### 📝 إدخال بيانات ماكينة {type_info.get('name')}")
    
    machine_data = {}
    
    # تنظيم الحقول في أعمدة
    required_fields = []
    optional_fields = []
    
    for field_id, field_info in fields.items():
        if field_info.get("required", False):
            required_fields.append((field_id, field_info))
        else:
            optional_fields.append((field_id, field_info))
    
    # عرض الحقول المطلوبة
    st.markdown("##### 🔸 الحقول المطلوبة:")
    cols = st.columns(2)
    col_idx = 0
    
    for field_id, field_info in required_fields:
        with cols[col_idx % 2]:
            value = get_field_input(field_id, field_info)
            if value is not None:
                machine_data[field_id] = value
        col_idx += 1
    
    # عرض الحقول الاختيارية
    if optional_fields:
        with st.expander("🔹 الحقول الاختيارية", expanded=True):
            cols = st.columns(2)
            col_idx = 0
            
            for field_id, field_info in optional_fields:
                with cols[col_idx % 2]:
                    value = get_field_input(field_id, field_info, required=False)
                    if value is not None:
                        machine_data[field_id] = value
                col_idx += 1
    
    # زر الإضافة
    if st.button("💾 إضافة الماكينة", type="primary", key="add_machine_btn"):
        # التحقق من الحقول المطلوبة
        missing_fields = []
        for field_id, field_info in required_fields:
            if field_id not in machine_data or not str(machine_data[field_id]).strip():
                missing_fields.append(field_info.get("label", field_id))
        
        if missing_fields:
            st.error(f"❌ الحقول التالية مطلوبة: {', '.join(missing_fields)}")
            return
        
        # إضافة الماكينة إلى DataFrame
        if selected_type not in sheets_edit:
            # إنشاء شيت جديد إذا لم يكن موجوداً
            sheets_edit[selected_type] = pd.DataFrame(columns=list(fields.keys()))
        
        df = sheets_edit[selected_type]
        new_row = pd.DataFrame([machine_data])
        df = pd.concat([df, new_row], ignore_index=True)
        sheets_edit[selected_type] = df.astype(object)
        
        # حفظ التغييرات
        machine_id = machine_data.get("machine_id", "غير معروف")
        commit_message = f"إضافة ماكينة {machine_id} من نوع {type_info.get('name')}"
        
        new_sheets = auto_save_to_github(sheets_edit, commit_message)
        if new_sheets is not None:
            sheets_edit = new_sheets
            st.success(f"✅ تم إضافة الماكينة {machine_id} بنجاح!")
            
            # إضافة إشعار
            add_notification(
                username=st.session_state.get("username", "غير معروف"),
                action="إضافة ماكينة",
                details=f"تمت إضافة ماكينة {machine_id} من نوع {type_info.get('name')}",
                target_sheet=selected_type,
                machine_id=machine_id
            )
            
            # عرض ملخص
            with st.expander("📋 ملخص الماكينة المضافة", expanded=True):
                for field_id, value in machine_data.items():
                    field_label = fields.get(field_id, {}).get("label", field_id)
                    st.markdown(f"**{field_label}:** {value}")
            
            # مسح الحقول
            st.rerun()
        else:
            st.error("❌ فشل إضافة الماكينة.")

def get_field_input(field_id, field_info, required=True):
    """إنشاء عنصر إدخال للحقل"""
    field_label = field_info.get("label", field_id)
    field_type = field_info.get("type", "text")
    options = field_info.get("options", [])
    
    if field_type == "text":
        return st.text_input(field_label, key=f"input_{field_id}", disabled=not required)
    
    elif field_type == "textarea":
        return st.text_area(field_label, key=f"textarea_{field_id}", disabled=not required)
    
    elif field_type == "number":
        return st.number_input(field_label, key=f"number_{field_id}", disabled=not required)
    
    elif field_type == "date":
        date_str = st.text_input(field_label, placeholder="YYYY-MM-DD", key=f"date_{field_id}", disabled=not required)
        return date_str
    
    elif field_type == "select":
        return st.selectbox(field_label, options, key=f"select_{field_id}", disabled=not required)
    
    elif field_type == "images":
        st.markdown(f"**{field_label}:**")
        uploaded_files = st.file_uploader(
            "اختر الصور:",
            type=APP_CONFIG["ALLOWED_IMAGE_TYPES"],
            accept_multiple_files=True,
            key=f"upload_{field_id}"
        )
        
        if uploaded_files:
            saved_files = save_uploaded_images(uploaded_files)
            if saved_files:
                return ", ".join(saved_files)
        
        return ""
    
    return ""

def edit_machine_ui(machine_types, sheets_edit):
    """تعديل ماكينة موجودة"""
    st.markdown("### ✏️ تعديل ماكينة")
    
    if not sheets_edit:
        st.warning("⚠ لا توجد بيانات للتحرير.")
        return
    
    # اختيار نوع الماكينة
    available_types = [k for k in machine_types.keys() if k in sheets_edit and not sheets_edit[k].empty]
    
    if not available_types:
        st.warning("⚠ لا توجد ماكينات مسجلة.")
        return
    
    type_options = {k: machine_types[k].get("name", k) for k in available_types}
    selected_type_name = st.selectbox(
        "اختر نوع الماكينة:",
        list(type_options.values()),
        key="edit_machine_type_select"
    )
    
    # العثور على نوع الماكينة المحدد
    selected_type = None
    for type_id, type_info in machine_types.items():
        if type_info.get("name") == selected_type_name:
            selected_type = type_id
            break
    
    if not selected_type or selected_type not in sheets_edit:
        st.error("❌ نوع الماكينة غير موجود أو لا يحتوي على بيانات.")
        return
    
    # اختيار الماكينة
    df = sheets_edit[selected_type]
    machine_options = []
    
    for idx, row in df.iterrows():
        machine_id = get_machine_id(row.to_dict())
        machine_name = row.get("machine_name", f"ماكينة {machine_id}")
        machine_options.append((idx, f"{machine_id} - {machine_name}"))
    
    if not machine_options:
        st.warning("⚠ لا توجد ماكينات من هذا النوع.")
        return
    
    selected_option = st.selectbox(
        "اختر الماكينة:",
        [opt[1] for opt in machine_options],
        key="select_machine_to_edit"
    )
    
    # العثور على الصف المحدد
    selected_idx = None
    for idx, label in machine_options:
        if label == selected_option:
            selected_idx = idx
            break
    
    if selected_idx is None:
        st.error("❌ الماكينة غير موجودة.")
        return
    
    # تحميل بيانات الماكينة
    machine_data = df.iloc[selected_idx].to_dict()
    type_info = machine_types[selected_type]
    fields = type_info.get("fields", {})
    
    st.markdown(f"#### ✏️ تعديل بيانات الماكينة {get_machine_id(machine_data)}")
    
    # عرض حقول التعديل
    updated_data = {}
    
    cols = st.columns(2)
    col_idx = 0
    
    for field_id, field_info in fields.items():
        with cols[col_idx % 2]:
            current_value = machine_data.get(field_id, "")
            field_label = field_info.get("label", field_id)
            field_type = field_info.get("type", "text")
            options = field_info.get("options", [])
            
            if field_type == "text":
                new_value = st.text_input(field_label, value=str(current_value), key=f"edit_{field_id}_{selected_idx}")
            
            elif field_type == "textarea":
                new_value = st.text_area(field_label, value=str(current_value), key=f"edit_textarea_{field_id}_{selected_idx}")
            
            elif field_type == "number":
                try:
                    num_value = float(current_value) if current_value else 0
                except:
                    num_value = 0
                new_value = st.number_input(field_label, value=num_value, key=f"edit_number_{field_id}_{selected_idx}")
            
            elif field_type == "date":
                new_value = st.text_input(field_label, value=str(current_value), key=f"edit_date_{field_id}_{selected_idx}")
            
            elif field_type == "select":
                default_idx = 0
                if current_value in options:
                    default_idx = options.index(current_value)
                new_value = st.selectbox(field_label, options, index=default_idx, key=f"edit_select_{field_id}_{selected_idx}")
            
            elif field_type == "images":
                st.markdown(f"**{field_label}:**")
                
                # عرض الصور الحالية
                current_images = []
                if current_value:
                    current_images = [img.strip() for img in str(current_value).split(",") if img.strip()]
                
                if current_images:
                    display_images(current_images, "الصور الحالية")
                
                # رفع صور جديدة
                uploaded_files = st.file_uploader(
                    "إضافة صور جديدة:",
                    type=APP_CONFIG["ALLOWED_IMAGE_TYPES"],
                    accept_multiple_files=True,
                    key=f"edit_upload_{field_id}_{selected_idx}"
                )
                
                all_images = current_images.copy()
                
                if uploaded_files:
                    saved_files = save_uploaded_images(uploaded_files)
                    if saved_files:
                        all_images.extend(saved_files)
                
                new_value = ", ".join(all_images) if all_images else ""
            
            else:
                new_value = st.text_input(field_label, value=str(current_value), key=f"edit_other_{field_id}_{selected_idx}")
            
            updated_data[field_id] = new_value
        
        col_idx += 1
    
    # أزرار التعديل
    col_btn1, col_btn2 = st.columns(2)
    
    with col_btn1:
        if st.button("💾 حفظ التعديلات", type="primary", key="save_edit_btn"):
            # تحديث البيانات
            for field_id, new_value in updated_data.items():
                df.at[selected_idx, field_id] = new_value
            
            sheets_edit[selected_type] = df.astype(object)
            
            # حفظ التغييرات
            machine_id = get_machine_id(updated_data)
            commit_message = f"تعديل ماكينة {machine_id} من نوع {type_info.get('name')}"
            
            new_sheets = auto_save_to_github(sheets_edit, commit_message)
            if new_sheets is not None:
                sheets_edit = new_sheets
                st.success(f"✅ تم تحديث الماكينة {machine_id} بنجاح!")
                
                # إضافة إشعار
                add_notification(
                    username=st.session_state.get("username", "غير معروف"),
                    action="تعديل ماكينة",
                    details=f"تم تعديل ماكينة {machine_id} من نوع {type_info.get('name')}",
                    target_sheet=selected_type,
                    machine_id=machine_id
                )
                
                st.rerun()
            else:
                st.error("❌ فشل حفظ التعديلات.")
    
    with col_btn2:
        if st.button("↩️ التراجع", key="cancel_edit_btn"):
            st.rerun()

def delete_machine_ui(machine_types, sheets_edit):
    """حذف ماكينة"""
    st.markdown("### 🗑️ حذف ماكينة")
    
    permissions = get_user_permissions(
        st.session_state.get("user_role", "viewer"),
        st.session_state.get("user_permissions", ["view"])
    )
    
    if not permissions["can_delete_machines"]:
        st.error("❌ ليس لديك صلاحية حذف الماكينات.")
        return
    
    if not sheets_edit:
        st.warning("⚠ لا توجد بيانات.")
        return
    
    # اختيار نوع الماكينة
    available_types = [k for k in machine_types.keys() if k in sheets_edit and not sheets_edit[k].empty]
    
    if not available_types:
        st.warning("⚠ لا توجد ماكينات مسجلة.")
        return
    
    type_options = {k: machine_types[k].get("name", k) for k in available_types}
    selected_type_name = st.selectbox(
        "اختر نوع الماكينة:",
        list(type_options.values()),
        key="delete_machine_type_select"
    )
    
    # العثور على نوع الماكينة المحدد
    selected_type = None
    for type_id, type_info in machine_types.items():
        if type_info.get("name") == selected_type_name:
            selected_type = type_id
            break
    
    if not selected_type or selected_type not in sheets_edit:
        st.error("❌ نوع الماكينة غير موجود.")
        return
    
    # اختيار الماكينة
    df = sheets_edit[selected_type]
    machine_options = []
    
    for idx, row in df.iterrows():
        machine_id = get_machine_id(row.to_dict())
        machine_name = row.get("machine_name", f"ماكينة {machine_id}")
        machine_options.append((idx, f"{machine_id} - {machine_name}"))
    
    if not machine_options:
        st.warning("⚠ لا توجد ماكينات من هذا النوع.")
        return
    
    selected_option = st.selectbox(
        "اختر الماكينة للحذف:",
        [opt[1] for opt in machine_options],
        key="select_machine_to_delete"
    )
    
    # العثور على الصف المحدد
    selected_idx = None
    machine_data = None
    
    for idx, label in machine_options:
        if label == selected_option:
            selected_idx = idx
            machine_data = df.iloc[idx].to_dict()
            break
    
    if selected_idx is None or machine_data is None:
        st.error("❌ الماكينة غير موجودة.")
        return
    
    # عرض بيانات الماكينة
    st.markdown("#### 📋 بيانات الماكينة المحددة:")
    
    type_info = machine_types[selected_type]
    for field_id, field_info in type_info.get("fields", {}).items():
        if field_id in machine_data:
            value = machine_data[field_id]
            if value and str(value).strip():
                field_label = field_info.get("label", field_id)
                st.markdown(f"**{field_label}:** {value}")
    
    # تأكيد الحذف
    machine_id = get_machine_id(machine_data)
    confirm = st.checkbox(f"أؤكد أنني أريد حذف الماكينة {machine_id}", key="confirm_delete")
    
    if confirm:
        if st.button("🗑️ حذف نهائياً", type="primary", key="delete_machine_btn"):
            # حذف الصور المرتبطة
            if "images" in machine_data and machine_data["images"]:
                images = machine_data["images"].split(",")
                for img in images:
                    delete_image_file(img.strip())
            
            # حذف الصف
            df = df.drop(selected_idx).reset_index(drop=True)
            sheets_edit[selected_type] = df.astype(object)
            
            # حفظ التغييرات
            commit_message = f"حذف ماكينة {machine_id} من نوع {type_info.get('name')}"
            
            new_sheets = auto_save_to_github(sheets_edit, commit_message)
            if new_sheets is not None:
                sheets_edit = new_sheets
                st.success(f"✅ تم حذف الماكينة {machine_id} بنجاح!")
                
                # إضافة إشعار
                add_notification(
                    username=st.session_state.get("username", "غير معروف"),
                    action="حذف ماكينة",
                    details=f"تم حذف ماكينة {machine_id} من نوع {type_info.get('name')}",
                    target_sheet=selected_type,
                    machine_id=machine_id
                )
                
                st.rerun()
            else:
                st.error("❌ فشل حذف الماكينة.")

def view_all_machines_ui(machine_types, sheets_edit):
    """عرض جميع الماكينات"""
    st.markdown("### 📊 جميع الماكينات")
    
    if not sheets_edit:
        st.warning("⚠ لا توجد بيانات.")
        return
    
    # حساب الإحصائيات
    total_machines = 0
    stats_by_type = {}
    
    for type_id, df in sheets_edit.items():
        if not df.empty:
            type_name = machine_types.get(type_id, {}).get("name", type_id)
            count = len(df)
            total_machines += count
            stats_by_type[type_name] = count
    
    # عرض الإحصائيات
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("🔢 إجمالي الماكينات", total_machines)
    
    with col2:
        st.metric("📁 عدد الأنواع", len(stats_by_type))
    
    with col3:
        # حساب الماكينات النشطة
        active_count = 0
        for type_id, df in sheets_edit.items():
            if "status" in df.columns:
                active_count += df[df["status"] == "نشطة"].shape[0]
        st.metric("✅ ماكينات نشطة", active_count)
    
    with col4:
        # حساب الماكينات تحت الصيانة
        maintenance_count = 0
        for type_id, df in sheets_edit.items():
            if "status" in df.columns:
                maintenance_count += df[df["status"] == "تحت الصيانة"].shape[0]
        st.metric("🔧 تحت الصيانة", maintenance_count)
    
    # عرض حسب النوع
    for type_id, df in sheets_edit.items():
        if not df.empty:
            type_name = machine_types.get(type_id, {}).get("name", type_id)
            
            with st.expander(f"{type_name} ({len(df)} ماكينة)", expanded=False):
                # عرض الأعمدة الافتراضية إن وجدت
                default_columns = machine_types.get(type_id, {}).get("default_columns", [])
                if default_columns:
                    display_columns = [col for col in default_columns if col in df.columns]
                    if not display_columns:
                        display_columns = df.columns[:6]  # أول 6 أعمدة
                else:
                    display_columns = df.columns[:6]
                
                st.dataframe(df[display_columns], use_container_width=True)

# -------------------------------
# ➕ إضافة نوع مكن جديد
# -------------------------------
def add_machine_type_ui():
    """واجهة إضافة نوع مكن جديد"""
    st.header("➕ إضافة نوع مكن جديد")
    
    permissions = get_user_permissions(
        st.session_state.get("user_role", "viewer"),
        st.session_state.get("user_permissions", ["view"])
    )
    
    if not permissions["can_manage_machine_types"]:
        st.error("❌ ليس لديك صلاحية إدارة أنواع الماكينات.")
        return
    
    machine_types = load_machine_types()
    
    # معلومات النوع الأساسية
    st.markdown("### 📝 معلومات النوع الأساسية")
    
    col1, col2 = st.columns(2)
    
    with col1:
        machine_type_id = st.text_input(
            "معرف النوع (ID):",
            placeholder="مثال: cnc_machine",
            help="يجب أن يكون معرف فريد باللغة الإنجليزية بدون مسافات"
        )
        
        machine_type_name = st.text_input(
            "اسم النوع (عربي):",
            placeholder="مثال: ماكينة CNC",
            help="اسم النوع باللغة العربية"
        )
    
    with col2:
        category = st.selectbox(
            "الفئة:",
            APP_CONFIG["MACHINE_CATEGORIES"],
            help="اختر الفئة المناسبة"
        )
        
        description = st.text_area(
            "الوصف:",
            placeholder="وصف مختصر لنوع الماكينة...",
            help="وصف عام للنوع ووظيفته"
        )
    
    # تعريف الحقول
    st.markdown("### 🏗️ تعريف الحقول")
    st.info("حدد الحقول التي ستكون متاحة لهذا النوع من الماكينات.")
    
    # قائمة الحقول الحالية
    fields = {}
    
    # حقل إجباري: رقم الماكينة
    st.markdown("##### 🔸 الحقول الإجبارية:")
    
    col_id1, col_id2, col_id3 = st.columns([3, 2, 1])
    with col_id1:
        st.markdown("**رقم الماكينة** (إجباري)")
    with col_id2:
        st.markdown("نوع: نص")
    with col_id3:
        st.markdown("✅ مطلوب")
    
    fields["machine_id"] = {
        "type": "text",
        "required": True,
        "label": "رقم الماكينة"
    }
    
    # حقل إجباري: اسم الماكينة
    col_name1, col_name2, col_name3 = st.columns([3, 2, 1])
    with col_name1:
        st.markdown("**اسم الماكينة** (إجباري)")
    with col_name2:
        st.markdown("نوع: نص")
    with col_name3:
        st.markdown("✅ مطلوب")
    
    fields["machine_name"] = {
        "type": "text",
        "required": True,
        "label": "اسم الماكينة"
    }
    
    # حقل إجباري: الحالة
    col_status1, col_status2, col_status3 = st.columns([3, 2, 1])
    with col_status1:
        st.markdown("**الحالة** (إجباري)")
    with col_status2:
        st.markdown("نوع: قائمة")
    with col_status3:
        st.markdown("✅ مطلوب")
    
    fields["status"] = {
        "type": "select",
        "required": True,
        "label": "الحالة",
        "options": ["نشطة", "متوقفة", "تحت الصيانة", "معطلة"]
    }
    
    # الحقول الاختيارية
    st.markdown("##### 🔹 الحقول الاختيارية:")
    
    if "optional_fields" not in st.session_state:
        st.session_state.optional_fields = []
    
    # إضافة حقول جديدة
    with st.expander("➕ إضافة حقل اختياري", expanded=False):
        new_field_name = st.text_input("اسم الحقل (عربي):", placeholder="مثال: الموديل", key="new_field_name")
        new_field_id = st.text_input("معرف الحقل (إنجليزي):", placeholder="مثال: model", key="new_field_id")
        
        col_type1, col_type2 = st.columns(2)
        with col_type1:
            new_field_type = st.selectbox(
                "نوع الحقل:",
                ["text", "textarea", "number", "date", "select", "images"],
                key="new_field_type"
            )
        with col_type2:
            new_field_required = st.checkbox("حقل مطلوب", key="new_field_required")
        
        # خيارات القائمة المختارة
        if new_field_type == "select":
            new_field_options = st.text_area(
                "خيارات القائمة (سطر لكل خيار):",
                placeholder="نشطة\nمتوقفة\nتحت الصيانة",
                key="new_field_options"
            )
        
        if st.button("➕ إضافة هذا الحقل", key="add_field_btn"):
            if new_field_name and new_field_id:
                field_data = {
                    "type": new_field_type,
                    "required": new_field_required,
                    "label": new_field_name
                }
                
                if new_field_type == "select" and new_field_options:
                    field_data["options"] = [opt.strip() for opt in new_field_options.split("\n") if opt.strip()]
                
                fields[new_field_id] = field_data
                st.session_state.optional_fields.append((new_field_id, field_data))
                st.success(f"✅ تم إضافة حقل {new_field_name}")
                st.rerun()
    
    # عرض الحقول المضافة
    if st.session_state.optional_fields:
        st.markdown("**الحقول المضافة:**")
        for field_id, field_data in st.session_state.optional_fields:
            col1, col2, col3 = st.columns([3, 2, 1])
            with col1:
                st.markdown(f"**{field_data['label']}**")
            with col2:
                st.markdown(f"نوع: {field_data['type']}")
            with col3:
                if st.button("🗑️", key=f"remove_{field_id}"):
                    st.session_state.optional_fields = [f for f in st.session_state.optional_fields if f[0] != field_id]
                    st.rerun()
    
    # تحديد الأعمدة الافتراضية للعرض
    st.markdown("### 👁️ الأعمدة الافتراضية للعرض")
    st.info("اختر الأعمدة التي تظهر افتراضياً عند عرض هذا النوع من الماكينات.")
    
    available_fields = list(fields.keys())
    default_columns = st.multiselect(
        "الأعمدة الافتراضية:",
        available_fields,
        default=["machine_id", "machine_name", "status"],
        help="اختر الأعمدة التي تظهر في الجداول افتراضياً"
    )
    
    # زر إنشاء النوع
    if st.button("💾 إنشاء نوع الماكينة", type="primary", key="create_machine_type_btn"):
        if not machine_type_id or not machine_type_name:
            st.error("❌ المعرف واسم النوع مطلوبان.")
            return
        
        if machine_type_id in machine_types:
            st.error("❌ معرف النوع موجود بالفعل.")
            return
        
        # إضافة الحقول الاختيارية
        for field_id, field_data in st.session_state.optional_fields:
            fields[field_id] = field_data
        
        # إنشاء بيانات النوع
        machine_type_data = {
            "name": machine_type_name,
            "category": category,
            "description": description,
            "fields": fields,
            "default_columns": default_columns,
            "created_at": datetime.now().isoformat(),
            "created_by": st.session_state.get("username", "system")
        }
        
        # حفظ النوع
        success, message = add_machine_type(machine_type_id, machine_type_data)
        if success:
            st.success(f"✅ {message}")
            
            # إضافة إشعار
            add_notification(
                username=st.session_state.get("username", "غير معروف"),
                action="إضافة نوع مكن",
                details=f"تمت إضافة نوع مكن جديد: {machine_type_name}",
                machine_id=machine_type_id
            )
            
            # مسح الحقول
            if "optional_fields" in st.session_state:
                del st.session_state.optional_fields
            
            st.rerun()
        else:
            st.error(f"❌ {message}")

# -------------------------------
# 👥 إدارة المستخدمين
# -------------------------------
def manage_users_ui():
    """واجهة إدارة المستخدمين"""
    st.header("👥 إدارة المستخدمين")
    
    permissions = get_user_permissions(
        st.session_state.get("user_role", "viewer"),
        st.session_state.get("user_permissions", ["view"])
    )
    
    if not permissions["can_manage_users"]:
        st.error("❌ ليس لديك صلاحية إدارة المستخدمين.")
        return
    
    users = load_users()
    
    # عرض المستخدمين الحاليين
    st.markdown("### 📋 المستخدمون الحاليون")
    
    if users:
        users_data = []
        for username, user_info in users.items():
            users_data.append({
                "اسم المستخدم": username,
                "الاسم الكامل": user_info.get("full_name", ""),
                "الدور": user_info.get("role", "viewer"),
                "القسم": user_info.get("department", ""),
                "البريد الإلكتروني": user_info.get("email", ""),
                "تاريخ الإنشاء": user_info.get("created_at", "غير معروف")
            })
        
        df = pd.DataFrame(users_data)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("ℹ️ لا توجد مستخدمين مسجلين.")
    
    # تبويبات إدارة المستخدمين
    tabs = st.tabs(["➕ إضافة مستخدم", "✏️ تعديل مستخدم", "🗑️ حذف مستخدم"])
    
    with tabs[0]:
        add_user_ui(users)
    
    with tabs[1]:
        edit_user_ui(users)
    
    with tabs[2]:
        delete_user_ui(users)

def add_user_ui(users):
    """إضافة مستخدم جديد"""
    st.markdown("#### ➕ إضافة مستخدم جديد")
    
    col1, col2 = st.columns(2)
    
    with col1:
        new_username = st.text_input("اسم المستخدم:", key="add_user_username")
        new_password = st.text_input("كلمة المرور:", type="password", key="add_user_password")
        confirm_password = st.text_input("تأكيد كلمة المرور:", type="password", key="add_user_confirm")
    
    with col2:
        full_name = st.text_input("الاسم الكامل:", key="add_user_fullname")
        email = st.text_input("البريد الإلكتروني:", key="add_user_email")
        department = st.text_input("القسم:", key="add_user_department")
    
    role = st.selectbox("الدور:", ["admin", "editor", "viewer"], key="add_user_role")
    
    # الصلاحيات
    st.markdown("##### 🔐 الصلاحيات:")
    
    if role == "admin":
        st.info("👑 المسؤول لديه جميع الصلاحيات تلقائياً.")
        permissions = ["all"]
    elif role == "editor":
        permissions = ["view", "edit", "add_machines"]
    else:
        permissions = ["view"]
    
    # عرض الصلاحيات
    st.markdown(f"الصلاحيات الممنوحة: {', '.join(permissions)}")
    
    if st.button("💾 إضافة المستخدم", type="primary", key="add_user_btn"):
        if not new_username or not new_password:
            st.error("❌ اسم المستخدم وكلمة المرور مطلوبان.")
            return
        
        if new_password != confirm_password:
            st.error("❌ كلمة المرور غير مطابقة.")
            return
        
        if len(new_password) < 6:
            st.warning("⚠ كلمة المرور يجب أن تكون 6 أحرف على الأقل.")
            return
        
        if new_username in users:
            st.error("❌ اسم المستخدم موجود بالفعل.")
            return
        
        # إضافة المستخدم
        users[new_username] = {
            "password": new_password,
            "role": role,
            "permissions": permissions,
            "full_name": full_name,
            "email": email,
            "department": department,
            "created_at": datetime.now().isoformat(),
            "created_by": st.session_state.get("username", "system")
        }
        
        if save_users(users):
            st.success(f"✅ تم إضافة المستخدم {new_username} بنجاح!")
            st.rerun()
        else:
            st.error("❌ حدث خطأ أثناء حفظ المستخدم.")

def edit_user_ui(users):
    """تعديل مستخدم"""
    st.markdown("#### ✏️ تعديل مستخدم")
    
    if not users:
        st.warning("⚠ لا توجد مستخدمين لتعديلهم.")
        return
    
    user_list = list(users.keys())
    if st.session_state.get("username") != "admin":
        user_list = [u for u in user_list if u != "admin"]
    
    selected_user = st.selectbox("اختر المستخدم:", user_list, key="edit_user_select")
    
    if selected_user:
        user_info = users[selected_user]
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.info(f"**المستخدم:** {selected_user}")
            st.info(f"**الدور الحالي:** {user_info.get('role', 'viewer')}")
            
            # تغيير كلمة المرور
            st.markdown("##### 🔐 تغيير كلمة المرور")
            new_password = st.text_input("كلمة المرور الجديدة:", type="password", key="edit_user_password")
            confirm_password = st.text_input("تأكيد كلمة المرور:", type="password", key="edit_user_confirm")
        
        with col2:
            # معلومات المستخدم
            full_name = st.text_input("الاسم الكامل:", value=user_info.get("full_name", ""), key="edit_user_fullname")
            email = st.text_input("البريد الإلكتروني:", value=user_info.get("email", ""), key="edit_user_email")
            department = st.text_input("القسم:", value=user_info.get("department", ""), key="edit_user_department")
        
        # تغيير الدور
        new_role = st.selectbox(
            "تغيير الدور:",
            ["admin", "editor", "viewer"],
            index=["admin", "editor", "viewer"].index(user_info.get("role", "viewer")),
            key="edit_user_role"
        )
        
        if st.button("💾 حفظ التعديلات", type="primary", key="save_user_edit_btn"):
            updated = False
            
            # تحديث المعلومات
            if user_info.get("full_name") != full_name:
                users[selected_user]["full_name"] = full_name
                updated = True
            
            if user_info.get("email") != email:
                users[selected_user]["email"] = email
                updated = True
            
            if user_info.get("department") != department:
                users[selected_user]["department"] = department
                updated = True
            
            if user_info.get("role") != new_role:
                users[selected_user]["role"] = new_role
                
                # تحديث الصلاحيات حسب الدور
                if new_role == "admin":
                    users[selected_user]["permissions"] = ["all"]
                elif new_role == "editor":
                    users[selected_user]["permissions"] = ["view", "edit", "add_machines"]
                else:
                    users[selected_user]["permissions"] = ["view"]
                
                updated = True
            
            # تغيير كلمة المرور
            if new_password:
                if new_password != confirm_password:
                    st.error("❌ كلمة المرور غير مطابقة.")
                    return
                
                if len(new_password) < 6:
                    st.warning("⚠ كلمة المرور يجب أن تكون 6 أحرف على الأقل.")
                    return
                
                users[selected_user]["password"] = new_password
                updated = True
            
            if updated:
                if save_users(users):
                    st.success(f"✅ تم تحديث المستخدم {selected_user} بنجاح!")
                    
                    # إذا كان المستخدم الحالي هو الذي تم تعديله، قم بتحديث session state
                    if st.session_state.get("username") == selected_user:
                        st.session_state.user_role = new_role
                        st.session_state.user_permissions = users[selected_user].get("permissions", ["view"])
                        st.session_state.user_full_name = full_name
                        st.session_state.user_email = email
                        st.session_state.user_department = department
                        st.info("🔁 تم تحديث بيانات جلسة العمل الحالية.")
                    
                    st.rerun()
                else:
                    st.error("❌ حدث خطأ أثناء حفظ التعديلات.")
            else:
                st.info("ℹ️ لم يتم إجراء أي تغييرات.")

def delete_user_ui(users):
    """حذف مستخدم"""
    st.markdown("#### 🗑️ حذف مستخدم")
    
    permissions = get_user_permissions(
        st.session_state.get("user_role", "viewer"),
        st.session_state.get("user_permissions", ["view"])
    )
    
    if not permissions["can_manage_users"]:
        st.error("❌ ليس لديك صلاحية حذف المستخدمين.")
        return
    
    if not users:
        st.warning("⚠ لا توجد مستخدمين لحذفهم.")
        return
    
    # قائمة المستخدمين المتاحة للحذف
    current_user = st.session_state.get("username")
    deletable_users = [u for u in users.keys() if u != "admin" and u != current_user]
    
    if not deletable_users:
        st.warning("⚠ لا يمكن حذف أي مستخدمين.")
        return
    
    selected_user = st.selectbox("اختر المستخدم للحذف:", deletable_users, key="delete_user_select")
    
    if selected_user:
        user_info = users[selected_user]
        
        st.warning(f"⚠ **تحذير:** أنت على وشك حذف المستخدم '{selected_user}'")
        st.info(f"**الاسم:** {user_info.get('full_name', 'غير محدد')}")
        st.info(f"**الدور:** {user_info.get('role', 'viewer')}")
        st.info(f"**القسم:** {user_info.get('department', 'غير محدد')}")
        
        # تأكيد الحذف
        confirm_delete = st.checkbox(f"أؤكد أنني أريد حذف المستخدم '{selected_user}'", key="confirm_user_delete")
        
        if confirm_delete:
            if st.button("🗑️ حذف المستخدم نهائياً", type="primary", key="delete_user_final_btn"):
                # التحقق من عدم وجود جلسة نشطة
                state = load_state()
                if selected_user in state and state[selected_user].get("active"):
                    st.error("❌ لا يمكن حذف المستخدم أثناء تسجيل دخوله.")
                    return
                
                # حذف المستخدم
                del users[selected_user]
                
                if save_users(users):
                    st.success(f"✅ تم حذف المستخدم '{selected_user}' بنجاح!")
                    st.rerun()
                else:
                    st.error("❌ حدث خطأ أثناء حذف المستخدم.")

# -------------------------------
# ⚙️ الإعدادات
# -------------------------------
def settings_ui():
    """واجهة الإعدادات"""
    st.header("⚙️ إعدادات النظام")
    
    permissions = get_user_permissions(
        st.session_state.get("user_role", "viewer"),
        st.session_state.get("user_permissions", ["view"])
    )
    
    if not permissions["can_manage_users"]:
        st.error("❌ ليس لديك صلاحية الوصول إلى الإعدادات.")
        return
    
    tabs = st.tabs(["⚙️ إعدادات التطبيق", "📁 إدارة الملفات", "🧹 الصيانة"])
    
    with tabs[0]:
        app_settings_ui()
    
    with tabs[1]:
        file_management_ui()
    
    with tabs[2]:
        maintenance_ui()

def app_settings_ui():
    """إعدادات التطبيق"""
    st.markdown("### ⚙️ إعدادات التطبيق")
    
    # تحميل الإعدادات الحالية
    current_settings = APP_CONFIG.copy()
    
    col1, col2 = st.columns(2)
    
    with col1:
        # إعدادات عامة
        st.markdown("##### 🏢 إعدادات عامة")
        app_title = st.text_input("عنوان التطبيق:", value=current_settings["APP_TITLE"])
        app_icon = st.text_input("أيقونة التطبيق:", value=current_settings["APP_ICON"])
        show_tech_support = st.checkbox("عرض الدعم الفني للجميع", value=current_settings["SHOW_TECH_SUPPORT_TO_ALL"])
    
    with col2:
        # إعدادات الأمان
        st.markdown("##### 🔒 إعدادات الأمان")
        max_users = st.number_input("الحد الأقصى للمستخدمين النشطين:", 
                                   min_value=1, max_value=50, 
                                   value=current_settings["MAX_ACTIVE_USERS"])
        session_duration = st.number_input("مدة الجلسة (دقائق):", 
                                          min_value=5, max_value=480,
                                          value=current_settings["SESSION_DURATION_MINUTES"])
    
    # إعدادات الصور
    st.markdown("##### 📷 إعدادات الصور")
    col_img1, col_img2 = st.columns(2)
    
    with col_img1:
        max_image_size = st.number_input("الحد الأقصى لحجم الصورة (MB):",
                                        min_value=1, max_value=100,
                                        value=current_settings["MAX_IMAGE_SIZE_MB"])
    
    with col_img2:
        allowed_types = st.multiselect(
            "أنواع الصور المسموحة:",
            ["jpg", "jpeg", "png", "gif", "bmp", "webp", "svg"],
            default=current_settings["ALLOWED_IMAGE_TYPES"]
        )
    
    # إعدادات البحث
    st.markdown("##### 🔍 إعدادات البحث")
    col_search1, col_search2 = st.columns(2)
    
    with col_search1:
        search_history_size = st.number_input("حجم سجل البحث:",
                                            min_value=5, max_value=100,
                                            value=current_settings["SEARCH_HISTORY_SIZE"])
    
    with col_search2:
        favorites_limit = st.number_input("الحد الأقصى للمفضلة:",
                                        min_value=10, max_value=200,
                                        value=current_settings["FAVORITE_MACHINES_LIMIT"])
    
    if st.button("💾 حفظ الإعدادات", type="primary", key="save_settings_btn"):
        # تحديث الإعدادات
        updated_settings = {
            "APP_TITLE": app_title,
            "APP_ICON": app_icon,
            "MAX_ACTIVE_USERS": int(max_users),
            "SESSION_DURATION_MINUTES": int(session_duration),
            "SHOW_TECH_SUPPORT_TO_ALL": show_tech_support,
            "MAX_IMAGE_SIZE_MB": int(max_image_size),
            "ALLOWED_IMAGE_TYPES": allowed_types,
            "SEARCH_HISTORY_SIZE": int(search_history_size),
            "FAVORITE_MACHINES_LIMIT": int(favorites_limit)
        }
        
        # تحديث الإعدادات الأخرى من APP_CONFIG
        for key in current_settings:
            if key not in updated_settings:
                updated_settings[key] = current_settings[key]
        
        st.success("✅ تم حفظ الإعدادات!")
        
        # ملاحظة: في بيئة production، يجب حفظ هذه الإعدادات في ملف
        st.info("💡 ملاحظة: في هذه النسخة، الإعدادات تطبق للجلسة الحالية فقط.")

def file_management_ui():
    """إدارة الملفات"""
    st.markdown("### 📁 إدارة الملفات")
    
    # معلومات الملفات
    st.markdown("##### ℹ️ معلومات الملفات")
    
    files_info = [
        ("📊 قاعدة البيانات", APP_CONFIG["LOCAL_FILE"]),
        ("👥 المستخدمين", USERS_FILE),
        ("🔔 الإشعارات", NOTIFICATIONS_FILE),
        ("🔧 أنواع الماكينات", MACHINE_TYPES_FILE),
        ("🔍 سجل البحث", SEARCH_HISTORY_FILE),
        ("⭐ المفضلة", FAVORITES_FILE)
    ]
    
    for icon, file_path in files_info:
        if os.path.exists(file_path):
            size = os.path.getsize(file_path) / 1024  # كيلوبايت
            mod_time = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M:%S')
            st.markdown(f"{icon} **{file_path}** - {size:.2f} كيلوبايت - آخر تعديل: {mod_time}")
        else:
            st.markdown(f"{icon} **{file_path}** - ⚠️ غير موجود")
    
    # إجراءات الملفات
    st.markdown("##### ⚡ إجراءات الملفات")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 تحديث من GitHub", use_container_width=True):
            if fetch_from_github_requests():
                st.success("✅ تم تحديث قاعدة البيانات من GitHub!")
                st.rerun()
    
    with col2:
        if st.button("🧹 مسح الكاش", use_container_width=True):
            try:
                st.cache_data.clear()
                st.success("✅ تم مسح الكاش!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ خطأ في مسح الكاش: {e}")
    
    # نسخ احتياطية
    st.markdown("##### 💾 النسخ الاحتياطية")
    
    backup_file = st.selectbox("اختر ملف للنسخ الاحتياطي:", 
                              [f[1] for f in files_info], 
                              key="backup_file_select")
    
    if st.button("📥 تنزيل نسخة احتياطية", key="download_backup_btn"):
        if os.path.exists(backup_file):
            with open(backup_file, "rb") as f:
                file_data = f.read()
            
            st.download_button(
                label=f"📥 تحميل {backup_file}",
                data=file_data,
                file_name=f"{backup_file}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                mime="application/octet-stream",
                key=f"download_{backup_file}"
            )
        else:
            st.error(f"❌ الملف {backup_file} غير موجود.")

def maintenance_ui():
    """صيانة النظام"""
    st.markdown("### 🧹 صيانة النظام")
    
    # تنظيف البيانات
    st.markdown("##### 🗑️ تنظيف البيانات")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🧹 تنظيف الإشعارات القديمة", use_container_width=True):
            notifications = load_notifications()
            # حفظ آخر 100 إشعار فقط
            if len(notifications) > 100:
                notifications = notifications[:100]
                save_notifications(notifications)
                st.success("✅ تم تنظيف الإشعارات!")
            else:
                st.info("ℹ️ لا توجد إشعارات قديمة للتنظيف.")
    
    with col2:
        if st.button("🧹 تنظيف سجل البحث", use_container_width=True):
            history = load_search_history()
            # حفظ آخر 50 بحث فقط
            if len(history) > 50:
                history = history[:50]
                save_search_history(history)
                st.success("✅ تم تنظيف سجل البحث!")
            else:
                st.info("ℹ️ لا توجد عمليات بحث قديمة للتنظيف.")
    
    # إحصائيات النظام
    st.markdown("##### 📊 إحصائيات النظام")
    
    # إحصائيات الماكينات
    all_sheets = load_all_sheets()
    total_machines = 0
    if all_sheets:
        for df in all_sheets.values():
            total_machines += len(df)
    
    # إحصائيات المستخدمين
    users = load_users()
    total_users = len(users)
    
    # إحصائيات الصور
    image_count = 0
    image_size = 0
    if os.path.exists(IMAGES_FOLDER):
        image_files = [f for f in os.listdir(IMAGES_FOLDER) if f.lower().endswith(tuple(APP_CONFIG["ALLOWED_IMAGE_TYPES"]))]
        image_count = len(image_files)
        image_size = sum(os.path.getsize(os.path.join(IMAGES_FOLDER, f)) for f in image_files) / (1024 * 1024)  # ميجابايت
    
    col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
    
    with col_stat1:
        st.metric("🔢 إجمالي الماكينات", total_machines)
    
    with col_stat2:
        st.metric("👥 عدد المستخدمين", total_users)
    
    with col_stat3:
        st.metric("📸 عدد الصور", image_count)
    
    with col_stat4:
        st.metric("💾 حجم الصور", f"{image_size:.2f} MB")
    
    # إعادة تعيين النظام
    st.markdown("##### ⚠️ إجراءات متقدمة")
    
    if st.button("🔄 إعادة تشغيل التطبيق", key="restart_app_btn"):
        try:
            st.cache_data.clear()
            st.rerun()
        except Exception as e:
            st.error(f"❌ خطأ في إعادة التشغيل: {e}")

# -------------------------------
# 📞 الدعم الفني
# -------------------------------
def tech_support_ui():
    """واجهة الدعم الفني"""
    st.header("📞 الدعم الفني")
    
    # معلومات النظام
    st.markdown("### ℹ️ معلومات النظام")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info(f"**اسم التطبيق:** {APP_CONFIG['APP_TITLE']}")
        st.info(f"**الملف الرئيسي:** {APP_CONFIG['FILE_PATH']}")
        st.info(f"**المستودع:** {APP_CONFIG['REPO_NAME']}")
    
    with col2:
        st.info(f"**المستخدم الحالي:** {st.session_state.get('username', 'غير مسجل')}")
        st.info(f"**الدور:** {st.session_state.get('user_role', 'غير محدد')}")
        st.info(f"**آخر تحديث:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # استكشاف الأخطاء
    st.markdown("### 🔧 استكشاف الأخطاء وإصلاحها")
    
    issues = [
        {
            "problem": "لا يمكن تحميل الملف من GitHub",
            "solution": "تأكد من اتصال الإنترنت، وتحقق من رابط الملف، واضغط على زر '🔄 تحديث الملف من GitHub'"
        },
        {
            "problem": "لا يمكن حفظ التعديلات",
            "solution": "تأكد من وجود token GitHub في الإعدادات، وتحقق من صلاحيات الرفع إلى المستودع"
        },
        {
            "problem": "التطبيق يعمل ببطء",
            "solution": "اضغط على زر '🧹 مسح الكاش'، قلل عدد الصفوف المعروضة، استخدم فلاتر البحث"
        },
        {
            "problem": "الصور لا تظهر",
            "solution": f"تأكد من أن ملفات الصور موجودة في مجلد {IMAGES_FOLDER}، تحقق من أذونات المجلد"
        },
        {
            "problem": "البحث لا يعمل",
            "solution": "تأكد من تنسيق البيانات، جرب بحثاً أبسط، تحقق من أسماء الأعمدة"
        }
    ]
    
    for issue in issues:
        with st.expander(f"❓ {issue['problem']}", expanded=False):
            st.markdown(f"**الحل:** {issue['solution']}")
    
    # معلومات الجلسة
    st.markdown("### 🖥 معلومات الجلسة الحالية")
    
    if st.session_state.get("logged_in"):
        session_info = {
            "المستخدم": st.session_state.get("username", "غير معروف"),
            "الدور": st.session_state.get("user_role", "غير معروف"),
            "الصلاحيات": ", ".join(st.session_state.get("user_permissions", [])),
            "الاسم الكامل": st.session_state.get("user_full_name", "غير محدد"),
            "البريد الإلكتروني": st.session_state.get("user_email", "غير محدد"),
            "القسم": st.session_state.get("user_department", "غير محدد")
        }
        
        for key, value in session_info.items():
            if value:
                st.text(f"**{key}:** {value}")
    else:
        st.info("ℹ️ لم يتم تسجيل الدخول")
    
    # زر الاتصال بالدعم
    st.markdown("### 📞 الاتصال بالدعم")
    
    contact_info = st.text_area(
        "وصف المشكلة:",
        placeholder="صف المشكلة التي تواجهها بالتفصيل...",
        height=100
    )
    
    if st.button("📤 إرسال تقرير المشكلة", key="send_support_request"):
        if contact_info:
            # في بيئة production، يمكن إرسال البريد الإلكتروني هنا
            st.success("✅ تم إرسال تقرير المشكلة!")
            st.info("سيتم الرد عليك في أقرب وقت ممكن.")
        else:
            st.warning("⚠ الرجاء وصف المشكلة أولاً.")

# -------------------------------
# 🖥 الواجهة الرئيسية المدمجة
# -------------------------------
# إعداد الصفحة
st.set_page_config(page_title=APP_CONFIG["APP_TITLE"], layout="wide")

# إعداد مجلد الصور
setup_images_folder()

# الشريط الجانبي
with st.sidebar:
    st.header("👤 الجلسة")
    if not st.session_state.get("logged_in"):
        if not login_ui():
            st.stop()
    else:
        state = cleanup_sessions(load_state())
        username = st.session_state.username
        user_role = st.session_state.user_role
        rem = remaining_time(state, username)
        if rem:
            mins, secs = divmod(int(rem.total_seconds()), 60)
            st.success(f"👋 {username} | الدور: {user_role} | ⏳ {mins:02d}:{secs:02d}")
        else:
            logout_action()
    
    st.markdown("---")
    st.write("🔧 أدوات:")
    
    # أزرار الإدارة السريعة
    col_tool1, col_tool2 = st.columns(2)
    with col_tool1:
        if st.button("🔄 تحديث", key="refresh_github_btn"):
            if fetch_from_github_requests():
                st.rerun()
    
    with col_tool2:
        if st.button("🗑 كاش", key="clear_cache_btn"):
            try:
                st.cache_data.clear()
                st.rerun()
            except:
                pass
    
    # المفضلة
    st.markdown("---")
    st.markdown("### ⭐ المفضلة")
    
    favorites = get_favorites_for_user()
    if favorites:
        for fav in favorites[:5]:  # عرض أول 5 مفضلة
            machine_type, machine_id = fav.split(":", 1)
            machine_types = load_machine_types()
            type_name = machine_types.get(machine_type, {}).get("name", machine_type)
            st.markdown(f"• {type_name} - {machine_id}")
        
        if len(favorites) > 5:
            st.caption(f"... و {len(favorites) - 5} أخرى")
    else:
        st.caption("لا توجد مفضلات")
    
    # الإشعارات (للمسؤولين)
    if st.session_state.get("user_role") == "admin":
        show_notifications_ui()
    
    st.markdown("---")
    if st.button("🚪 تسجيل الخروج", key="logout_btn"):
        logout_action()

# تحميل البيانات
all_sheets = load_all_sheets()
sheets_edit = load_sheets_for_edit()

# الواجهة الرئيسية
st.title(f"{APP_CONFIG['APP_ICON']} {APP_CONFIG['APP_TITLE']}")

# التحقق من الصلاحيات
username = st.session_state.get("username")
user_role = st.session_state.get("user_role", "viewer")
user_permissions = st.session_state.get("user_permissions", ["view"])
permissions = get_user_permissions(user_role, user_permissions)

# تحديد التبويبات بناءً على الصلاحيات
if permissions["can_manage_users"]:  # admin
    tabs = st.tabs(APP_CONFIG["CUSTOM_TABS"])
    
    with tabs[0]:  # البحث في الماكينات
        if all_sheets is None:
            st.warning("❗ قاعدة البيانات غير موجودة. استخدم زر التحديث في الشريط الجانبي.")
        else:
            search_machines_ui(all_sheets)
    
    with tabs[1]:  # إدارة الماكينات
        if sheets_edit is None:
            st.warning("❗ قاعدة البيانات غير موجودة. اضغط تحديث أولاً.")
        else:
            manage_machines_ui(sheets_edit)
    
    with tabs[2]:  # إضافة نوع مكن
        add_machine_type_ui()
    
    with tabs[3]:  # إدارة المستخدمين
        manage_users_ui()
    
    with tabs[4]:  # الإعدادات
        settings_ui()
    
    with tabs[5]:  # الدعم الفني
        tech_support_ui()

elif permissions["can_edit"]:  # editor
    tabs = st.tabs(["📋 البحث في الماكينات", "🛠 إدارة الماكينات", "📞 الدعم الفني"])
    
    with tabs[0]:
        if all_sheets is None:
            st.warning("❗ قاعدة البيانات غير موجودة. استخدم زر التحديث في الشريط الجانبي.")
        else:
            search_machines_ui(all_sheets)
    
    with tabs[1]:
        if sheets_edit is None:
            st.warning("❗ قاعدة البيانات غير موجودة. اضغط تحديث أولاً.")
        else:
            manage_machines_ui(sheets_edit)
    
    with tabs[2]:
        tech_support_ui()

else:  # viewer
    tabs = st.tabs(["📋 البحث في الماكينات", "📞 الدعم الفني"])
    
    with tabs[0]:
        if all_sheets is None:
            st.warning("❗ قاعدة البيانات غير موجودة. استخدم زر التحديث في الشريط الجانبي.")
        else:
            search_machines_ui(all_sheets)
    
    with tabs[1]:
        tech_support_ui()
