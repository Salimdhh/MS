# hr/context_processors.py
from .models import PermissionRequest, Employee, ApprovalStatus

def pending_requests_count(request):
    count = 0
    if request.user.is_authenticated:
        try:
            employee = request.user.employee

            # 1. طلبات بانتظار موافقة المسؤول المباشر
            if employee.managed_employees.exists():
                count += PermissionRequest.objects.filter(
                    employee__direct_manager=employee,
                    direct_manager_status=ApprovalStatus.PENDING
                ).count()

            # 2. طلبات بانتظار موافقة مدير الإدارة
            if employee.is_department_manager and employee.department:
                count += PermissionRequest.objects.filter(
                    employee__department=employee.department,
                    direct_manager_status=ApprovalStatus.APPROVED,
                    department_manager_status=ApprovalStatus.PENDING
                ).exclude(employee__direct_manager=employee).count() # تجنب التكرار مع المدير المباشر

            # 3. طلبات بانتظار موافقة شؤون الموظفين
            if employee.is_hr_staff:
                count += PermissionRequest.objects.filter(
                    direct_manager_status=ApprovalStatus.APPROVED,
                    department_manager_status=ApprovalStatus.APPROVED,
                    hr_status=ApprovalStatus.PENDING
                ).count()

        except Employee.DoesNotExist:
            pass # المستخدم ليس موظفًا
    return {'pending_requests_count': count}