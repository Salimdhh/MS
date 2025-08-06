from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.auth.forms import UserCreationForm, UserChangeForm # سنحتفظ بهما كمرجع، لكن لن نستخدمهما مباشرة هنا
from .models import Profile, Employee # تأكد من أن هذه النماذج موجودة في accounts/models.py


# احصل على نموذج المستخدم النشط، سواء كان Django's User أو مخصص
User = get_user_model()

# -----------------------------------------------------
# نماذج المصادقة (Authentication Forms)

class LoginForm(forms.Form):
    username = forms.CharField(
        label='اسم المستخدم',
        widget=forms.TextInput(attrs={'class': 'form-input-field', 'placeholder': 'أدخل اسم المستخدم'})
    )
    password = forms.CharField(
        label='كلمة المرور',
        widget=forms.PasswordInput(attrs={'class': 'form-input-field', 'placeholder': 'أدخل كلمة المرور'})
    )

class UserRegistrationForm(forms.ModelForm):
    """
    نموذج لتسجيل مستخدم جديد.
    هذا النموذج مخصص لعملية التسجيل الذاتي أو إنشاء حسابات بسيطة.
    """
    password = forms.CharField(
        label='كلمة المرور',
        widget=forms.PasswordInput(attrs={'class': 'form-input-field', 'placeholder': 'أدخل كلمة المرور'})
    )
    password2 = forms.CharField(
        label='إعادة كلمة المرور',
        widget=forms.PasswordInput(attrs={'class': 'form-input-field', 'placeholder': 'أعد إدخال كلمة المرور'})
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email'] # أضف last_name هنا
        labels = {
            'username': 'اسم المستخدم',
            'first_name': 'الاسم الأول',
            'last_name': 'الاسم الأخير', # أضف التسمية هنا
            'email': 'عنوان البريد الإلكتروني',
        }
        error_messages = {
            'username': {
                'unique': "اسم المستخدم هذا مستخدم بالفعل.",
            },
            'email': {
                'unique': "عنوان البريد الإلكتروني هذا مستخدم بالفعل.",
                'required': "عنوان البريد الإلكتروني مطلوب.",
                'invalid': "الرجاء إدخال عنوان بريد إلكتروني صالح.",
            },
        }
        widgets = { # إضافة ويدجت لتطبيق كلاسات Tailwind مبدئيًا
            'username': forms.TextInput(attrs={'class': 'form-input-field', 'placeholder': 'أدخل اسم المستخدم'}),
            'first_name': forms.TextInput(attrs={'class': 'form-input-field', 'placeholder': 'أدخل الاسم الأول'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input-field', 'placeholder': 'أدخل الاسم الأخير'}),
            'email': forms.EmailInput(attrs={'class': 'form-input-field', 'placeholder': 'أدخل عنوان البريد الإلكتروني'}),
        }

    def clean_username(self):
            username = self.cleaned_data['username']
            if User.objects.filter(username=username).exists():
                raise forms.ValidationError('اسم المستخدم موجود مسبقًا.')
            return username

    def clean_password2(self):
        cd = self.cleaned_data
        if cd['password'] and cd['password2'] and cd['password'] != cd['password2']: # تحقق من وجودهما
            raise forms.ValidationError("كلمة المرور غير متطابقة.")
        return cd['password2']

    def clean_email(self):
        data = self.cleaned_data['email']
        # تحقق مما إذا كان البريد الإلكتروني موجودًا بالفعل
        if User.objects.filter(email=data).exists():
            raise forms.ValidationError('هذا البريد الإلكتروني مستخدم بالفعل.')
        return data
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password2 = cleaned_data.get("password2")

        if password and password2 and password != password2:
            self.add_error('password2', 'كلمتا المرور غير متطابقتين.')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user

# -----------------------------------------------------
# نماذج تعديل المستخدمين (لصفحة ملفهم الشخصي)

class UserEditForm(forms.ModelForm):
    """
    نموذج لتعديل معلومات المستخدم الأساسية (من صفحة ملف المستخدم).
    """
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        labels = {
            'first_name': 'الاسم الأول',
            'last_name': 'الاسم الأخير',
            'email': 'البريد الإلكتروني',
        }
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-input-field'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input-field'}),
            'email': forms.EmailInput(attrs={'class': 'form-input-field'}),
        }

    def clean_email(self):
        data = self.cleaned_data['email']
        # استثناء المستخدم الحالي من البحث لمنع الخطأ إذا لم يغير بريده الإلكتروني
        qs = User.objects.exclude(id=self.instance.id).filter(email=data)
        if qs.exists():
            raise forms.ValidationError('هذا البريد الإلكتروني مستخدم بالفعل بواسطة حساب آخر.')
        return data

class ProfileEditForm(forms.ModelForm):
    """
    نموذج لتعديل معلومات الملف الشخصي الإضافية (مثل تاريخ الميلاد والصورة).
    """
    class Meta:
        model = Profile
        fields = ['date_of_birth', 'photo']
        labels = {
            'date_of_birth': 'تاريخ الميلاد',
            'photo': 'الصورة الشخصية',
        }
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date', 'class': 'form-input-field'}),
            'photo': forms.ClearableFileInput(attrs={'class': 'form-file-input'}), # ويدجت مناسب لرفع الملفات
        }

# -----------------------------------------------------
# نماذج لوحة إدارة المستخدمين (للمدراء)

class CustomUserCreationForm(UserCreationForm):
    """
    نموذج إنشاء مستخدم جديد للمدراء.
    يرث من UserCreationForm ويضيف حقولًا إضافية مع تخصيصات Tailwind.
    """
    email = forms.EmailField(
        label='البريد الإلكتروني',
        required=True, # جعل البريد الإلكتروني مطلوبًا عند الإنشاء
        widget=forms.EmailInput(attrs={'class': 'form-input-field', 'placeholder': 'أدخل عنوان البريد الإلكتروني'})
    )
    first_name = forms.CharField(
        label='الاسم الأول',
        max_length=150,
        required=False, # قد لا يكون مطلوبًا دائمًا عند الإنشاء
        widget=forms.TextInput(attrs={'class': 'form-input-field', 'placeholder': 'أدخل الاسم الأول'})
    )
    last_name = forms.CharField(
        label='الاسم الأخير',
        max_length=150,
        required=False, # قد لا يكون مطلوبًا دائمًا عند الإنشاء
        widget=forms.TextInput(attrs={'class': 'form-input-field', 'placeholder': 'أدخل الاسم الأخير'})
    )
    is_active = forms.BooleanField(
        label="حساب نشط",
        required=False,
        initial=True, # عادة ما يكون الحساب نشطًا افتراضيًا عند الإنشاء
        widget=forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5 text-blue-600'})
    )
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="المجموعات"
    )

    class Meta(UserCreationForm.Meta):
        model = User # تأكد أن هذا يشير إلى نموذج المستخدم الصحيح
        fields = ('username', 'email', 'first_name', 'last_name', 'is_active', 'groups') + UserCreationForm.Meta.fields # دمج الحقول

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # تخصيص widgets لـ password1 و password2 لنموذج UserCreationForm
        if 'password' in self.fields:
            self.fields['password'].widget.attrs.update({'class': 'form-input-field', 'placeholder': 'أدخل كلمة المرور'})
        if 'password2' in self.fields:
            self.fields['password2'].widget.attrs.update({'class': 'form-input-field', 'placeholder': 'أعد إدخال كلمة المرور'})
      
        # إضافة اتجاه النص RTL للحقول النصية
        for field_name, field in self.fields.items():
            if isinstance(field.widget, (forms.TextInput, forms.EmailInput, forms.PasswordInput, forms.PasswordInput, forms.Textarea)):
                field.widget.attrs['dir'] = 'rtl'

    def save(self, commit=True):
        user = super().save(commit=False)
        # UserCreationForm يتعامل مع تعيين كلمة المرور تلقائيًا، فقط تأكد من حفظ المجموعات
        if commit:
            user.save()
            self.save_m2m() # حفظ العلاقات Many-to-Many مثل المجموعات
        return user


class UserProfileEditForm(forms.ModelForm):
    """
    نموذج لتعديل ملفات تعريف المستخدمين بواسطة المدير.
    يسمح بتعديل جميع الحقول الأساسية، بما في ذلك المجموعات وحالة النشاط.
    """
    first_name = forms.CharField(max_length=150, required=False, label="الاسم الأول")
    last_name = forms.CharField(max_length=150, required=False, label="الاسم الأخير")
    email = forms.EmailField(required=False, label="البريد الإلكتروني")
    is_active = forms.BooleanField(required=False, label="حساب نشط")
    is_staff = forms.BooleanField(required=False, label="وصول للوحة الإدارة")

    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="المجموعات"
    )
    user_permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.all().order_by('content_type__app_label', 'codename'),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="الصلاحيات الفردية للمستخدم"
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'is_active', 'is_staff', 'groups', 'user_permissions')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-input-field'}),
            'first_name': forms.TextInput(attrs={'class': 'form-input-field'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input-field'}),
            'email': forms.EmailInput(attrs={'class': 'form-input-field'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5 text-blue-600'}),
            'is_staff': forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5 text-blue-600'}),
        }
        labels = {
            'username': 'اسم المستخدم',
            'first_name': 'الاسم الأول',
            'last_name': 'الاسم الأخير',
            'email': 'البريد الإلكتروني',
            'is_active': 'حساب نشط',
            'is_staff': 'وصول للوحة الإدارة',
        }


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # إضافة اتجاه النص RTL للحقول النصية
        for field_name, field in self.fields.items():
            if isinstance(field.widget, (forms.TextInput, forms.EmailInput)):
                field.widget.attrs['dir'] = 'rtl'
            # لا حاجة لتطبيق الكلاسات هنا لأننا عرفناها في widgets في Meta

        # تهيئة قيم المجموعات والصلاحيات عند تحميل النموذج
        if self.instance.pk:
            self.initial['groups'] = self.instance.groups.all()
            self.initial['user_permissions'] = self.instance.user_permissions.all()

    def clean_email(self):
        data = self.cleaned_data['email']
        # استثناء المستخدم الحالي من البحث لمنع الخطأ إذا لم يغير بريده الإلكتروني
        qs = User.objects.exclude(id=self.instance.id).filter(email=data)
        if qs.exists():
            raise forms.ValidationError('هذا البريد الإلكتروني مستخدم بالفعل بواسطة حساب آخر.')
        return data

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            # حفظ علاقات Many-to-Many بعد حفظ المستخدم
            if 'groups' in self.cleaned_data:
                user.groups.set(self.cleaned_data['groups'])
            if 'user_permissions' in self.cleaned_data:
                user.user_permissions.set(self.cleaned_data['user_permissions'])
            self.save_m2m() # هذا يحفظ علاقات Many-to-Many التي لم تتم معالجتها يدوياً
        return user


class EmployeeProfileEditForm(forms.ModelForm):
    """
    نموذج لتعديل معلومات الموظف الإضافية (مثل الرقم الوظيفي والقسم).
    """
    class Meta:
        model = Employee
        fields = ('employee_id', 'department', 'position', 'hire_date')
        labels = {
            'employee_id': "الرقم الوظيفي",
            'department': "الإدارة",
            'position': "المنصب",
            'hire_date': "تاريخ التعيين",
        }
        widgets = {
            'employee_id': forms.TextInput(attrs={'class': 'form-input-field', 'placeholder': 'أدخل الرقم الوظيفي'}),
            'department': forms.Select(attrs={'class': 'form-input-field', 'placeholder': 'أدخل الإدارة'}),
            'position': forms.TextInput(attrs={'class': 'form-input-field', 'placeholder': 'أدخل المنصب'}),
            'hire_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-input-field'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # إضافة اتجاه النص RTL للحقول النصية
        for field_name, field in self.fields.items():
            if isinstance(field.widget, (forms.TextInput, forms.Textarea)):
                field.widget.attrs['dir'] = 'rtl'


class AdminPasswordChangeForm(forms.Form):
    """
    نموذج لتغيير كلمة مرور المستخدم بواسطة المدير.
    """
    new_password1 = forms.CharField(
        label="كلمة المرور الجديدة",
        widget=forms.PasswordInput(attrs={'class': 'form-input-field', 'placeholder': 'أدخل كلمة المرور الجديدة', 'dir': 'rtl'})
    )
    new_password2 = forms.CharField(
        label="تأكيد كلمة المرور الجديدة",
        widget=forms.PasswordInput(attrs={'class': 'form-input-field', 'placeholder': 'أعد إدخال كلمة المرور الجديدة', 'dir': 'rtl'})
    )

    def clean(self):
        cleaned_data = super().clean()
        new_password1 = cleaned_data.get('new_password1')
        new_password2 = cleaned_data.get('new_password2')

        if new_password1 and new_password2 and new_password1 != new_password2:
            raise forms.ValidationError("كلمتا المرور غير متطابقتين.")
        return cleaned_data

# -----------------------------------------------------
# نموذج إدارة المجموعات

class GroupForm(forms.ModelForm):
    """
    نموذج لإنشاء وتعديل المجموعات وصلاحياتها.
    """
    permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.all().order_by('content_type__app_label', 'codename'),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="الصلاحيات المتاحة"
    )

    class Meta:
        model = Group
        fields = ('name', 'permissions')
        labels = {
            'name': 'اسم المجموعة',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input-field', 'placeholder': 'أدخل اسم المجموعة', 'dir': 'rtl'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # تهيئة الصلاحيات المحددة للمجموعة عند التعديل
        if self.instance.pk:
            self.initial['permissions'] = self.instance.permissions.all()

    def save(self, commit=True):
        group = super().save(commit=False)
        if commit:
            group.save()
        # حفظ الصلاحيات بعد حفظ المجموعة
        if group.pk:
            group.permissions.set(self.cleaned_data['permissions'])
            self.save_m2m() # مهم لحفظ العلاقات Many-to-Many
        return group