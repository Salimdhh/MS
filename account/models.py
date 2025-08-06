from django.db import models

# Create your models here.
from django.conf import settings
from django.contrib.auth.models import User # استيراد نموذج User الافتراضي

class Profile(models.Model):
    ROLE_CHOICES = [
        ('employee', 'موظف عام'),
        ('hr', 'موارد بشرية'),
        ('store_manager', 'مدير مخازن'),
        ('admin', 'إداري'),
        ('superadmin', 'مدير النظام'),
    ]
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    date_of_birth = models.DateField(blank=True, null=True)
    photo = models.ImageField(
        upload_to='users/%Y/%m/%d/',
        blank=True
    )
    def __str__(self):
        return f'Profile of {self.user.username}'
    
#----------------
# accounts/models.py
class Department(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="الإدارة")
    # manager = models.OneToOneField('Employee', on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_department', verbose_name="مدير هذه الإدارة")

    class Meta:
        verbose_name = "إدارة"
        verbose_name_plural = "إدارات"

    def __str__(self):
        return self.name

class Section(models.Model):
    name = models.CharField(max_length=100, verbose_name="القسم")
    department = models.ForeignKey('Department', on_delete=models.CASCADE, related_name='sections', verbose_name="الإدارة")

    class Meta:
        verbose_name = "قسم"
        verbose_name_plural = "أقسام"
        unique_together = ('name', 'department')  # لمنع تكرار القسم داخل نفس الإدارة

    def __str__(self):
        return f"{self.name} ({self.department.name})"


class Employee(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    # حقول إضافية للموظف
    employee_id = models.CharField(max_length=20, unique=True, verbose_name="الرقم الوظيفي")
    position = models.CharField(max_length=100, verbose_name="الوظيفة")
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="الإدارة")
    # يمكنك إضافة حقل لتحديد ما إذا كان هذا الموظف هو مدير إدارة
    is_department_manager = models.BooleanField(default=False, verbose_name="هل هو مدير إدارة؟")
    # يمكنك إضافة حقل لتحديد ما إذا كان هذا الموظف من شؤون الموظفين
    is_hr_staff = models.BooleanField(default=False, verbose_name="هل هو من شؤون الموظفين؟")
    direct_manager = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_employees', verbose_name="المسؤول المباشر")
    hire_date = models.DateField(verbose_name="تاريخ التعيين", null=True, blank=True)

    class Meta:
        verbose_name = "موظف"
        verbose_name_plural = "الموظفون"
        # صلاحيات مخصصة لنموذج الموظف إذا لزم الأمر
        permissions = [
            ("can_view_employee_details", "Can view employee details"),
            ("can_manage_employees", "Can manage all employee profiles"),
        ]

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}"    

    # دالة مساعدة للحصول على مدير الإدارة لهذا الموظف
    def get_department_manager(self):
        if self.department:
            # ابحث عن موظف في نفس القسم هو مدير إدارة
            # يمكن تحسين هذا البحث ليكون أكثر دقة (مثلا، إذا كان هناك حقل 'manager' في Department)
            return Employee.objects.filter(department=self.department, is_department_manager=True).first()
        return None

    # دالة مساعدة للحصول على موظفي شؤون الموظفين (يمكن أن يكونوا أكثر من واحد)
    @staticmethod
    def get_hr_staff():
        return Employee.objects.filter(is_hr_staff=True)

