from django.contrib import admin
from .models import DailyAttendance, DeviceProfile, PermissionRequest, ApprovalStatus
from account.models import Employee, Department
from django.utils.html import format_html
from django.urls import reverse
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
import logging
from django.shortcuts import redirect
from .utils import send_approval_notification_email, send_next_approval_notification # تأكد من استيرادها

logger = logging.getLogger(__name__)


# # لتسجيل نموذج Department
# @admin.register(Department)
# class DepartmentAdmin(admin.ModelAdmin):
#     list_display = ('name',)
#     search_fields = ('name',)

# قم بتسجيل نموذج الموظف إذا لم تكن قد فعلت ذلك
@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['user', 'get_first_name', 'get_last_name', 'get_email', 'employee_id', 'department', 'position', 'direct_manager']
    list_filter = ('department', 'position')
    search_fields = ('user__first_name', 'user__last_name', 'employee_id', 'position')
    raw_id_fields = ('user', 'direct_manager')

  
    def get_first_name(self, obj):
        return obj.user.first_name
    get_first_name.short_description = 'الاسم الأول'

    def get_last_name(self, obj):
        return obj.user.last_name
    get_last_name.short_description = 'اسم العائلة'

    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = 'البريد الإلكتروني'
    
    fieldsets = (
        (None, {
            'fields': ('user', 'employee_id', 'position', 'department', 'direct_manager')
        }),
    )
@admin.register(DailyAttendance)
class DailyAttendanceAdmin(admin.ModelAdmin):
    list_display = ('employee', 'attendance_date', 'check_in_time', 'check_out_time', 'is_late', 'is_early_departure', 'user_agent', 'late_notes', 'early_exit_notes')
    list_filter = ('attendance_date', 'is_late', 'is_early_departure') # تم إزالة 'employee__department__name'
    search_fields = ('employee__first_name', 'employee__last_name', 'user_agent')
    date_hierarchy = 'attendance_date' # لتنظيم العرض حسب التاريخ
    raw_id_fields = ('employee',)


# ... (استيراداتك ونماذج Admin الحالية) ...

@admin.register(DeviceProfile)
class DeviceProfileAdmin(admin.ModelAdmin):
    list_display = ('employee', 'node', 'system', 'device_id', 'is_active', 'last_seen')
    list_filter = ('system', 'is_active')
    search_fields = ('employee__first_name', 'employee__last_name', 'node', 'device_id')
    raw_id_fields = ('employee',)



# لتسجيل نموذج PermissionRequest في لوحة الإدارة
@admin.register(PermissionRequest)
class PermissionRequestAdmin(admin.ModelAdmin):
    list_display = (
        'employee_full_name', 'request_type', 'request_date', 'display_time_range',
        'direct_manager_status', 'department_manager_status', 'hr_status',
        'is_fully_approved', 'actions_column'
    )
    list_filter = (
        'request_type', 'direct_manager_status', 'department_manager_status',
        'hr_status', 'request_date'
    )
    search_fields = (
        'employee__user__first_name', 'employee__user__last_name',
        'employee__employee_id', 'reason', 'location'
    )

    readonly_fields = (
        'employee', 'request_date', 'request_day', 'start_time', 'end_time',
        'reason', 'location', 'requester_name', 'created_at', 'updated_at',
        # ملاحظات وتواريخ الموافقات يجب أن تكون للقراءة فقط هنا
        'direct_manager_status', 'direct_manager_approved_at', 'direct_manager_notes',
        'department_manager_status', 'department_manager_approved_at', 'department_manager_notes',
        'hr_status', 'hr_approved_at', 'hr_notes',
    )

    # حقول لصفحة التفاصيل
    fieldsets = (
        ('معلومات الطلب', {
            'fields': (
                'employee', 'request_type', 'request_date', 'request_day',
                'start_time', 'end_time', 'reason', 'location', 'requester_name'
            ),
        }),
        ('حالة موافقة المسؤول المباشر', {
            'fields': ('direct_manager_status', 'direct_manager_approved_at', 'direct_manager_notes'),
            'description': 'حالة الموافقة من قبل المسؤول المباشر للموظف.'
        }),
        ('حالة موافقة مدير الإدارة', {
            'fields': ('department_manager_status', 'department_manager_approved_at', 'department_manager_notes'),
            'description': 'حالة الموافقة من قبل مدير الإدارة للموظف.'
        }),
        ('حالة موافقة شؤون الموظفين', {
            'fields': ('hr_status', 'hr_approved_at', 'hr_notes'),
            'description': 'الحالة النهائية للموافقة من قبل شؤون الموظفين.'
        }),
        ('تواريخ الإنشاء والتعديل', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',), # لجعلها قابلة للطي
        }),
    )

    # دالة مساعدة لعرض الاسم الكامل للموظف
    @admin.display(description='الموظف')
    def employee_full_name(self, obj):
        return obj.employee.user.get_full_name() if obj.employee and obj.employee.user else 'N/A'

    # دالة مساعدة لعرض نطاق الوقت
    @admin.display(description='الوقت')
    def display_time_range(self, obj):
        return f"{obj.start_time.strftime('%H:%M')} - {obj.end_time.strftime('%H:%M')}"

    # عمود الإجراءات في قائمة الطلبات
    @admin.display(description='الإجراءات')
    def actions_column(self, obj):
        detail_url = reverse('admin:hr_permissionrequest_change', args=[obj.pk])
        return format_html(f'<a class="button" href="{detail_url}">مراجعة الطلب</a>')

        buttons = []
        if obj.direct_manager_status == ApprovalStatus.PENDING:
            buttons.append(f'<a class="button" href="{approve_url}?stage=direct_manager">موافقة (مسؤول مباشر)</a>')
            buttons.append(f'<a class="button" href="{reject_url}?stage=direct_manager">رفض (مسؤول مباشر)</a>')
        elif obj.direct_manager_status == ApprovalStatus.APPROVED and obj.department_manager_status == ApprovalStatus.PENDING:
            buttons.append(f'<a class="button" href="{approve_url}?stage=department_manager">موافقة (مدير إدارة)</a>')
            buttons.append(f'<a class="button" href="{reject_url}?stage=department_manager">رفض (مدير إدارة)</a>')
        elif obj.department_manager_status == ApprovalStatus.APPROVED and obj.hr_status == ApprovalStatus.PENDING:
            buttons.append(f'<a class="button" href="{approve_url}?stage=hr">موافقة (شؤون موظفين)</a>')
            buttons.append(f'<a class="button" href="{reject_url}?stage=hr">رفض (شؤون موظفين)</a>')
        
        return format_html(' '.join(buttons))
    
    # إضافة الأزرار إلى لوحة الإدارة (يتطلب CSS مخصصًا لجعلها تبدو كأزرار)
    actions_column.allow_tags = True

    # إضافة إجراءات مخصصة (Approval Actions)
    actions = ['approve_selected_requests', 'reject_selected_requests']

    def approve_selected_requests(self, request, queryset):
        updated_count = 0
        for obj in queryset:
            if obj.direct_manager_status == ApprovalStatus.PENDING:
                obj.direct_manager_status = ApprovalStatus.APPROVED
                obj.direct_manager_approved_at = timezone.now()
                obj.save()
                updated_count += 1
                messages.success(request, f"تمت الموافقة على {updated_count} طلبًا من المسؤول المباشر.")
        
        if updated_count > 0:
            self.message_user(request, f"تمت الموافقة على {updated_count} طلب إذن من قبل المسؤول المباشر.", messages.SUCCESS)
        else:
            self.message_user(request, "لم يتم العثور على طلبات معلقة للموافقة عليها كمسؤول مباشر.", messages.WARNING)

    approve_selected_requests.short_description = "الموافقة على الطلبات المحددة (المسؤول المباشر)"

    def reject_selected_requests(self, request, queryset):
        updated_count = 0
        for obj in queryset:
            if obj.direct_manager_status == ApprovalStatus.PENDING:
                obj.direct_manager_status = ApprovalStatus.REJECTED
                obj.direct_manager_approved_at = timezone.now()
                obj.save()
                updated_count += 1
        if updated_count > 0:
            self.message_user(request, f"تم رفض {updated_count} طلب إذن من قبل المسؤول المباشر.", messages.ERROR)
        else:
            self.message_user(request, "لم يتم العثور على طلبات معلقة للرفض كمسؤول مباشر.", messages.WARNING)
    reject_selected_requests.short_description = "رفض الطلبات المحددة (المسؤول المباشر)"



    @admin.display(description='الإجراءات')
    def actions_column(self, obj):
        detail_url = reverse('admin:hr_permissionrequest_change', args=[obj.pk])
        return format_html(f'<a class="button" href="{detail_url}">مراجعة الطلب</a>')

    actions = []

    # دالة لتغيير قالب التفاصيل (change_form) لإضافة حقول الملاحظات والتعامل مع الإجراءات
    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        permission_request = self.get_object(request, object_id)

        approver_employee = request.user.employee
        can_approve_direct_manager = (
            permission_request.direct_manager_status == ApprovalStatus.PENDING and
            approver_employee and
            approver_employee == permission_request.employee.direct_manager
        )
        can_approve_department_manager = (
            permission_request.direct_manager_status == ApprovalStatus.APPROVED and
            permission_request.department_manager_status == ApprovalStatus.PENDING and
            approver_employee and
            approver_employee.is_department_manager and
            approver_employee.department == permission_request.employee.department
        )
        can_approve_hr = (
            permission_request.direct_manager_status == ApprovalStatus.APPROVED and
            permission_request.department_manager_status == ApprovalStatus.APPROVED and
            permission_request.hr_status == ApprovalStatus.PENDING and
            approver_employee and
            approver_employee.is_hr_staff
        )
        
        extra_context['can_approve_direct_manager'] = can_approve_direct_manager
        extra_context['can_approve_department_manager'] = can_approve_department_manager
        extra_context['can_approve_hr'] = can_approve_hr
        
        # ... (نفس منطق معالجة POST للموافقة/الرفض)
        if request.method == 'POST' and ('_approve' in request.POST or '_reject' in request.POST):
            action = 'approve' if '_approve' in request.POST else 'reject'
            notes_field_name = ''
            status_field_name = ''
            approved_at_field_name = ''
            
            # تحديد المرحلة التي يتم معالجتها
            if can_approve_direct_manager:
                notes_field_name = 'direct_manager_notes'
                status_field_name = 'direct_manager_status'
                approved_at_field_name = 'direct_manager_approved_at'
                current_stage_name_for_notification = "المسؤول المباشر"
            elif can_approve_department_manager:
                notes_field_name = 'department_manager_notes'
                status_field_name = 'department_manager_status'
                approved_at_field_name = 'department_manager_approved_at'
                current_stage_name_for_notification = "مدير الإدارة"
            elif can_approve_hr:
                notes_field_name = 'hr_notes'
                status_field_name = 'hr_status'
                approved_at_field_name = 'hr_approved_at'
                current_stage_name_for_notification = "شؤون الموظفين"
            else:
                self.message_user(request, "لا تملك صلاحية الموافقة على هذا الطلب في هذه المرحلة.", messages.ERROR)
                return redirect(request.path)

            notes = request.POST.get('notes', '')

            try:
                with transaction.atomic():
                    setattr(permission_request, status_field_name, ApprovalStatus.APPROVED if action == 'approve' else ApprovalStatus.REJECTED)
                    setattr(permission_request, approved_at_field_name, timezone.now())
                    setattr(permission_request, notes_field_name, notes)
                    permission_request.save()

                    if action == 'approve':
                        self.message_user(request, f"تمت الموافقة على طلب الإذن بنجاح من {current_stage_name_for_notification}.", messages.SUCCESS)
                        if current_stage_name_for_notification in ["المسؤول المباشر", "مدير الإدارة"]:
                            send_next_approval_notification(permission_request, current_stage_name_for_notification)
                        elif current_stage_name_for_notification == "شؤون الموظفين":
                            send_approval_notification_email(
                                permission_request,
                                permission_request.employee.user,
                                "الموظف (تمت الموافقة النهائية)",
                                final_status=True
                            )
                    else: # Reject
                        self.message_user(request, f"تم رفض طلب الإذن بنجاح من {current_stage_name_for_notification}.", messages.ERROR)
                        send_approval_notification_email(
                            permission_request,
                            permission_request.employee.user,
                            "الموظف (تم الرفض)",
                            final_status=True,
                            notes=notes
                        )

            except Exception as e:
                logger.error(f"Error during approval/rejection from admin: {e}")
                self.message_user(request, f"حدث خطأ أثناء معالجة الطلب: {e}", messages.ERROR)

            return redirect('.') # إعادة توجيه لنفس الصفحة لتحديثها
        
        return super().change_view(request, object_id, form_url, extra_context=extra_context)

