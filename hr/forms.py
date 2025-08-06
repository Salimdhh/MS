# hr/forms.py

from django import forms
from .models import DailyAttendance, PermissionRequest, PermissionType, ApprovalStatus
from account.models import Employee

import datetime

class AttendanceNoteForm(forms.ModelForm):
    class Meta:
        model = DailyAttendance
        fields = ['late_notes', 'early_exit_notes'] # فقط حقل الملاحظات

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['late_notes'].required = False # اجعل الملاحظات اختيارية
        self.fields['late_notes'].widget.attrs.update({
            'placeholder': 'أدخل أي ملاحظات هنا',
            'rows': '3',
            'style': 'resize: vertical; overflow-y: auto; max-height: 150px; margin-top:10px;',
            'class': 'from-control',
            'dir': 'rtl',
            })
        self.fields['early_exit_notes'].required = False # اجعل الملاحظات اختيارية
        self.fields['early_exit_notes'].widget.attrs.update({
            'placeholder': 'أدخل أي ملاحظات هنا',
            'rows': '3',
            'style': 'resize: vertical; overflow-y: auto; max-height: 150px; margin-top:10px;',
            'class': 'from-control',
            'dir': 'rtl',
            })



class PermissionRequestForm(forms.ModelForm):
    # حقول غير ظاهرة للمستخدم ولكن سيتم تعبئتها تلقائياً
    employee_name = forms.CharField(label="اسم الموظف", required=False, widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    employee_position = forms.CharField(label="الوظيفة", required=False, widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    employee_department = forms.CharField(label="الإدارة", required=False, widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    
    class Meta:
        model = PermissionRequest
        fields = [
            'request_type',
            'request_date',
            'start_time',
            'end_time',
            'reason',
            'location',
            # 'requester_name' # سيتم تعبئته تلقائياً
        ]
        widgets = {
            'request_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
            'start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-input'}),
            'end_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-input'}),
            'request_type': forms.Select(attrs={'class': 'form-select'}),
            'reason': forms.Textarea(attrs={'rows': 4, 'class': 'form-textarea'}),
            'location': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'يظهر فقط لمهمة العمل'}),
        }
        labels = {
            'request_type': 'نوع الطلب',
            'request_date': 'التاريخ',
            'start_time': 'الوقت من',
            'end_time': 'الوقت إلى',
            'reason': 'البيان/السبب',
            'location': 'الموقع',
        }

    def __init__(self, *args, **kwargs):
        self.requesting_employee = kwargs.pop('requesting_employee', None) # الموظف الذي يقدم الطلب
        super().__init__(*args, **kwargs)

        # تعبئة حقول الموظف إذا كان موجوداً
        if self.requesting_employee:
            self.fields['employee_name'].initial = f"{self.requesting_employee.user.first_name} {self.requesting_employee.user.last_name}"
            self.fields['employee_position'].initial = self.requesting_employee.position
            if self.requesting_employee.department:
                self.fields['employee_department'].initial = self.requesting_employee.department.name
            else:
                self.fields['employee_department'].initial = 'غير محدد'

        if self.initial.get('request_type') != PermissionType.BUSINESS_TRIP:
            self.fields['location'].widget.attrs['style'] = 'display:none;'

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        request_date = cleaned_data.get('request_date')
        
        # تحقق من أن تاريخ الطلب ليس في الماضي
        if request_date and request_date < datetime.date.today():
            self.add_error('request_date', "لا يمكن تقديم طلب إذن بتاريخ ماضي.")

        # تحقق من أن وقت الانتهاء بعد وقت البدء في نفس اليوم
        if start_time and end_time:
            if end_time <= start_time:
                self.add_error('end_time', "يجب أن يكون وقت الانتهاء بعد وقت البدء.")
        
        # التحقق من حقل الموقع إذا كان نوع الطلب مهمة عمل
        request_type = cleaned_data.get('request_type')
        location = cleaned_data.get('location')
        if request_type == PermissionType.BUSINESS_TRIP and not location:
            self.add_error('location', "الموقع مطلوب لمهمة العمل.")

        return cleaned_data
