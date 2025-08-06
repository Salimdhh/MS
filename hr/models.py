from django.db import models

# Create your models here.
from django.contrib.auth import get_user_model # لاستخدام نموذج المستخدم الافتراضي أو المخصص
from datetime import time, date, timedelta
from django.utils import timezone
from account.models import Employee

User = get_user_model() # الحصول على نموذج المستخدم الحالي في Django

class DailyAttendance(models.Model):
    employee = models.OneToOneField(Employee, on_delete=models.CASCADE, related_name='attendances', verbose_name="الموظف")
    attendance_date = models.DateField(verbose_name="التاريخ")
    check_in_time = models.TimeField(null=True, blank=True, verbose_name="وقت الدخول")
    check_out_time = models.TimeField(null=True, blank=True, verbose_name="وقت الخروج")
    is_late = models.BooleanField(default=False, verbose_name="تأخير دخول")
    is_early_departure = models.BooleanField(default=False, verbose_name="مغادرة مبكرة")
    late_duration = models.DurationField(null=True, blank=True, verbose_name="مدة التأخير")
    early_departure_duration = models.DurationField(null=True, blank=True, verbose_name="مدة المغادرة المبكرة")
    late_notes = models.TextField(blank=True, null=True, verbose_name="ملاحظات الحضور المتأخر")
    early_exit_notes = models.TextField(blank=True, null=True, verbose_name="ملاحظات الخروج المبكر")

    user_agent = models.CharField(max_length=255, blank=True, null=True, verbose_name="وكيل المستخدم")
    class Meta:
        unique_together = ('employee', 'attendance_date') # لضمان سجل حضور واحد لكل موظف في اليوم
        ordering = ['employee__user__last_name']
        verbose_name = "حضور يومي"
        verbose_name_plural = "الحضور اليومي"

    def __str__(self):
        return f"حضور {self.employee.user.first_name} في {self.attendance_date}"


    def save(self, *args, **kwargs):
        # افترض أن وقت الدخول القياسي هو 09:00:00 ووقت الخروج 17:00:00
        # standard_check_in = time(8, 0, 0)
        # standard_check_out = time(13, 0, 0)
        today_date = self.attendance_date # التاريخ من سجل الحضور
        standard_check_in_dt = timezone.datetime.combine(today_date, time(8, 0, 0))
        standard_check_out_dt = timezone.datetime.combine(today_date, time(13, 0, 0))

        self.is_late = False
        self.late_duration = None
        self.is_early_departure = False
        self.early_departure_duration = None


         # حساب التأخير
        if self.check_in_time:
            actual_check_in_dt = timezone.datetime.combine(today_date, self.check_in_time)
            if actual_check_in_dt > standard_check_in_dt:
                self.is_late = True
                self.late_duration = actual_check_in_dt - standard_check_in_dt
            else:
                self.is_late = False
                self.late_duration = timedelta(0) # أو None إذا كنت تفضل تخزينها فارغة

        # حساب المغادرة المبكرة
        # يجب أن يكون وقت الدخول مسجلاً ليتم حساب المغادرة المبكرة بشكل منطقي
        if self.check_out_time and self.check_in_time: # تأكد من وجود وقت خروج ودخول
            actual_check_out_dt = timezone.datetime.combine(today_date, self.check_out_time)
            if actual_check_out_dt < standard_check_out_dt:
                self.is_early_departure = True
                self.early_departure_duration = standard_check_out_dt - actual_check_out_dt
            else:
                self.is_early_departure = False
                self.early_departure_duration = timedelta(0) # أو None

        super().save(*args, **kwargs)


class DeviceProfile(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='device_profiles', verbose_name="الموظف")
    device_id = models.CharField(max_length=255, unique=True, verbose_name="معرّف الجهاز (MAC)") # uuid.getnode()
    system = models.CharField(max_length=100, verbose_name="نظام التشغيل")
    node = models.CharField(max_length=255, verbose_name="اسم الجهاز")
    release = models.CharField(max_length=100, verbose_name="إصدار النظام")
    version = models.CharField(max_length=255, blank=True, null=True, verbose_name="نسخة النظام")
    machine = models.CharField(max_length=100, verbose_name="نوع المعالج")
    processor = models.CharField(max_length=255, blank=True, null=True, verbose_name="المعالج")

    first_seen = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ أول ظهور")
    last_seen = models.DateTimeField(auto_now=True, verbose_name="آخر ظهور")
    is_active = models.BooleanField(default=True, verbose_name="نشط") # لتفعيل/تعطيل الجهاز0

    class Meta:
        verbose_name = "ملف تعريف الجهاز"
        verbose_name_plural = "ملفات تعريف الأجهزة"
        unique_together = ('employee', 'device_id') # كل موظف يمكن أن يكون لديه معرف جهاز واحد فريد

    def __str__(self):
        return f"{self.employee.first_name} {self.employee.last_name} - {self.node} ({self.system})"


# حالات الموافقة
class ApprovalStatus(models.TextChoices):
    PENDING = 'PENDING', 'معلق'
    APPROVED = 'APPROVED', 'تمت الموافقة'
    REJECTED = 'REJECTED', 'مرفوض'

# أنواع طلبات الإذن
class PermissionType(models.TextChoices):
    SPECIAL_PERMISSION = 'SPECIAL_PERMISSION', 'إذن خاص'
    BUSINESS_TRIP = 'BUSINESS_TRIP', 'مهمة عمل'

# نموذج طلب الإذن
class PermissionRequest(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, verbose_name="الموظف")
    request_type = models.CharField(
        max_length=20,
        choices=PermissionType.choices,
        default=PermissionType.SPECIAL_PERMISSION,
        verbose_name="نوع الطلب"
    )
    request_date = models.DateField(default=timezone.now, verbose_name="تاريخ الطلب")
    request_day = models.CharField(max_length=20, default='', verbose_name="اليوم") # يمكن حسابه تلقائيًا
    start_time = models.TimeField(verbose_name="الوقت من")
    end_time = models.TimeField(verbose_name="الوقت إلى")
    reason = models.TextField(verbose_name="البيان/السبب")
    location = models.CharField(max_length=255, blank=True, null=True, verbose_name="الموقع (لمهمة العمل)")
    requester_name = models.CharField(max_length=100, verbose_name="مقدم الطلب") # يمكن أن يكون هو نفسه الموظف
    
    # حالات الموافقة
    direct_manager_status = models.CharField(
        max_length=20,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.PENDING,
        verbose_name="حالة موافقة المسؤول المباشر"
    )
    direct_manager_approved_at = models.DateTimeField(null=True, blank=True)
    direct_manager_notes = models.TextField(blank=True, null=True, verbose_name="ملاحظات المسؤول المباشر")

    department_manager_status = models.CharField(
        max_length=20,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.PENDING,
        verbose_name="حالة موافقة مدير الإدارة"
    )
    department_manager_approved_at = models.DateTimeField(null=True, blank=True)
    department_manager_notes = models.TextField(blank=True, null=True, verbose_name="ملاحظات مدير الإدارة")

    hr_status = models.CharField(
        max_length=20,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.PENDING,
        verbose_name="حالة موافقة شؤون الموظفين"
    )
    hr_approved_at = models.DateTimeField(null=True, blank=True)
    hr_notes = models.TextField(blank=True, null=True, verbose_name="ملاحظات شؤون الموظفين")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "طلب إذن"
        verbose_name_plural = "طلبات الإذن"
        ordering = ['-created_at']

    def __str__(self):
        return f"طلب إذن لـ {self.employee.user.first_name} {self.employee.user.last_name} ({self.get_request_type_display()})"

    # خاصية لتحديد ما إذا كان الطلب قد تم الموافقة عليه بالكامل
    @property
    def is_fully_approved(self):
        return (self.direct_manager_status == ApprovalStatus.APPROVED and
                self.department_manager_status == ApprovalStatus.APPROVED and
                self.hr_status == ApprovalStatus.APPROVED)

    # خاصية لتحديد ما إذا كان الطلب قد تم رفضه في أي مرحلة
    @property
    def is_rejected_at_any_stage(self):
        return (self.direct_manager_status == ApprovalStatus.REJECTED or
                self.department_manager_status == ApprovalStatus.REJECTED or
                self.hr_status == ApprovalStatus.REJECTED)

    # دالة لحساب اليوم من التاريخ
    def save(self, *args, **kwargs):
        if self.request_date:
            days_of_week = ["الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]
            self.request_day = days_of_week[self.request_date.weekday()]
        super().save(*args, **kwargs)
