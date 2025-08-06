$(document).ready(function() {
    const addAccountModal = $('#addAccountModal');
    const openModalBtn = $('#openAddAccountModalBtn');
    const closeModalBtns = addAccountModal.find('.close-modal-btn');

    // فتح النافذة المنبثقة
    openModalBtn.on('click', function() {
        addAccountModal.addClass('active');
    });

    // إغلاق النافذة المنبثقة عند النقر على زر الإغلاق أو الإلغاء
    closeModalBtns.on('click', function() {
        addAccountModal.removeClass('active');
    });

    // إغلاق النافذة المنبثقة عند النقر خارج المحتوى
    $(window).on('click', function(event) {
        if ($(event.target).is(addAccountModal)) {
            addAccountModal.removeClass('active');
        }
    });

    // معالجة تقديم النموذج عبر AJAX
    $('#addAccountForm').on('submit', function(e) {
        e.preventDefault();

        var form = $(this);
        var url = form.attr('action');
        var method = form.attr('method');
        var formData = form.serialize();

        $.ajax({
            url: url,
            method: method,
            data: formData,
            success: function(response) {
                if (response.success) {
                    alert('تم إضافة الحساب بنجاح!');
                    addAccountModal.removeClass('active');
                    // هنا يمكن تحديث الجدول أو إعادة تحميل الصفحة:
                    // location.reload();
                } else {
                    // إزالة الأخطاء السابقة
                    form.find('.text-red-500').remove();

                    // عرض أخطاء الحقول
                    for (const [fieldName, errors] of Object.entries(response.errors)) {
                        const input = form.find(`[name="${fieldName}"]`);
                        errors.forEach(error => {
                            const errorEl = $(`<p class="text-red-500 text-xs mt-1 text-right">${error}</p>`);
                            input.after(errorEl);
                        });
                    }

                    // أخطاء غير مرتبطة بحقول معينة
                    if (response.errors['__all__']) {
                        alert("أخطاء عامة: " + response.errors['__all__'].join(', '));
                    }
                }
            },
            error: function(xhr, status, error) {
                alert('حدث خطأ أثناء الاتصال بالخادم: ' + error);
            }
        }); // <-- تم إغلاق $.ajax بشكل صحيح هنا
    });
});
