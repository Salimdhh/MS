// Mock functions for Supabase interaction
// You will replace these with actual Django views or Supabase API calls
const createDefaultUser = async () => {
    return new Promise(resolve => {
        setTimeout(() => {
            console.log('Mock: Default user creation simulated.');
            resolve({ success: true });
        }, 1000);
    });
};

const login = async (email, password) => {
    // هذه الدالة سترسل طلب POST إلى Django View
    // ستحتاج إلى تغيير هذا ليتناسب مع Django Backend الخاص بك
    const response = await fetch('/login/', { // افترض أن نقطة النهاية هي /login/
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken') // لإرسال CSRF Token في طلبات POST
        },
        body: JSON.stringify({ email, password })
    });

    const data = await response.json();

    if (response.ok && data.success) {
        console.log('Login successful for', email);
        showToast('تم تسجيل الدخول بنجاح!', 'success');
        // قد ترغب في إعادة توجيه المستخدم هنا:
        // window.location.href = '/dashboard/';
        return { success: true };
    } else {
        console.log('Login failed for', email);
        showToast(data.message || 'فشل تسجيل الدخول.', 'error');
        throw new Error(data.message || 'Invalid credentials');
    }
};

// Helper function to get CSRF token for Django POST requests
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}


// DOM Elements
const emailInput = document.getElementById('email');
const passwordInput = document.getElementById('password');
const loginForm = document.getElementById('loginForm');
const loginButton = document.getElementById('loginButton');
const supabaseStatusAlert = document.getElementById('supabase-status-alert');
const defaultUserInfoAlert = document.getElementById('default-user-info-alert');

// State variables (mimicking React useState)
let creatingDefaultUser = false;
let defaultUserCreated = false;
let loading = false; // For login process
// هذه القيمة يجب أن تأتي من Django Context في مشروع حقيقي
// const isSupabaseConnected = !!'{{ VITE_SUPABASE_URL }}' && !!'{{ VITE_SUPABASE_ANON_KEY }}';
// في هذا المثال، سنفترض أنها متصلة لغرض العرض.
const isSupabaseConnected = true; // Simulating connection, set to false to test warning

// Icons as SVG strings
const alertCircleIcon = `<svg class="alert-icon" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <circle cx="12" cy="12" r="10"></circle>
    <line x1="12" y1="8" x2="12" y2="12"></line>
    <line x1="12" y1="16" x2="12.01" y2="16"></line>
</svg>`;

const infoIcon = `<svg class="alert-icon" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <circle cx="12" cy="12" r="10"></circle>
    <line x1="12" y1="16" x2="12" y2="12"></line>
    <line x1="12" y1="8" x2="12.01" y2="8"></line>
</svg>`;


// Functions to update UI based on state
function updateLoginButtonState() {
    loginButton.disabled = loading || !isSupabaseConnected || creatingDefaultUser;
    if (loading) {
        loginButton.textContent = 'جاري تسجيل الدخول...';
    } else if (creatingDefaultUser) {
        loginButton.textContent = 'جاري إعداد المستخدم الافتراضي...';
    } else {
        loginButton.textContent = 'دخول';
    }
}

function updateSupabaseStatusAlert() {
    if (!isSupabaseConnected) {
        supabaseStatusAlert.innerHTML = `
            <div class="alert-message alert-warning">
                ${alertCircleIcon}
                <div class="alert-content">
                    <p class="text-yellow-700 font-medium mb-1">يجب الاتصال بقاعدة البيانات</p>
                    <p class="text-yellow-600 text-sm">
                        يرجى النقر على زر "Connect to Supabase" في الأعلى لإعداد قاعدة البيانات قبل تسجيل الدخول.
                    </p>
                </div>
            </div>
        `;
    } else {
        supabaseStatusAlert.innerHTML = ''; // Clear if connected
    }
}

function updateDefaultUserInfoAlert() {
    if (isSupabaseConnected && defaultUserCreated) {
        defaultUserInfoAlert.innerHTML = `
            <div class="alert-message alert-info">
                ${infoIcon}
                <div class="alert-content">
                    <p class="text-blue-700 font-medium mb-1">بيانات تسجيل الدخول الافتراضية</p>
                    <p class="text-blue-600 text-sm">
                        البريد الإلكتروني: admin@example.com
                        <br />
                        كلمة المرور: admin123
                    </p>
                </div>
            </div>
        `;
    } else {
        defaultUserInfoAlert.innerHTML = ''; // Clear if not needed
    }
}

// Initial UI render
updateLoginButtonState();
updateSupabaseStatusAlert();
updateDefaultUserInfoAlert();

// Handle creating default user on page load
async function handleCreateDefaultUser() {
    if (isSupabaseConnected) {
        creatingDefaultUser = true;
        updateLoginButtonState();
        try {
            const result = await createDefaultUser();
            if (result.success) {
                defaultUserCreated = true;
                updateDefaultUserInfoAlert();
            }
        } catch (error) {
            console.error('خطأ غير متوقع في إنشاء المستخدم الافتراضي:', error);
            showToast('فشل في إنشاء المستخدم الافتراضي.', 'error');
        } finally {
            creatingDefaultUser = false;
            updateLoginButtonState();
        }
    }
}

// Call on page load (mimics useEffect)
handleCreateDefaultUser();

// Event Listener for form submission
loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    if (!isSupabaseConnected) {
        showToast('يرجى الاتصال بقاعدة البيانات أولاً باستخدام زر "Connect to Supabase"', 'error');
        return;
    }
    
    const email = emailInput.value;
    const password = passwordInput.value;

    if (!email || !password) {
        showToast('الرجاء إدخال البريد الإلكتروني وكلمة المرور', 'error');
        return;
    }
    
    loading = true;
    updateLoginButtonState();
    try {
        await login(email, password);
        // On successful login, you might redirect:
        // window.location.href = '/dashboard/';
    } catch (error) {
        // Error handling is done within the login function by showToast
    } finally {
        loading = false;
        updateLoginButtonState();
    }
});