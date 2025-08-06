from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .forms import AttendanceNoteForm # استورد الفورم إذا قمت بإنشائه
from django.conf import settings
import ipaddress
from user_agents import parse
from django.http import JsonResponse # لاستقبال وإرسال بيانات JSON
from django.views.decorators.csrf import csrf_exempt # مؤقتًا للاختبار، سيتم إزالته لاحقًا
from django.contrib.auth.models import User # لاسترجاع كائن المستخدم
import json # للتعامل مع JSON في الطلبات
import uuid
import platform
from django.db import transaction
from datetime import datetime, time, date, timedelta
from calendar import calendar
from .models import Employee, DailyAttendance, PermissionRequest, ApprovalStatus, DeviceProfile # تأكد من استيراد النماذج
from .forms import AttendanceNoteForm, PermissionRequestForm # تأكد من استيراد النموذج الخاص بالملاحظات
from account.models import Department, Employee
from .utils import send_approval_notification_email, send_next_approval_notification
from django.shortcuts import render, get_object_or_404
import calendar


def is_allowed_attendance_ip(request_ip):
    """
    تتحقق مما إذا كان IP الطلب موجودًا ضمن قائمة عناوين IP المسموح بها للحضور.
    """
    # إذا لم يتم تعريف الإعداد، اسمح بكل شيء (يمكن تغيير هذا السلوك للأمان)
    if not hasattr(settings, 'ALLOWED_ATTENDANCE_IPS'):
        return True 
    
    try:
        request_ip_obj = ipaddress.ip_address(request_ip)
        for allowed_ip_entry in settings.ALLOWED_ATTENDANCE_IPS:
            if '/' in allowed_ip_entry: # إذا كان نطاق IP (مثال: 192.168.1.0/24)
                if request_ip_obj in ipaddress.ip_network(allowed_ip_entry, strict=False):
                    return True
            else: # إذا كان IP فردي
                if request_ip_obj == ipaddress.ip_address(allowed_ip_entry):
                    return True
        return False
    except ValueError:
        return False # في حالة IP غير صالح

def get_client_ip(request):
    """
    محاولة الحصول على IP العميل الحقيقي، مع مراعاة الخوادم الوكيلة (proxies).
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # إذا كان هناك وكيل، فغالباً ما يكون الأول هو IP العميل الحقيقي
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
# --- نهاية دوال مساعدة لـ IP ---


# --- دالة مساعدة جديدة لتحليل User-Agent ---
def parse_user_agent(user_agent_string):
    """
    تحلل سلسلة User-Agent وتُرجع قاموسًا بالمعلومات المفصلة.
    """
    if not user_agent_string:
        return {
            'os': 'غير معروف',
            'browser': 'غير معروف',
            'device_type': 'غير معروف',
            'is_mobile': False,
            'is_tablet': False,
            'is_pc': False,
        }
    
    user_agent = parse(user_agent_string)
    
    # تحديد نوع الجهاز بشكل أكثر وضوحاً
    device_type = 'غير معروف'
    if user_agent.is_mobile:
        device_type = 'هاتف محمول'
    elif user_agent.is_tablet:
        device_type = 'جهاز لوحي'
    elif user_agent.is_pc:
        device_type = 'كمبيوتر مكتبي/محمول'
    elif user_agent.is_bot:
        device_type = 'روبوت/برنامج زحف'
    
    return {
        'os': user_agent.os.family + (f" {user_agent.os.version_string}" if user_agent.os.version_string else ''),
        'browser': user_agent.browser.family + (f" {user_agent.browser.version_string}" if user_agent.browser.version_string else ''),
        'device_type': device_type,
        'is_mobile': user_agent.is_mobile,
        'is_tablet': user_agent.is_tablet,
        'is_pc': user_agent.is_pc,
        'full_string': user_agent_string, # احتفظ بالسلسلة الكاملة إذا أردت عرضها
    }


@login_required
def attendance_dashboard(request):
    # employee = get_object_or_404(Employee, user=request.user)
    full_name = request.user.get_full_name().strip()
    name_parts = full_name.split(' ', 1)
    first_name = name_parts[0] if name_parts else 'مستخدم'
    last_name = name_parts[1] if len(name_parts) > 1 else 'بدون لقب'
    email = request.user.email or f'user{request.user.id}@example.com'

    employee, created = Employee.objects.get_or_create(
        user=request.user,
        defaults={
             'first_name': first_name,
             'last_name': last_name,
             'email': email,
         }
        )
    today = timezone.localdate()
    
    attendance_record = DailyAttendance.objects.filter(
        employee=employee,
        attendance_date=today
    ).first()

    # **الإصلاح الأول:** تحديد client_ip و is_allowed هنا
    client_ip = get_client_ip(request)
    is_allowed = is_allowed_attendance_ip(client_ip)

    current_user_agent_string = request.META.get('HTTP_USER_AGENT', '')
    parsed_user_agent_info = parse_user_agent(current_user_agent_string)


    selected_month = int(request.GET.get('month', today.month))
    selected_year = int(request.GET.get('year', today.year))

    # التأكد من أن الشهر والسنة ضمن نطاق معقول (اختياري لكن يفضل)
    if not (1 <= selected_month <= 12) or not (2000 <= selected_year <= today.year + 5): # يمكنك تعديل نطاق السنوات
        selected_month = today.month
        selected_year = today.year

    # تحديد بداية ونهاية الشهر المحدد
    num_days = calendar.monthrange(selected_year, selected_month)[1]
    start_date = date(selected_year, selected_month, 1)
    end_date = date(selected_year, selected_month, num_days)

    # جلب سجلات الحضور لهذا الشهر للموظف الحالي
    monthly_attendance_records = DailyAttendance.objects.filter(
        employee=employee,
        attendance_date__range=(start_date, end_date)
    ).order_by('attendance_date')

    # حساب المجاميع الشهرية
    total_working_hours_td = timedelta(0)
    total_late_duration_td = timedelta(0)
    total_overtime_duration_td = timedelta(0)

    # أوقات العمل القياسية (للحسابات) - يمكنك جعلها قابلة للتكوين في قاعدة البيانات
    standard_check_in_time = time(8, 0, 0) # 8:00 AM
    standard_check_out_time = time(16, 0, 0) # 4:00 PM (أو حسب ساعات العمل القياسية لديك)
    expected_work_duration = timedelta(hours=standard_check_out_time.hour - standard_check_in_time.hour,
                                       minutes=standard_check_out_time.minute - standard_check_in_time.minute)

    for record in monthly_attendance_records:
        if record.check_in_time and record.check_out_time:
            check_in_dt = datetime.combine(record.attendance_date, record.check_in_time)
            check_out_dt = datetime.combine(record.attendance_date, record.check_out_time)

            daily_work_duration = check_out_dt - check_in_dt
            total_working_hours_td += daily_work_duration

            # حساب الوقت الإضافي اليومي
            if daily_work_duration > expected_work_duration:
                total_overtime_duration_td += (daily_work_duration - expected_work_duration)

        if record.is_late and record.late_duration:
            total_late_duration_td += record.late_duration
    
    # تحويل مدد timedelta إلى تنسيق عشري للساعات
    total_working_hours_decimal = total_working_hours_td.total_seconds() / 3600 if total_working_hours_td else 0
    total_late_duration_decimal = total_late_duration_td.total_seconds() / 3600 if total_late_duration_td else 0
    total_overtime_duration_decimal = total_overtime_duration_td.total_seconds() / 3600 if total_overtime_duration_td else 0

    context = {
        'employee': employee,
        'today': today,
        'attendance_record': attendance_record,
        'form': AttendanceNoteForm(),
        'client_ip': client_ip,      # الآن client_ip معرّف
        'is_allowed_ip': is_allowed, # والآن is_allowed معرّف
        'parsed_user_agent': parsed_user_agent_info,




        'monthly_attendance_records': monthly_attendance_records, # السجلات التي سيتم عرضها
        'selected_month': selected_month,
        'selected_year': selected_year,
        'current_year': today.year, # لتعبئة قائمة السنوات
        'total_working_hours_decimal': round(total_working_hours_decimal, 2),
        'total_late_duration_decimal': round(total_late_duration_decimal, 2),
        'total_overtime_duration_decimal': round(total_overtime_duration_decimal, 2),


    }
    return render(request, 'hr/attendance_dashboard.html', context)

HOLIDAYS = [
    date(2025, 1, 1),
    date(2025, 4, 10),
    date(2025, 5, 1),
    # أضف تواريخ العطل الرسمية هنا
]
@login_required
def check_in(request):
    if request.method == 'POST':
        client_ip = get_client_ip(request)

        if not is_allowed_attendance_ip(client_ip):
            messages.error(request, 'لا يمكن تسجيل الدخول إلا من داخل شبكة المؤسسة. IP الخاص بك: ' + client_ip)
            return redirect('attendance_dashboard')
        today = timezone.localdate()

        
        # التحقق من الجمعة
        if today.weekday() == 4:
            messages.error(request, 'لا يمكن تسجيل الدخول يوم الجمعة.')
            return redirect('attendance_dashboard')
        if today.weekday() == 0:
            messages.error(request, 'لا يمكن تسجيل الدخول يوم االسبت.')
            return redirect('attendance_dashboard')

        employee = get_object_or_404(Employee, user=request.user)
        #today = timezone.localdate()
        current_time = timezone.localtime().time()
        start_time_allowed = time(8, 0, 0)
        end_time_allowed = time(21, 0, 0)
        attendance_record = DailyAttendance.objects.filter(
            employee=employee,
            attendance_date=today
        ).first()

        # التقاط User-Agent
        user_agent_string = request.META.get('HTTP_USER_AGENT', '')
        # now = datetime.now()
        # today_checkin_time = time(8, 0)  # 8:00 صباحًا

        if attendance_record and attendance_record.check_in_time:
            messages.warning(request, 'لقد قمت بتسجيل الدخول بالفعل لهذا اليوم.')
        elif not (start_time_allowed <= current_time <= end_time_allowed):
            # الشرط الجديد للتحقق من النطاق الزمني
            messages.warning(request, f'لا يمكن تسجيل الدخول إلا بين الساعة {start_time_allowed.strftime("%I:%M %p")} والساعة {end_time_allowed.strftime("%I:%M %p")}.')
        else:
            form = AttendanceNoteForm(request.POST)
            late_notes = form.data.get('late_notes', '')

            if attendance_record:
                attendance_record.check_in_time = current_time
                attendance_record.late_notes = late_notes
                attendance_record.user_agent = user_agent_string # حفظ User-Agent للدخول
                attendance_record.save()
            else:
                DailyAttendance.objects.create(
                    employee=employee,
                    attendance_date=today,
                    check_in_time=current_time,
                    late_notes=late_notes,
                    user_agent=user_agent_string # حفظ User-Agent للدخول
                )
            messages.success(request, f'تم تسجيل دخولك بنجاح في {current_time.strftime("%I:%M:%S %p")}.')
        return redirect('attendance_dashboard')
    else:
        messages.error(request, 'طريقة الطلب غير صالحة.')
        return redirect('attendance_dashboard')


@login_required
def check_out(request):
    if request.method == 'POST':
        client_ip = get_client_ip(request)
        #
        user_agent_string = request.META.get('HTTP_USER_AGENT', '') # <--- التقاط User-Agent

        # **التحقق من الجهاز المصرح به**
        # is_device_allowed, reason = is_authorized_device(request.user.employee_profile, client_ip, user_agent_string)
        # if not is_device_allowed:
        #     messages.error(request, f'لا يمكن تسجيل الخروج. {reason}')
        #     return redirect('attendance_dashboard')
        # #
        if not is_allowed_attendance_ip(client_ip):
            messages.error(request, 'لا يمكن تسجيل الخروج إلا من داخل شبكة المؤسسة. IP الخاص بك: ' + client_ip)
            return redirect('attendance_dashboard')

        employee = get_object_or_404(Employee, user=request.user)
        today = timezone.localdate()
        current_time = timezone.localtime().time()

        attendance_record = DailyAttendance.objects.filter(
            employee=employee,
            attendance_date=today
        ).first()

        # التقاط User-Agent للخروج أيضًا
        user_agent_string = request.META.get('HTTP_USER_AGENT', '')


        if not attendance_record or not attendance_record.check_in_time:
            messages.error(request, 'يجب عليك تسجيل الدخول أولاً قبل تسجيل الخروج.')
        elif attendance_record.check_out_time:
            messages.warning(request, 'لقد قمت بتسجيل الخروج بالفعل لهذا اليوم.')
        else:
            form = AttendanceNoteForm(request.POST)
            early_exit_notes = form.data.get('early_exit_notes', '')

            attendance_record.check_out_time = current_time
            if early_exit_notes:
                attendance_record.early_exit_notes = f"{attendance_record.early_exit_notes or ''}\n{early_exit_notes}"
            # **الإصلاح الثاني:** استخدام حقل user_agent الموجود، بدلًا من user_agent_out
            attendance_record.user_agent = user_agent_string 
            attendance_record.save()
            messages.success(request, f'تم تسجيل خروجك بنجاح في {current_time.strftime("%I:%M:%S %p")}.')
        return redirect('attendance_dashboard')
    else:
        messages.error(request, 'طريقة الطلب غير صالحة.')
        return redirect('attendance_dashboard')






@login_required
def attendance_history(request):
    employee = get_object_or_404(Employee, user=request.user)

    # تحديد الشهر والسنة الافتراضيين (الشهر والسنة الحاليين)
    today = timezone.localdate()
    selected_month = int(request.GET.get('month', today.month))
    selected_year = int(request.GET.get('year', today.year))

    # التأكد من أن الشهر والسنة ضمن نطاق معقول
    if not (1 <= selected_month <= 12) or not (2000 <= selected_year <= today.year + 1):
        selected_month = today.month
        selected_year = today.year

    # تحديد بداية ونهاية الشهر المحدد
    num_days = calendar.monthrange(selected_year, selected_month)[1]
    start_date = date(selected_year, selected_month, 1)
    end_date = date(selected_year, selected_month, num_days)

    # جلب سجلات الحضور لهذا الشهر
    # تأكد أن 'attendances' هو related_name في Foreign Key في نموذج DailyAttendance
    monthly_attendance_records = employee.attendances.filter(
        attendance_date__range=(start_date, end_date)
    ).order_by('attendance_date')

    # حساب المجاميع الشهرية
    total_working_hours_td = timedelta(0) # timedelta for total working hours
    total_late_duration_td = timedelta(0) # timedelta for total late duration
    total_overtime_duration_td = timedelta(0) # timedelta for total overtime

    # أوقات العمل القياسية (للحسابات)
    standard_check_in_time = time(8, 0, 0) # 8:00 AM
    standard_check_out_time = time(13, 0, 0) # 1:00 PM
    expected_work_duration = timedelta(hours=standard_check_out_time.hour - standard_check_in_time.hour,
                                       minutes=standard_check_out_time.minute - standard_check_in_time.minute)

    for record in monthly_attendance_records:
        # حساب إجمالي ساعات العمل لكل سجل
        if record.check_in_time and record.check_out_time:
            # دمج الوقت مع التاريخ لحساب timedelta بشكل صحيح
            check_in_dt = datetime.combine(record.attendance_date, record.check_in_time)
            check_out_dt = datetime.combine(record.attendance_date, record.check_out_time)
            
            daily_work_duration = check_out_dt - check_in_dt
            total_working_hours_td += daily_work_duration

            # حساب الوقت الإضافي اليومي
            if daily_work_duration > expected_work_duration:
                total_overtime_duration_td += (daily_work_duration - expected_work_duration)

        # إضافة مدة التأخير
        if record.is_late and record.late_duration:
            total_late_duration_td += record.late_duration
            
        # ملاحظة: المغادرة المبكرة لا تعتبر "تأخير إضافي" في المجاميع، بل هي حالة.
        # إذا كنت تريد احتسابها كخصم من ساعات العمل، يجب تعديل منطق total_working_hours_td.
        # للحصول على "غياب" في السجل، يجب أن يكون هناك سجل DailyAttendance بدون check_in_time.
        # هذا العرض لا يحسب أيام الغياب بشكل صريح، فقط يعرض السجلات الموجودة.

    # تحويل مدد timedelta إلى تنسيق عشري للساعات (أو أي تنسيق عرض تفضله)
    total_working_hours_decimal = total_working_hours_td.total_seconds() / 3600 if total_working_hours_td else 0
    total_late_duration_decimal = total_late_duration_td.total_seconds() / 3600 if total_late_duration_td else 0
    total_overtime_duration_decimal = total_overtime_duration_td.total_seconds() / 3600 if total_overtime_duration_td else 0

    # إعداد السياق (Context) للقالب
    context = {
        'employee': employee,
        'selected_month': selected_month,
        'selected_year': selected_year,
        'monthly_attendance_records': monthly_attendance_records,
        'total_working_hours_decimal': round(total_working_hours_decimal, 2),
        'total_late_duration_decimal': round(total_late_duration_decimal, 2),
        'total_overtime_duration_decimal': round(total_overtime_duration_decimal, 2),
        'current_year': today.year, # لتمرير السنة الحالية لمحدد السنة
    }

    return render(request, 'hr/attendance_dashboard.html', context)



@login_required
def request_permission_view(request):
    try:
        employee = request.user.employee # افترض أن كل مستخدم لديه كائن Employee مرتبط به
        print(type(employee))  
    except Employee.DoesNotExist:
        messages.error(request, "لم يتم ربط حسابك بملف موظف. يرجى الاتصال بمسؤول النظام.")
        return redirect('some_error_page') # يمكنك توجيههم لصفحة خطأ أو صفحة رئيسية

    if request.method == 'POST':
        form = PermissionRequestForm(request.POST, requesting_employee=employee)
        if form.is_valid():
            permission_request = form.save(commit=False)
            permission_request.employee = employee # ربط الطلب بالموظف الحالي
            permission_request.requester_name = f"{employee.user.first_name} {employee.user.last_name}"
            permission_request.save()

            messages.success(request, "تم تقديم طلب الإذن بنجاح!")
            
            # إرسال إشعار للمسؤول المباشر
            if employee.direct_manager and employee.direct_manager.user.email:
                send_approval_notification_email(
                    permission_request,
                    employee.direct_manager.user,
                    "المسؤول المباشر"
                )
                messages.info(request, f"تم إرسال إشعار للمسؤول المباشر: {employee.direct_manager.user.get_full_name()}.")
            else:
                messages.warning(request, "لا يوجد مسؤول مباشر محدد أو بريده الإلكتروني مفقود. يرجى الاتصال بالمسؤول.")
                # إذا لم يكن هناك مدير مباشر، ربما يتم تجاوز هذه المرحلة تلقائيًا أو يذهب للمرحلة التالية مباشرة؟
                # لغرض هذا المثال، سنفترض أنه يجب أن يكون هناك مدير مباشر أولاً.

            return redirect('permission_request_list') # صفحة لعرض طلبات الإذن الخاصة بالموظف
        else:
            messages.error(request, "حدث خطأ في تقديم الطلب. يرجى مراجعة الأخطاء.")
    else:
        form = PermissionRequestForm(requesting_employee=employee, initial={
            'request_date': timezone.now().date(),
            'start_time': time(1, 0), # وقت افتراضي
            'end_time': time(0, 0),   # وقت افتراضي
        })

    context = {
        'form': form,
        'employee': employee, # لتمرير معلومات الموظف للقالب
    }
    return render(request, 'hr/permission_request_form.html', context)


@login_required
def permission_request_list_view(request):
    try:
        employee = request.user.employee
    except Employee.DoesNotExist:
        messages.error(request, "لم يتم ربط حسابك بملف موظف. يرجى التواصل مع المسؤول.")
        return redirect('some_safe_url') # صفحة خطأ أو تسجيل خروج

    my_requests = PermissionRequest.objects.filter(employee=employee).order_by('-created_at')

    pending_approvals = []

    # 1. طلبات بانتظار موافقة المسؤول المباشر
    if employee.managed_employees.exists(): # إذا كان هذا الموظف هو مدير مباشر لأي موظف
        direct_manager_pending = PermissionRequest.objects.filter(
            employee__direct_manager=employee,
            direct_manager_status=ApprovalStatus.PENDING
        ).order_by('-created_at')
        pending_approvals.extend(list(direct_manager_pending))

    # 2. طلبات بانتظار موافقة مدير الإدارة
    if employee.is_department_manager and employee.department:
        department_manager_pending = PermissionRequest.objects.filter(
            employee__department=employee.department,
            direct_manager_status=ApprovalStatus.APPROVED,
            department_manager_status=ApprovalStatus.PENDING
        ).order_by('-created_at')
        # استبعاد الطلبات التي قد يكون الموظف الحالي وافق عليها بالفعل كمسؤول مباشر
        pending_approvals.extend(list(department_manager_pending.exclude(employee__direct_manager=employee)))

    # 3. طلبات بانتظار موافقة شؤون الموظفين
    if employee.is_hr_staff:
        hr_pending = PermissionRequest.objects.filter(
            direct_manager_status=ApprovalStatus.APPROVED,
            department_manager_status=ApprovalStatus.APPROVED,
            hr_status=ApprovalStatus.PENDING
        ).order_by('-created_at')
        pending_approvals.extend(list(hr_pending))

    context = {
        'my_requests': my_requests,
        'pending_approvals': sorted(list(set(pending_approvals)), key=lambda x: x.created_at, reverse=True), # إزالة التكرارات وفرزها
    }
    return render(request, 'hr/permission_request_list.html', context)

@login_required
def approve_permission_request(request, pk):
    permission_request = get_object_or_404(PermissionRequest, pk=pk)
    approver_employee = request.user.employee # المستخدم الذي يقوم بالموافقة

    # تحديد دور الموافق الحالي والتحقق من الصلاحيات بناءً على النموذج Employee
    is_direct_manager_for_this_request = (approver_employee == permission_request.employee.direct_manager)
    is_department_manager_for_this_request = (
        approver_employee.is_department_manager and
        approver_employee.department and
        approver_employee.department == permission_request.employee.department
    )
    is_hr_staff = approver_employee.is_hr_staff

    with transaction.atomic():
        if request.method == 'POST':
            action = request.POST.get('action') # 'approve' أو 'reject'
            notes = request.POST.get('notes', '')

            # منطق الموافقة المتسلسلة
            if is_direct_manager_for_this_request and permission_request.direct_manager_status == ApprovalStatus.PENDING:
                if action == 'approve':
                    permission_request.direct_manager_status = ApprovalStatus.APPROVED
                    permission_request.direct_manager_approved_at = timezone.now()
                    messages.success(request, "تمت الموافقة على طلب الإذن من قبل المسؤول المباشر.")
                    send_next_approval_notification(permission_request, "المسؤول المباشر")
                else: # reject
                    permission_request.direct_manager_status = ApprovalStatus.REJECTED
                    permission_request.direct_manager_approved_at = timezone.now()
                    messages.error(request, "تم رفض طلب الإذن من قبل المسؤول المباشر.")
                    send_approval_notification_email(
                        permission_request,
                        permission_request.employee.user,
                        "الموظف (تم الرفض)",
                        final_status=True,
                        notes=notes # تمرير الملاحظات
                    )
                permission_request.direct_manager_notes = notes
                permission_request.save()
                return redirect('permission_request_list')

            elif is_department_manager_for_this_request and permission_request.direct_manager_status == ApprovalStatus.APPROVED and permission_request.department_manager_status == ApprovalStatus.PENDING:
                if action == 'approve':
                    permission_request.department_manager_status = ApprovalStatus.APPROVED
                    permission_request.department_manager_approved_at = timezone.now()
                    messages.success(request, "تمت الموافقة على طلب الإذن من قبل مدير الإدارة.")
                    send_next_approval_notification(permission_request, "مدير الإدارة")
                else: # reject
                    permission_request.department_manager_status = ApprovalStatus.REJECTED
                    permission_request.department_manager_approved_at = timezone.now()
                    messages.error(request, "تم رفض طلب الإذن من قبل مدير الإدارة.")
                    send_approval_notification_email(
                        permission_request,
                        permission_request.employee.user,
                        "الموظف (تم الرفض)",
                        final_status=True,
                        notes=notes
                    )
                permission_request.department_manager_notes = notes
                permission_request.save()
                return redirect('permission_request_list')

            elif is_hr_staff and permission_request.direct_manager_status == ApprovalStatus.APPROVED and permission_request.department_manager_status == ApprovalStatus.APPROVED and permission_request.hr_status == ApprovalStatus.PENDING:
                if action == 'approve':
                    permission_request.hr_status = ApprovalStatus.APPROVED
                    permission_request.hr_approved_at = timezone.now()
                    messages.success(request, "تمت الموافقة النهائية على طلب الإذن من قبل شؤون الموظفين.")
                    send_approval_notification_email(
                        permission_request,
                        permission_request.employee.user,
                        "الموظف (تمت الموافقة النهائية)",
                        final_status=True
                    )
                else: # reject
                    permission_request.hr_status = ApprovalStatus.REJECTED
                    permission_request.hr_approved_at = timezone.now()
                    messages.error(request, "تم رفض طلب الإذن من قبل شؤون الموظفين.")
                    send_approval_notification_email(
                        permission_request,
                        permission_request.employee.user,
                        "الموظف (تم الرفض)",
                        final_status=True,
                        notes=notes
                    )
                permission_request.hr_notes = notes
                permission_request.save()
                return redirect('permission_request_list')
            else:
                messages.warning(request, "لا تملك صلاحية الموافقة على هذا الطلب في هذه المرحلة، أو تم التعامل مع الطلب بالفعل.")
                return redirect('permission_request_list')
        else:
            context = {
                'request_details': permission_request,
                'can_approve_direct_manager': is_direct_manager_for_this_request and permission_request.direct_manager_status == ApprovalStatus.PENDING,
                'can_approve_department_manager': is_department_manager_for_this_request and permission_request.direct_manager_status == ApprovalStatus.APPROVED and permission_request.department_manager_status == ApprovalStatus.PENDING,
                'can_approve_hr': is_hr_staff and permission_request.direct_manager_status == ApprovalStatus.APPROVED and permission_request.department_manager_status == ApprovalStatus.APPROVED and permission_request.hr_status == ApprovalStatus.PENDING,
            }
            return render(request, 'hr/permission_request_detail.html', context)

# def permission_request_detail_view(request, pk):
#     permission_request = get_object_or_404(PermissionRequest, pk=pk)
#     return render(request, 'hr/permission_request_detail.html', {
#         'permission_request': permission_request
#     })