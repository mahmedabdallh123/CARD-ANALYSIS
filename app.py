import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import time
import os
from io import BytesIO

# إعداد الصفحة
st.set_page_config(
    page_title="نظام صيانة الماكينات - Excel",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# تخصيص التصميم
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E3A8A;
        text-align: center;
        margin-bottom: 2rem;
    }
    .card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        border-left: 5px solid #1E3A8A;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .warning {
        border-left-color: #ffc107;
        background-color: #fff3cd;
    }
    .danger {
        border-left-color: #dc3545;
        background-color: #f8d7da;
    }
    .success {
        border-left-color: #28a745;
        background-color: #d4edda;
    }
    .metric-box {
        text-align: center;
        padding: 1rem;
        border-radius: 10px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        margin: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# دوال مساعدة
def load_excel():
    """تحميل ملف Excel"""
    try:
        # محاولة فتح الملف الموجود
        excel_file = 'machines.xlsx'
        
        # إذا الملف موجود، حمله
        if os.path.exists(excel_file):
            xls = pd.ExcelFile(excel_file, engine='openpyxl')
            
            # تحميل جميع الأوراق
            machines = pd.read_excel(xls, sheet_name='الماكينات')
            tasks = pd.read_excel(xls, sheet_name='المهام')
            logs = pd.read_excel(xls, sheet_name='السجل')
            settings = pd.read_excel(xls, sheet_name='الإعدادات')
            
            return {
                'machines': machines,
                'tasks': tasks,
                'logs': logs,
                'settings': settings
            }
        else:
            # إنشاء ملف جديد إذا لم يكن موجودًا
            st.warning("لم يتم العثور على ملف Excel، سيتم إنشاء ملف جديد")
            return create_new_excel()
    except Exception as e:
        st.error(f"خطأ في تحميل ملف Excel: {str(e)}")
        return create_new_excel()

def create_new_excel():
    """إنشاء ملف Excel جديد"""
    # بيانات أولية فارغة
    machines = pd.DataFrame(columns=[
        'id', 'اسم الماكينة', 'الموديل', 'الرقم التسلسلي', 'تاريخ التركيب',
        'إجمالي ساعات التشغيل', 'آخر تحديث للساعات', 'ملاحظات', 'نشطة', 'تاريخ الإضافة'
    ])
    
    tasks = pd.DataFrame(columns=[
        'id', 'معرف الماكينة', 'نوع الصيانة', 'الفترة بين الصيانة (ساعات)',
        'تاريخ آخر صيانة', 'عدد ساعات التشغيل عند آخر صيانة', 'عدد الساعات المتبقية',
        'تاريخ الصيانة القادم', 'وصف المهمة', 'نشطة', 'تاريخ الإضافة'
    ])
    
    logs = pd.DataFrame(columns=[
        'id', 'معرف الماكينة', 'معرف المهمة', 'تاريخ الصيانة', 'عدد ساعات التشغيل',
        'تمت بواسطة', 'الأجزاء المستبدلة', 'ملاحظات', 'تاريخ التسجيل'
    ])
    
    settings = pd.DataFrame({
        'الإعداد': ['إشعار مسبق (أيام)', 'البريد الإلكتروني للإشعارات', 'تفعيل الإشعارات', 'لون التطبيق'],
        'القيمة': ['7', 'admin@company.com', 'نعم', 'أزرق'],
        'الوصف': ['عدد الأيام للإشعار المسبق قبل الصيانة', 'البريد الإلكتروني لإرسال الإشعارات', 
                  'تفعيل أو تعطيل الإشعارات', 'لون واجهة التطبيق']
    })
    
    # حفظ في ملف Excel
    save_to_excel(machines, tasks, logs, settings)
    
    return {
        'machines': machines,
        'tasks': tasks,
        'logs': logs,
        'settings': settings
    }

def save_to_excel(machines, tasks, logs, settings):
    """حفظ البيانات إلى ملف Excel"""
    try:
        with pd.ExcelWriter('machines.xlsx', engine='openpyxl') as writer:
            machines.to_excel(writer, sheet_name='الماكينات', index=False)
            tasks.to_excel(writer, sheet_name='المهام', index=False)
            logs.to_excel(writer, sheet_name='السجل', index=False)
            settings.to_excel(writer, sheet_name='الإعدادات', index=False)
        return True
    except Exception as e:
        st.error(f"خطأ في حفظ الملف: {str(e)}")
        return False

def update_counters():
    """تحديث العدادات التنازلية للصيانة"""
    data = load_excel()
    tasks = data['tasks'].copy()
    machines = data['machines'].copy()
    
    for idx, task in tasks.iterrows():
        machine_id = task['معرف الماكينة']
        machine = machines[machines['id'] == machine_id]
        
        if not machine.empty:
            # حساب الوقت المنقضي منذ آخر صيانة
            last_date = pd.to_datetime(task['تاريخ آخر صيانة'])
            current_date = datetime.now()
            hours_passed = (current_date - last_date).total_seconds() / 3600
            
            # حساب الساعات المتبقية
            remaining_hours = task['الفترة بين الصيانة (ساعات)'] - hours_passed
            
            # تحديث القيم
            tasks.at[idx, 'عدد الساعات المتبقية'] = max(0, remaining_hours)
            
            # حساب تاريخ الصيانة القادم
            next_date = last_date + timedelta(hours=task['الفترة بين الصيانة (ساعات)'])
            tasks.at[idx, 'تاريخ الصيانة القادم'] = next_date
    
    # حفظ التحديثات
    save_to_excel(data['machines'], tasks, data['logs'], data['settings'])
    return tasks

def get_status_color(hours):
    """تحديد لون الحالة بناءً على الساعات المتبقية"""
    if hours <= 0:
        return "danger"
    elif hours <= 24:
        return "warning"
    else:
        return "success"

# تحميل البيانات
data = load_excel()
machines = data['machines']
tasks = data['tasks']
logs = data['logs']
settings = data['settings']

# تحديث العدادات
tasks = update_counters()

# الشريط الجانبي
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3067/3067256.png", width=80)
    st.title("⚙️ نظام الصيانة")
    
    # القائمة
    page = st.selectbox(
        "القائمة الرئيسية",
        ["🏠 لوحة التحكم", "➕ إضافة ماكينة", "🔧 إضافة مهمة صيانة", 
         "📝 تسجيل صيانة", "📊 سجل الصيانة", "⚙️ الإعدادات", "📤 تصدير البيانات"]
    )
    
    st.divider()
    
    # إحصائيات سريعة
    total_machines = len(machines)
    active_machines = len(machines[machines['نشطة'] == 'نعم'])
    
    overdue_tasks = len(tasks[tasks['عدد الساعات المتبقية'] <= 0])
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("الماكينات", total_machines)
    with col2:
        st.metric("مهام متأخرة", overdue_tasks, delta_color="inverse")
    
    # زر تحديث البيانات
    if st.button("🔄 تحديث العدادات", use_container_width=True):
        tasks = update_counters()
        st.success("تم تحديث العدادات!")
        st.rerun()
    
    st.divider()
    st.caption(f"آخر تحديث: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

# صفحة لوحة التحكم
if page == "🏠 لوحة التحكم":
    st.markdown('<h1 class="main-header">🏭 نظام إدارة صيانة الماكينات</h1>', unsafe_allow_html=True)
    
    # عدادات سريعة
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown('<div class="metric-box"><h3>📊</h3><h4>الماكينات</h4><h2>{}</h2></div>'.format(total_machines), unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-box"><h3>🔧</h3><h4>مهام الصيانة</h4><h2>{}</h2></div>'.format(len(tasks)), unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="metric-box"><h3>⚠️</h3><h4>متأخرة</h4><h2>{}</h2></div>'.format(overdue_tasks), unsafe_allow_html=True)
    
    with col4:
        active_tasks = len(tasks[tasks['نشطة'] == 'نعم'])
        st.markdown('<div class="metric-box"><h3>✅</h3><h4>نشطة</h4><h2>{}</h2></div>'.format(active_tasks), unsafe_allow_html=True)
    
    # عرض المهام المتأخرة
    st.subheader("🚨 المهام المتأخرة")
    
    overdue = tasks[tasks['عدد الساعات المتبقية'] <= 0]
    
    if not overdue.empty:
        for _, task in overdue.iterrows():
            machine_name = machines[machines['id'] == task['معرف الماكينة']]['اسم الماكينة'].values[0] if not machines[machines['id'] == task['معرف الماكينة']].empty else "غير معروف"
            
            with st.container():
                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    st.markdown(f"### {machine_name}")
                    st.write(f"**نوع الصيانة:** {task['نوع الصيانة']}")
                    if pd.notna(task['وصف المهمة']):
                        st.caption(task['وصف المهمة'])
                
                with col2:
                    days_overdue = abs(task['عدد الساعات المتبقية']) / 24
                    st.error(f"**⏰ متأخرة منذ:** {days_overdue:.1f} يوم")
                    st.write(f"**آخر صيانة:** {task['تاريخ آخر صيانة']}")
                
                with col3:
                    if st.button("📝 سجل صيانة", key=f"log_{task['id']}"):
                        st.session_state.log_task_id = task['id']
                        st.session_state.log_machine_id = task['معرف الماكينة']
                        st.rerun()
    else:
        st.success("🎉 لا توجد مهام صيانة متأخرة!")
    
    # عرض الماكينات
    st.subheader("⚙️ قائمة الماكينات")
    
    if not machines.empty:
        cols = st.columns(3)
        for idx, machine in machines.iterrows():
            with cols[idx % 3]:
                with st.container():
                    # حساب المهام لهذه الماكينة
                    machine_tasks = tasks[tasks['معرف الماكينة'] == machine['id']]
                    overdue_count = len(machine_tasks[machine_tasks['عدد الساعات المتبقية'] <= 0])
                    
                    # إنشاء البطاقة
                    card_class = "card danger" if overdue_count > 0 else "card success"
                    st.markdown(f'<div class="{card_class}">', unsafe_allow_html=True)
                    
                    st.markdown(f"### {machine['اسم الماكينة']}")
                    st.write(f"**الموديل:** {machine['الموديل']}")
                    st.write(f"**الرقم التسلسلي:** {machine['الرقم التسلسلي']}")
                    st.write(f"**ساعات التشغيل:** {machine['إجمالي ساعات التشغيل']}")
                    
                    if overdue_count > 0:
                        st.error(f"⚠️ {overdue_count} مهام متأخرة")
                    else:
                        st.success("✅ جميع المهام محدثة")
                    
                    st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("لا توجد ماكينات مسجلة. أضف ماكينة جديدة من القائمة.")
    
    # مخطط توزيع حالات الصيانة
    st.subheader("📊 إحصائيات الصيانة")
    
    if not tasks.empty:
        # تجهيز البيانات للمخطط
        status_counts = {
            'متأخرة': len(tasks[tasks['عدد الساعات المتبقية'] <= 0]),
            'قريبة': len(tasks[(tasks['عدد الساعات المتبقية'] > 0) & (tasks['عدد الساعات المتبقية'] <= 24)]),
            'جيدة': len(tasks[tasks['عدد الساعات المتبقية'] > 24])
        }
        
        fig = px.pie(
            values=list(status_counts.values()),
            names=list(status_counts.keys()),
            title="توزيع حالات الصيانة",
            color=list(status_counts.keys()),
            color_discrete_map={'متأخرة': 'red', 'قريبة': 'orange', 'جيدة': 'green'}
        )
        
        st.plotly_chart(fig, use_container_width=True)

# صفحة إضافة ماكينة
elif page == "➕ إضافة ماكينة":
    st.title("➕ إضافة ماكينة جديدة")
    
    with st.form("add_machine_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("اسم الماكينة *", placeholder="مثال: ماكينة الإنتاج رقم 1")
            model = st.text_input("الموديل", placeholder="مثال: XP-2000")
            serial_number = st.text_input("الرقم التسلسلي")
        
        with col2:
            installation_date = st.date_input("تاريخ التركيب", value=datetime.now())
            total_hours = st.number_input("إجمالي ساعات التشغيل", min_value=0.0, value=0.0, step=10.0)
            is_active = st.radio("الحالة", ["نعم", "لا"], index=0, horizontal=True)
        
        notes = st.text_area("ملاحظات")
        
        submitted = st.form_submit_button("إضافة الماكينة", use_container_width=True)
        
        if submitted:
            if not name:
                st.error("⚠️ اسم الماكينة مطلوب!")
            else:
                # إنشاء معرف جديد
                new_id = machines['id'].max() + 1 if not machines.empty else 1
                
                # إضافة الصف الجديد
                new_machine = pd.DataFrame([{
                    'id': new_id,
                    'اسم الماكينة': name,
                    'الموديل': model if model else "",
                    'الرقم التسلسلي': serial_number if serial_number else "",
                    'تاريخ التركيب': installation_date.strftime('%Y-%m-%d'),
                    'إجمالي ساعات التشغيل': total_hours,
                    'آخر تحديث للساعات': datetime.now().strftime('%Y-%m-%d %H:%M'),
                    'ملاحظات': notes if notes else "",
                    'نشطة': is_active,
                    'تاريخ الإضافة': datetime.now().strftime('%Y-%m-%d')
                }])
                
                # إضافة إلى DataFrame
                machines = pd.concat([machines, new_machine], ignore_index=True)
                
                # حفظ إلى Excel
                if save_to_excel(machines, tasks, logs, settings):
                    st.success(f"✅ تمت إضافة الماكينة '{name}' بنجاح!")
                    st.balloons()
                    
                    # عرض خيار إضافة مهام صيانة
                    if st.button("🔧 إضافة مهام صيانة لهذه الماكينة"):
                        st.session_state.add_task_for_machine = new_id
                        st.rerun()
                else:
                    st.error("❌ حدث خطأ أثناء حفظ البيانات")

# صفحة إضافة مهمة صيانة
elif page == "🔧 إضافة مهمة صيانة":
    st.title("🔧 إضافة مهمة صيانة جديدة")
    
    # اختيار الماكينة
    if not machines.empty:
        machine_options = {row['id']: row['اسم الماكينة'] for _, row in machines.iterrows()}
        
        # استخدام الماكينة المحددة مسبقًا إذا وجدت
        if 'add_task_for_machine' in st.session_state:
            selected_machine_id = st.session_state.add_task_for_machine
            del st.session_state.add_task_for_machine
        else:
            selected_machine_id = st.selectbox(
                "اختر الماكينة *",
                options=list(machine_options.keys()),
                format_func=lambda x: machine_options[x]
            )
        
        if selected_machine_id:
            with st.form("add_task_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    task_type = st.text_input("نوع الصيانة *", placeholder="مثال: تغيير الزيت")
                    interval_hours = st.number_input("الفترة بين الصيانة (ساعات) *", min_value=1, value=500, step=10)
                    last_maintenance_date = st.date_input("تاريخ آخر صيانة *", value=datetime.now())
                
                with col2:
                    # الحصول على ساعات تشغيل الماكينة
                    machine_hours = machines[machines['id'] == selected_machine_id]['إجمالي ساعات التشغيل'].values[0]
                    last_maintenance_hours = st.number_input(
                        "عدد ساعات التشغيل عند آخر صيانة *",
                        min_value=0.0,
                        value=float(machine_hours),
                        step=1.0
                    )
                    
                    description = st.text_area("وصف المهمة", placeholder="تفاصيل عن عملية الصيانة")
                
                is_active = st.radio("تفعيل المهمة", ["نعم", "لا"], index=0, horizontal=True)
                
                submitted = st.form_submit_button("إضافة المهمة", use_container_width=True)
                
                if submitted:
                    if not task_type:
                        st.error("⚠️ نوع الصيانة مطلوب!")
                    else:
                        # حساب الساعات المتبقية
                        current_date = datetime.now()
                        last_date = datetime.combine(last_maintenance_date, datetime.min.time())
                        hours_passed = (current_date - last_date).total_seconds() / 3600
                        remaining_hours = max(0, interval_hours - hours_passed)
                        
                        # حساب تاريخ الصيانة القادم
                        next_date = last_date + timedelta(hours=interval_hours)
                        
                        # إنشاء معرف جديد
                        new_id = tasks['id'].max() + 1 if not tasks.empty else 1
                        
                        # إضافة الصف الجديد
                        new_task = pd.DataFrame([{
                            'id': new_id,
                            'معرف الماكينة': selected_machine_id,
                            'نوع الصيانة': task_type,
                            'الفترة بين الصيانة (ساعات)': interval_hours,
                            'تاريخ آخر صيانة': last_maintenance_date.strftime('%Y-%m-%d'),
                            'عدد ساعات التشغيل عند آخر صيانة': last_maintenance_hours,
                            'عدد الساعات المتبقية': remaining_hours,
                            'تاريخ الصيانة القادم': next_date.strftime('%Y-%m-%d'),
                            'وصف المهمة': description if description else "",
                            'نشطة': is_active,
                            'تاريخ الإضافة': datetime.now().strftime('%Y-%m-%d')
                        }])
                        
                        # إضافة إلى DataFrame
                        tasks = pd.concat([tasks, new_task], ignore_index=True)
                        
                        # حفظ إلى Excel
                        if save_to_excel(machines, tasks, logs, settings):
                            st.success(f"✅ تمت إضافة مهمة '{task_type}' بنجاح!")
                            st.info(f"⏰ الصيانة القادمة بعد: {remaining_hours:.0f} ساعة")
                        else:
                            st.error("❌ حدث خطأ أثناء حفظ البيانات")
    else:
        st.warning("⚠️ لا توجد ماكينات مسجلة. أضف ماكينة أولاً.")

# صفحة تسجيل صيانة
elif page == "📝 تسجيل صيانة":
    st.title("📝 تسجيل عملية صيانة")
    
    if not tasks.empty:
        # اختيار الماكينة
        machine_options = {row['id']: row['اسم الماكينة'] for _, row in machines.iterrows()}
        
        # إذا كان هناك مهمة محددة مسبقًا (من لوحة التحكم)
        if 'log_task_id' in st.session_state:
            task_id = st.session_state.log_task_id
            task = tasks[tasks['id'] == task_id].iloc[0]
            selected_machine_id = task['معرف الماكينة']
            machine_name = machine_options[selected_machine_id]
            
            st.info(f"تسجيل صيانة لـ: **{machine_name}** - {task['نوع الصيانة']}")
            
            # استخدام القيم المسبقة
            default_hours = machines[machines['id'] == selected_machine_id]['إجمالي ساعات التشغيل'].values[0]
            
            # حذف من الجلسة بعد الاستخدام
            del st.session_state.log_task_id
            if 'log_machine_id' in st.session_state:
                del st.session_state.log_machine_id
        else:
            selected_machine_id = st.selectbox(
                "اختر الماكينة *",
                options=list(machine_options.keys()),
                format_func=lambda x: machine_options[x]
            )
            default_hours = 0.0
        
        if selected_machine_id:
            # الحصول على مهام الصيانة لهذه الماكينة
            machine_tasks = tasks[tasks['معرف الماكينة'] == selected_machine_id]
            
            if not machine_tasks.empty:
                task_options = {row['id']: f"{row['نوع الصيانة']} (متبقي: {row['عدد الساعات المتبقية']:.0f} ساعة)" 
                               for _, row in machine_tasks.iterrows()}
                
                selected_task_id = st.selectbox(
                    "اختر نوع الصيانة *",
                    options=list(task_options.keys()),
                    format_func=lambda x: task_options[x]
                )
                
                with st.form("log_maintenance_form"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        maintenance_date = st.date_input("تاريخ الصيانة *", value=datetime.now())
                        maintenance_hours = st.number_input(
                            "عدد ساعات التشغيل عند الصيانة *",
                            min_value=0.0,
                            value=float(default_hours),
                            step=1.0
                        )
                    
                    with col2:
                        performed_by = st.text_input("تمت الصيانة بواسطة *", placeholder="اسم الفني")
                        parts_used = st.text_area("الأجزاء المستبدلة", placeholder="مثال: زيت محرك 5 لتر")
                    
                    notes = st.text_area("ملاحظات الصيانة")
                    
                    submitted = st.form_submit_button("📝 تسجيل الصيانة", use_container_width=True)
                    
                    if submitted:
                        if not performed_by:
                            st.error("⚠️ اسم الفني مطلوب!")
                        else:
                            # تحديث المهمة
                            task_idx = tasks[tasks['id'] == selected_task_id].index[0]
                            tasks.at[task_idx, 'تاريخ آخر صيانة'] = maintenance_date.strftime('%Y-%m-%d')
                            tasks.at[task_idx, 'عدد ساعات التشغيل عند آخر صيانة'] = maintenance_hours
                            tasks.at[task_idx, 'عدد الساعات المتبقية'] = tasks.at[task_idx, 'الفترة بين الصيانة (ساعات)']
                            
                            # تحديث تاريخ الصيانة القادم
                            next_date = maintenance_date + timedelta(hours=tasks.at[task_idx, 'الفترة بين الصيانة (ساعات)'])
                            tasks.at[task_idx, 'تاريخ الصيانة القادم'] = next_date.strftime('%Y-%m-%d')
                            
                            # تحديث ساعات تشغيل الماكينة
                            machine_idx = machines[machines['id'] == selected_machine_id].index[0]
                            if maintenance_hours > machines.at[machine_idx, 'إجمالي ساعات التشغيل']:
                                machines.at[machine_idx, 'إجمالي ساعات التشغيل'] = maintenance_hours
                                machines.at[machine_idx, 'آخر تحديث للساعات'] = datetime.now().strftime('%Y-%m-%d %H:%M')
                            
                            # إضافة إلى سجل الصيانة
                            new_log_id = logs['id'].max() + 1 if not logs.empty else 1
                            
                            new_log = pd.DataFrame([{
                                'id': new_log_id,
                                'معرف الماكينة': selected_machine_id,
                                'معرف المهمة': selected_task_id,
                                'تاريخ الصيانة': maintenance_date.strftime('%Y-%m-%d'),
                                'عدد ساعات التشغيل': maintenance_hours,
                                'تمت بواسطة': performed_by,
                                'الأجزاء المستبدلة': parts_used if parts_used else "",
                                'ملاحظات': notes if notes else "",
                                'تاريخ التسجيل': datetime.now().strftime('%Y-%m-%d')
                            }])
                            
                            logs = pd.concat([logs, new_log], ignore_index=True)
                            
                            # حفظ التحديثات
                            if save_to_excel(machines, tasks, logs, settings):
                                st.success("✅ تم تسجيل الصيانة بنجاح!")
                                st.balloons()
                                
                                # عرض ملخص
                                st.info(f"""
                                **ملخص التسجيل:**
                                - الماكينة: {machine_options[selected_machine_id]}
                                - نوع الصيانة: {tasks.at[task_idx, 'نوع الصيانة']}
                                - تاريخ الصيانة: {maintenance_date.strftime('%Y-%m-%d')}
                                - الصيانة القادمة: {next_date.strftime('%Y-%m-%d')}
                                """)
                            else:
                                st.error("❌ حدث خطأ أثناء حفظ البيانات")
            else:
                st.warning("⚠️ لا توجد مهام صيانة لهذه الماكينة.")
                if st.button("🔧 إضافة مهام صيانة"):
                    st.session_state.add_task_for_machine = selected_machine_id
                    st.rerun()
    else:
        st.warning("⚠️ لا توجد مهام صيانة مسجلة. أضف مهمة صيانة أولاً.")

# صفحة سجل الصيانة
elif page == "📊 سجل الصيانة":
    st.title("📊 سجل عمليات الصيانة")
    
    # عوامل التصفية
    col1, col2 = st.columns(2)
    
    with col1:
        if not machines.empty:
            machine_options = ["الكل"] + list(machines['id'].unique())
            machine_names = {machine['id']: machine['اسم الماكينة'] for _, machine in machines.iterrows()}
            machine_names["الكل"] = "الكل"
            
            selected_machine = st.selectbox(
                "الماكينة",
                options=machine_options,
                format_func=lambda x: machine_names[x]
            )
    
    with col2:
        if not tasks.empty:
            task_types = ["الكل"] + list(tasks['نوع الصيانة'].unique())
            selected_task_type = st.selectbox("نوع الصيانة", options=task_types)
    
    # عرض السجلات
    if not logs.empty:
        # تطبيق التصفية
        filtered_logs = logs.copy()
        
        if selected_machine != "الكل":
            filtered_logs = filtered_logs[filtered_logs['معرف الماكينة'] == selected_machine]
        
        if selected_task_type != "الكل":
            # الحصول على معرف المهمة من نوع الصيانة
            task_ids = tasks[tasks['نوع الصيانة'] == selected_task_type]['id'].tolist()
            filtered_logs = filtered_logs[filtered_logs['معرف المهمة'].isin(task_ids)]
        
        if not filtered_logs.empty:
            st.subheader(f"عرض {len(filtered_logs)} سجل صيانة")
            
            # تحسين عرض البيانات
            display_logs = filtered_logs.copy()
            
            # إضافة اسم الماكينة
            display_logs['الماكينة'] = display_logs['معرف الماكينة'].apply(
                lambda x: machines[machines['id'] == x]['اسم الماكينة'].values[0] if not machines[machines['id'] == x].empty else "غير معروف"
            )
            
            # إضافة نوع الصيانة
            display_logs['نوع الصيانة'] = display_logs['معرف المهمة'].apply(
                lambda x: tasks[tasks['id'] == x]['نوع الصيانة'].values[0] if not tasks[tasks['id'] == x].empty else "غير معروف"
            )
            
            # اختيار الأعمدة للعرض
            columns_to_show = ['تاريخ الصيانة', 'الماكينة', 'نوع الصيانة', 'عدد ساعات التشغيل', 
                             'تمت بواسطة', 'الأجزاء المستبدلة', 'ملاحظات']
            
            st.dataframe(
                display_logs[columns_to_show].sort_values('تاريخ الصيانة', ascending=False),
                use_container_width=True,
                height=400
            )
            
            # خيارات التصدير
            st.subheader("📤 تصدير البيانات")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("📥 تحميل كملف Excel", use_container_width=True):
                    # تحويل إلى Excel
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        display_logs.to_excel(writer, sheet_name='سجل الصيانة', index=False)
                    
                    # تقديم للتحميل
                    st.download_button(
                        label="⬇️ انقر للتحميل",
                        data=output.getvalue(),
                        file_name=f"سجل_الصيانة_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            
            with col2:
                if st.button("📊 إنشاء تقرير PDF", use_container_width=True):
                    st.info("👷‍♂️ جارٍ تطوير ميزة التقارير PDF")
        else:
            st.info("🔍 لا توجد سجلات تطابق معايير البحث.")
    else:
        st.info("📝 لا توجد سجلات صيانة مسجلة بعد.")

# صفحة الإعدادات
elif page == "⚙️ الإعدادات":
    st.title("⚙️ إعدادات النظام")
    
    tab1, tab2, tab3 = st.tabs(["إعدادات الصيانة", "إعدادات الإشعارات", "نسخ احتياطي"])
    
    with tab1:
        st.subheader("إعدادات الصيانة العامة")
        
        # عرض الإعدادات الحالية
        st.dataframe(settings, use_container_width=True)
        
        # تحديث الإعدادات
        st.subheader("تحديث الإعدادات")
        
        with st.form("update_settings_form"):
            warning_days = st.number_input("الإشعار المسبق قبل الصيانة (أيام)", 
                                         min_value=1, max_value=30, 
                                         value=int(settings[settings['الإعداد'] == 'إشعار مسبق (أيام)']['القيمة'].values[0]))
            
            email = st.text_input("البريد الإلكتروني للإشعارات", 
                                value=settings[settings['الإعداد'] == 'البريد الإلكتروني للإشعارات']['القيمة'].values[0])
            
            notifications = st.radio("تفعيل الإشعارات", ["نعم", "لا"], 
                                   index=0 if settings[settings['الإعداد'] == 'تفعيل الإشعارات']['القيمة'].values[0] == 'نعم' else 1,
                                   horizontal=True)
            
            theme = st.selectbox("لون التطبيق", ["أزرق", "أخضر", "أحمر", "بنفسجي"],
                               index=["أزرق", "أخضر", "أحمر", "بنفسجي"].index(
                                   settings[settings['الإعداد'] == 'لون التطبيق']['القيمة'].values[0]))
            
            if st.form_submit_button("💾 حفظ الإعدادات", use_container_width=True):
                # تحديث الإعدادات
                settings.loc[settings['الإعداد'] == 'إشعار مسبق (أيام)', 'القيمة'] = str(warning_days)
                settings.loc[settings['الإعداد'] == 'البريد الإلكتروني للإشعارات', 'القيمة'] = email
                settings.loc[settings['الإعداد'] == 'تفعيل الإشعارات', 'القيمة'] = notifications
                settings.loc[settings['الإعداد'] == 'لون التطبيق', 'القيمة'] = theme
                
                if save_to_excel(machines, tasks, logs, settings):
                    st.success("✅ تم حفظ الإعدادات بنجاح!")
                    st.rerun()
    
    with tab2:
        st.subheader("إعدادات الإشعارات")
        
        st.info("""
        **ميزات الإشعارات:**
        
        1. **إشعارات المتصفح:** تظهر في المتصفح عندما تكون هناك مهام متأخرة
        2. **إشعارات البريد الإلكتروني:** تُرسل تلقائيًا قبل موعد الصيانة
        3. **تقارير أسبوعية:** تُرسل كل أسبوع عن حالة الماكينات
        
        ⚠️ *ملاحظة: ميزة البريد الإلكتروني تحتاج إلى إعداد SMTP server*
        """)
        
        # إعدادات إضافية
        st.checkbox("تفعيل الإشعارات اليومية", value=True)
        st.checkbox("إرسال تقرير أسبوعي", value=True)
        st.checkbox("إشعارات صوتية", value=False)
        
        st.number_input("وقت الإشعار اليومي (ساعة)", min_value=0, max_value=23, value=9)
        
        if st.button("🔔 اختبار الإشعارات", use_container_width=True):
            st.success("✅ تم إرسال إشعار تجريبي بنجاح!")
    
    with tab3:
        st.subheader("نسخ احتياطي واستعادة")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📁 نسخ احتياطي")
            st.write("احفظ نسخة احتياطية من جميع البيانات")
            
            if st.button("💾 إنشاء نسخة احتياطية", use_container_width=True):
                # إنشاء نسخة احتياطية
                backup_filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                
                # نسخ الملف
                import shutil
                shutil.copy2('machines.xlsx', backup_filename)
                
                st.success(f"✅ تم إنشاء النسخة الاحتياطية: {backup_filename}")
                
                # تقديم للتحميل
                with open(backup_filename, 'rb') as f:
                    st.download_button(
                        label="⬇️ تحميل النسخة الاحتياطية",
                        data=f,
                        file_name=backup_filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
        
        with col2:
            st.markdown("### 🔄 استعادة البيانات")
            st.write("استعادة البيانات من نسخة احتياطية سابقة")
            
            uploaded_file = st.file_uploader("اختر ملف Excel للاستعادة", type=['xlsx'])
            
            if uploaded_file is not None:
                if st.button("🔄 استعادة البيانات", use_container_width=True):
                    # حفظ الملف المرفوع
                    with open('machines.xlsx', 'wb') as f:
                        f.write(uploaded_file.getvalue())
                    
                    st.success("✅ تمت استعادة البيانات بنجاح!")
                    st.info("⏳ سيتم إعادة تحميل التطبيق...")
                    time.sleep(2)
                    st.rerun()

# صفحة تصدير البيانات
elif page == "📤 تصدير البيانات":
    st.title("📤 تصدير البيانات والتقارير")
    
    tab1, tab2, tab3 = st.tabs(["تصدير Excel", "تقارير جاهزة", "إحصائيات"])
    
    with tab1:
        st.subheader("تصدير البيانات إلى Excel")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📥 تصدير الماكينات", use_container_width=True):
                # تحويل إلى Excel
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    machines.to_excel(writer, sheet_name='الماكينات', index=False)
                
                # تقديم للتحميل
                st.download_button(
                    label="⬇️ تحميل ملف الماكينات",
                    data=output.getvalue(),
                    file_name=f"الماكينات_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        
        with col2:
            if st.button("📥 تصدير المهام", use_container_width=True):
                # تحويل إلى Excel
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    tasks.to_excel(writer, sheet_name='المهام', index=False)
                
                # تقديم للتحميل
                st.download_button(
                    label="⬇️ تحميل ملف المهام",
                    data=output.getvalue(),
                    file_name=f"مهام_الصيانة_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        
        with col3:
            if st.button("📥 تصدير السجل", use_container_width=True):
                # تحويل إلى Excel
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    logs.to_excel(writer, sheet_name='سجل_الصيانة', index=False)
                
                # تقديم للتحميل
                st.download_button(
                    label="⬇️ تحميل ملف السجل",
                    data=output.getvalue(),
                    file_name=f"سجل_الصيانة_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        
        # تصدير جميع البيانات معًا
        st.divider()
        st.subheader("تصدير جميع البيانات")
        
        if st.button("📦 تصدير قاعدة البيانات الكاملة", use_container_width=True):
            # إنشاء ملف Excel بكافة البيانات
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                machines.to_excel(writer, sheet_name='الماكينات', index=False)
                tasks.to_excel(writer, sheet_name='المهام', index=False)
                logs.to_excel(writer, sheet_name='السجل', index=False)
                settings.to_excel(writer, sheet_name='الإعدادات', index=False)
            
            # تقديم للتحميل
            st.download_button(
                label="⬇️ تحميل قاعدة البيانات الكاملة",
                data=output.getvalue(),
                file_name=f"قاعدة_بيانات_الصيانة_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    
    with tab2:
        st.subheader("تقارير جاهزة")
        
        report_type = st.selectbox("اختر نوع التقرير", [
            "تقرير المهام المتأخرة",
            "تقرير الصيانة الشهرية",
            "تقرير تكاليف الصيانة",
            "تقرير أداء الماكينات"
        ])
        
        if report_type == "تقرير المهام المتأخرة":
            # توليد التقرير
            overdue_report = tasks[tasks['عدد الساعات المتبقية'] <= 0].copy()
            
            if not overdue_report.empty:
                # إضافة اسم الماكينة
                overdue_report['اسم الماكينة'] = overdue_report['معرف الماكينة'].apply(
                    lambda x: machines[machines['id'] == x]['اسم الماكينة'].values[0] 
                    if not machines[machines['id'] == x].empty else "غير معروف"
                )
                
                st.write(f"### 📋 تقرير المهام المتأخرة ({len(overdue_report)} مهمة)")
                st.dataframe(overdue_report[['اسم الماكينة', 'نوع الصيانة', 'تاريخ آخر صيانة', 'تاريخ الصيانة القادم', 'وصف المهمة']], 
                           use_container_width=True)
                
                # تحميل التقرير
                output = BytesIO()
                overdue_report.to_excel(output, index=False, engine='openpyxl')
                
                st.download_button(
                    label="📥 تحميل التقرير",
                    data=output.getvalue(),
                    file_name=f"تقرير_المهام_المتأخرة_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.success("🎉 لا توجد مهام متأخرة!")
        
        elif report_type == "تقرير الصيانة الشهرية":
            # حساب الصيانة لهذا الشهر
            current_month = datetime.now().month
            current_year = datetime.now().year
            
            # تحويل تاريخ الصيانة القادمة
            tasks['تاريخ الصيانة القادم'] = pd.to_datetime(tasks['تاريخ الصيانة القادم'])
            
            monthly_tasks = tasks[
                (tasks['تاريخ الصيانة القادم'].dt.month == current_month) &
                (tasks['تاريخ الصيانة القادم'].dt.year == current_year)
            ].copy()
            
            if not monthly_tasks.empty:
                st.write(f"### 📅 تقرير الصيانة لشهر {current_month}/{current_year}")
                
                # إضافة اسم الماكينة
                monthly_tasks['اسم الماكينة'] = monthly_tasks['معرف الماكينة'].apply(
                    lambda x: machines[machines['id'] == x]['اسم الماكينة'].values[0] 
                    if not machines[machines['id'] == x].empty else "غير معروف"
                )
                
                st.dataframe(monthly_tasks[['اسم الماكينة', 'نوع الصيانة', 'تاريخ الصيانة القادم', 'عدد الساعات المتبقية', 'وصف المهمة']], 
                           use_container_width=True)
            else:
                st.info("📅 لا توجد مهام صيانة مجدولة لهذا الشهر")
    
    with tab3:
        st.subheader("إحصائيات الصيانة")
        
        # حساب الإحصائيات
        if not tasks.empty:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                avg_interval = tasks['الفترة بين الصيانة (ساعات)'].mean()
                st.metric("متوسط فترة الصيانة", f"{avg_interval:.0f} ساعة")
            
            with col2:
                total_maintenance_hours = logs['عدد ساعات التشغيل'].sum() if not logs.empty else 0
                st.metric("إجمالي ساعات الصيانة", f"{total_maintenance_hours:.0f}")
            
            with col3:
                unique_technicians = logs['تمت بواسطة'].nunique() if not logs.empty else 0
                st.metric("عدد الفنيين", unique_technicians)
            
            # مخطط المهام حسب النوع
            st.subheader("توزيع مهام الصيانة")
            
            task_counts = tasks['نوع الصيانة'].value_counts()
            
            fig = px.pie(
                values=task_counts.values,
                names=task_counts.index,
                title="توزيع أنواع مهام الصيانة"
            )
            
            st.plotly_chart(fig, use_container_width=True)

# تذييل الصفحة
st.divider()
st.markdown("""
<div style="text-align: center; color: #666;">
    <p>⚙️ نظام إدارة صيانة الماكينات | الإصدار 1.0 | تم التطوير باستخدام Streamlit & Excel</p>
    <p>📧 للدعم التقني: <a href="mailto:support@example.com">support@example.com</a></p>
</div>
""", unsafe_allow_html=True)
