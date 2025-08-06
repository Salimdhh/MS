from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test, permission_required
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from django.contrib import messages
from django.contrib.auth.models import Group, Permission
from django.db.models import Q

from .forms import (
    LoginForm,
    UserRegistrationForm,
    UserEditForm,
    ProfileEditForm,
    UserProfileEditForm,
    CustomUserCreationForm,
    EmployeeProfileEditForm,
    AdminPasswordChangeForm,
    GroupForm
)
from .models import Profile, Employee
from django.conf import settings
# تأكد من أن send_mail مُكوّن بشكل صحيح في settings.py إذا كنت تستخدمه
from django.core.mail import send_mail

User = get_user_model() # احصل على نموذج المستخدم النشط


## عروض مصادقة المستخدم والحساب الأساسية

def user_login(request):
    """
    يتعامل مع تسجيل دخول المستخدمين.
    """
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            user = authenticate(
                request,
                username=cd['username'],
                password=cd['password']
            )
            if user is not None:
                if user.is_active:
                    login(request, user)
                    messages.success(request, 'تم تسجيل الدخول بنجاح. مرحباً بك!')
                    return redirect('home')
                else:
                    messages.error(request, 'الحساب غير نشط.')
            else:
                messages.error(request, 'اسم المستخدم أو كلمة المرور غير صحيحة.')
    else:
        form = LoginForm()
    return render(request, 'registration/login.html', {'form': form})

@login_required
def home(request):
    """
    عرض لوحة التحكم الرئيسية للمستخدم بعد تسجيل الدخول.
    """
    return render(request, 'account/home.html', {'section': 'home'})

def register(request):
    """
    يتعامل مع تسجيل المستخدمين العامين.
    إذا كنت تنشئ المستخدمين فقط عبر لوحة التحكم (المسؤول)، فقد لا تحتاج إلى هذا العرض.
    """
    if request.method == 'POST':
        user_form = UserRegistrationForm(request.POST)
        if user_form.is_valid():
            new_user = user_form.save(commit=False)
            new_user.set_password(user_form.cleaned_data['password'])
            new_user.save()

            # إنشاء ملف شخصي إذا لم يكن موجوداً
            Profile.objects.create(user=new_user)

            # إرسال بريد إلكتروني (تأكد من تكوين البريد الإلكتروني في settings.py)
            if new_user.email:
                try:
                    send_mail(
                        'مرحبًا بك في موقعنا',
                        'تم إنشاء حسابك بنجاح.',
                        settings.DEFAULT_FROM_EMAIL,
                        [new_user.email],
                        fail_silently=False,
                    )
                except Exception as e:
                    messages.warning(request, f"تم إنشاء الحساب، ولكن حدث خطأ في إرسال البريد الإلكتروني: {e}")

            messages.success(request, 'تم إنشاء حسابك بنجاح. يمكنك الآن تسجيل الدخول.')
            return render(request, 'account/register_done.html', {'new_user': new_user})
        else:
            # عرض الأخطاء في رسائل الفلاش
            for field, errors in user_form.errors.items():
                for error in errors:
                    messages.error(request, f"خطأ في حقل '{user_form[field].label}': {error}")
    else:
        user_form = UserRegistrationForm()
    return render(request, 'account/register.html', {'user_form': user_form})

@login_required
def edit(request):
    """
    يتعامل مع تعديل ملفات تعريف المستخدمين الشخصية (من قبل المستخدم نفسه).
    """
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        profile = Profile.objects.create(user=request.user)

    if request.method == 'POST':
        user_form = UserEditForm(instance=request.user, data=request.POST)
        profile_form = ProfileEditForm(instance=profile, data=request.POST, files=request.FILES)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'تم تحديث ملفك الشخصي بنجاح!')
            return redirect('edit')
        else:
            messages.error(request, 'حدث خطأ في تحديث البيانات. يرجى التحقق من الأخطاء.')
    else:
        user_form = UserEditForm(instance=request.user)
        profile_form = ProfileEditForm(instance=profile)
    return render(request, 'account/edit.html', {
        'user_form': user_form,
        'profile_form': profile_form
    })

## عروض لوحة إدارة المستخدمين والمجموعات (للمدراء)

# دالة مساعدة للتحقق من صلاحيات المسؤول/الإدارة
def is_admin_or_can_manage_users(user):
    """
    تتحقق مما إذا كان المستخدم مديراً فائقاً (superuser) أو لديه إذن تغيير المستخدمين
    أو إذن إدارة الموظفين.
    """
    return user.is_superuser or user.has_perm('auth.change_user') or user.has_perm('accounts.can_manage_employees')

@login_required
@user_passes_test(is_admin_or_can_manage_users, login_url='/accounts/login/')
def user_list(request):
    # ... (منطق البحث والفلترة كما هو)
    users = User.objects.all().order_by('username')
    groups = Group.objects.all()

    search_query = request.GET.get('q')
    status_filter = request.GET.get('status')
    group_filter = request.GET.get('group')

    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    if status_filter:
        if status_filter == 'active':
            users = users.filter(is_active=True)
        elif status_filter == 'inactive':
            users = users.filter(is_active=False)
    if group_filter:
        try:
            group_id = int(group_filter)
            users = users.filter(groups__id=group_id).distinct()
        except ValueError:
            pass

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        # إذا كان الطلب AJAX، أعد جزء جدول المستخدمين فقط
        html = render_to_string('user/user_table_body.html', {'users': users}, request=request)
        return HttpResponse(html)
    else:
        # للطلب الأولي (غير AJAX)، أعد الصفحة بالكامل (لم نعد نمرر add_user_form هنا)
        context = {
            'users': users,
            'groups': groups,
            # 'form': CustomUserCreationForm(), # لم نعد نحتاج لتمرير النموذج هنا
        }
        return render(request, 'user/user_list.html', context)


@login_required
@permission_required('auth.add_user', raise_exception=True)
def add_account(request):
    """
    يتعامل مع إضافة حساب مستخدم جديد بواسطة المسؤول.
    الآن مصمم للعمل مع صفحة منفصلة (طلبات GET و POST عادية).
    """
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'تم إضافة الحساب "{user.username}" بنجاح!')
            return redirect('user_list') # إعادة التوجيه إلى قائمة المستخدمين بعد النجاح
        else:
            # عرض الأخطاء في رسائل الفلاش
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"خطأ في حقل '{form[field].label}': {error}")
            # لا تزال تعرض النموذج بنفس الأخطاء إذا كان غير صالح
            return render(request, 'user/add_account_form.html', {'form': form, 'page_title': 'إضافة حساب جديد'})
    else:
        # عند طلب GET، اعرض نموذجاً فارغاً
        form = CustomUserCreationForm()
    return render(request, 'user/add_account_form.html', {'form': form, 'page_title': 'إضافة حساب جديد'})

@login_required
@user_passes_test(is_admin_or_can_manage_users, login_url='/accounts/login/')
def user_edit(request, user_id):
    """
    يتعامل مع تعديل معلومات المستخدم وملف تعريف الموظف بواسطة المسؤول.
    يتضمن أيضاً خيار تغيير كلمة مرور المستخدم.
    """
    user = get_object_or_404(User, pk=user_id)
    employee = None
    try:
        employee = user.employee # محاولة الحصول على كائن Employee المرتبط
    except Employee.DoesNotExist:
        pass # لا يوجد كائن موظف لهذا المستخدم

    if request.method == 'POST':
        user_form = UserProfileEditForm(request.POST, instance=user)
        # إذا لم يكن هناك كائن موظف، يمكن تهيئة نموذج فارغ
        employee_form = EmployeeProfileEditForm(request.POST, instance=employee)
        admin_password_form = AdminPasswordChangeForm(request.POST)

        # تحقق من صحة جميع النماذج التي سيتم حفظها
        is_user_form_valid = user_form.is_valid()
        is_employee_form_valid = employee_form.is_valid()
        is_password_form_valid = True # نفترض صحتها ما لم يتم إرسالها أو كانت غير صالحة

        if 'change_password_submit' in request.POST:
            is_password_form_valid = admin_password_form.is_valid()

        if is_user_form_valid and is_employee_form_valid and is_password_form_valid:
            user_form.save()
            # حفظ المجموعات والصلاحيات الفردية
            if 'groups' in user_form.cleaned_data:
                user.groups.set(user_form.cleaned_data['groups'])
            if 'user_permissions' in user_form.cleaned_data:
                user.user_permissions.set(user_form.cleaned_data['user_permissions'])

            if employee:
                employee_form.save()
            elif employee_form.has_changed(): # إذا تم ملء بيانات موظف جديدة لمستخدم لم يكن موظفاً
                new_employee = employee_form.save(commit=False)
                new_employee.user = user
                new_employee.save()

            if 'change_password_submit' in request.POST and is_password_form_valid:
                new_password = admin_password_form.cleaned_data['new_password1']
                user.set_password(new_password)
                user.save()
                messages.success(request, 'تم تحديث كلمة المرور بنجاح.')

            messages.success(request, f'تم تحديث بيانات المستخدم {user.username} بنجاح.')
            return redirect('user_list')
        else:
            # جمع الأخطاء من جميع النماذج وعرضها
            all_errors = {
                **user_form.errors.get_json_data(),
                **employee_form.errors.get_json_data(),
            }
            if 'change_password_submit' in request.POST:
                all_errors.update(admin_password_form.errors.get_json_data())

            for field, errors in all_errors.items():
                for error in errors:
                    messages.error(request, f"خطأ في حقل '{field}': {error['message']}")
            messages.error(request, 'حدث خطأ في تحديث البيانات. يرجى التحقق من الأخطاء.')

    else:
        user_form = UserProfileEditForm(instance=user)
        employee_form = EmployeeProfileEditForm(instance=employee)
        admin_password_form = AdminPasswordChangeForm()

    context = {
        'user_obj': user,
        'user_form': user_form,
        'employee_form': employee_form,
        'admin_password_form': admin_password_form,
    }
    return render(request, 'user/user_edit.html', context)

@login_required
@permission_required('auth.delete_user', raise_exception=True)
def user_delete(request, pk):
    """
    يتعامل مع حذف المستخدمين.
    """
    user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        user.delete()
        messages.success(request, f'تم حذف المستخدم {user.username} بنجاح.')
        return redirect('user_list')
    # إذا كان طلب GET، قم بعرض صفحة تأكيد الحذف بدلاً من إعادة التوجيه الفوري
    return render(request, 'user/user_confirm_delete.html', {'user_obj': user})

@login_required
@user_passes_test(is_admin_or_can_manage_users, login_url='/accounts/login/')
def group_list(request):
    """
    يعرض قائمة بجميع المجموعات.
    """
    groups = Group.objects.all().order_by('name')
    return render(request, 'user/group_list.html', {'groups': groups})

@login_required
@user_passes_test(is_admin_or_can_manage_users, login_url='/accounts/login/')
def group_create(request):
    """
    يتعامل مع إنشاء مجموعة جديدة.
    """
    if request.method == 'POST':
        form = GroupForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, f'تم إنشاء المجموعة "{form.cleaned_data["name"]}" بنجاح.')
            return redirect('group_list')
        else:
            messages.error(request, 'حدث خطأ في إنشاء المجموعة. يرجى التحقق من الأخطاء.')
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"خطأ في حقل '{form[field].label}': {error}")
    else:
        form = GroupForm()
    return render(request, 'user/group_form.html', {'form': form, 'page_title': 'إنشاء مجموعة جديدة'})

@login_required
@user_passes_test(is_admin_or_can_manage_users, login_url='/accounts/login/')
def group_edit(request, group_id):
    """
    يتعامل مع تعديل مجموعة موجودة.
    """
    group = get_object_or_404(Group, pk=group_id)
    if request.method == 'POST':
        form = GroupForm(request.POST, instance=group)
        if form.is_valid():
            form.save()
            messages.success(request, f'تم تحديث المجموعة "{group.name}" بنجاح.')
            return redirect('group_list')
        else:
            messages.error(request, 'حدث خطأ في تحديث المجموعة. يرجى التحقق من الأخطاء.')
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"خطأ في حقل '{form[field].label}': {error}")
    else:
        form = GroupForm(instance=group)
    return render(request, 'user/group_form.html', {'form': form, 'group': group, 'page_title': f'تعديل المجموعة: {group.name}'})

@login_required
@user_passes_test(is_admin_or_can_manage_users, login_url='/accounts/login/')
def group_delete(request, group_id):
    """
    يتعامل مع حذف مجموعة.
    """
    group = get_object_or_404(Group, pk=group_id)
    if request.method == 'POST':
        group.delete()
        messages.success(request, f'تم حذف المجموعة "{group.name}" بنجاح.')
        return redirect('group_list')
    return render(request, 'user/group_confirm_delete.html', {'group': group})