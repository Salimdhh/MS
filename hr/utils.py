from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import logging

logger = logging.getLogger(__name__)

def send_approval_notification_email(permission_request, recipient_user, approver_role, final_status=False, notes=None):
    """
    يرسل إشعار بريد إلكتروني حول طلب الإذن إلى الموافق التالي أو الموظف.
    """
    if not recipient_user or not recipient_user.email:
        logger.warning(f"Failed to send email: Recipient user or email is missing for request {permission_request.id}.")
        return

    subject = ""
    template_name = ""
    
    context = {
        'permission_request': permission_request,
        'recipient_user': recipient_user,
        'approver_role': approver_role,
        'request_url': f"http://127.0.0.1:8000/hr/permission-requests/{permission_request.id}/detail/", # مسار لوحة الإدارة أو واجهة المستخدم
        'notes': notes, # ملاحظات الرفض/الموافقة
        'site_name': settings.SITE_NAME, # استخدم اسم الموقع من settings
    }
    
    if final_status:
        if permission_request.is_fully_approved:
            subject = f"تمت الموافقة النهائية على طلب الإذن الخاص بك - {permission_request.id}"
            template_name = 'hr/email/final_approval_email.html'
        else: # تم الرفض
            subject = f"تم رفض طلب الإذن الخاص بك - {permission_request.id}"
            template_name = 'hr/email/rejection_email.html'
    else:
        subject = f"طلب إذن جديد بانتظار موافقتك - رقم {permission_request.id}"
        template_name = 'hr/email/approval_notification_email.html'
        
    try:
        html_message = render_to_string(template_name, context)
        plain_message = strip_tags(html_message)

        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [recipient_user.email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Email sent to {recipient_user.email} (Role: {approver_role}) for request {permission_request.id}.")
    except Exception as e:
        logger.error(f"Failed to send email for request {permission_request.id} to {recipient_user.email}: {e}")

def send_next_approval_notification(permission_request, current_approver_stage_name):
    """
    يحدد من هو الموافق التالي ويرسل له إشعاراً بناءً على الهيكل الإداري.
    current_approver_stage_name يمكن أن يكون "المسؤول المباشر", "مدير الإدارة"
    """
    from .models import Employee, ApprovalStatus # استيراد النماذج هنا لتجنب Circular Import

    next_approver_user = None
    approver_role_for_email = ""
    
    # الموافقة من المسؤول المباشر تمت، الآن دور مدير الإدارة
    if current_approver_stage_name == "المسؤول المباشر" and permission_request.direct_manager_status == ApprovalStatus.APPROVED:
        # البحث عن مدير الإدارة للموظف الذي قدم الطلب
        department_manager_employee = permission_request.employee.get_department_manager()
        
        if department_manager_employee and department_manager_employee.user:
            next_approver_user = department_manager_employee.user
            approver_role_for_email = "مدير الإدارة"
            logger.info(f"Next approver for request {permission_request.id} is Department Manager: {next_approver_user.email}")
        else:
            logger.warning(f"No Department Manager found or user missing for employee's department {permission_request.employee.department.name} for request {permission_request.id}.")
            # إذا لم يوجد مدير إدارة، قد تنتقل مباشرة إلى شؤون الموظفين أو تبقى معلقة
            # لغرض هذا المثال، إذا لم يوجد مدير إدارة، نرسل إلى HR مباشرة
            hr_staff_members = Employee.get_hr_staff()
            if hr_staff_members.exists():
                next_approver_user = hr_staff_members.first().user # إرسال لأول موظف HR
                approver_role_for_email = "شؤون الموظفين"
                logger.info(f"No Dept Manager, sending to HR Staff: {next_approver_user.email} for request {permission_request.id}")


    # الموافقة من مدير الإدارة تمت، الآن دور شؤون الموظفين
    elif current_approver_stage_name == "مدير الإدارة" and permission_request.department_manager_status == ApprovalStatus.APPROVED:
        # البحث عن موظفي شؤون الموظفين
        hr_staff_members = Employee.get_hr_staff()
        
        if hr_staff_members.exists():
            next_approver_user = hr_staff_members.first().user # يمكن إرسالها لجميع موظفي الـ HR
            approver_role_for_email = "شؤون الموظفين"
            logger.info(f"Next approver for request {permission_request.id} is HR Staff: {next_approver_user.email}")
        else:
            logger.warning(f"No HR staff found for request {permission_request.id}.")

    if next_approver_user:
        send_approval_notification_email(permission_request, next_approver_user, approver_role_for_email)
    else:
        logger.info(f"No further approver in the chain for request {permission_request.id} after {current_approver_stage_name}.")