$(document).ajaxStart(function() {
    // Global setup for AJAX request spinner if needed
});

function showAlert(message, type = 'danger') {
    const color = type === 'success' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)';
    const icon = type === 'success' ? 'fa-circle-check' : 'fa-triangle-exclamation';
    const alertHtml = `
        <div class="alert alert-${type} alert-dismissible fade show border-0 glass-panel" role="alert" style="background: ${color}; color: #f8fafc;">
            <i class="fa-solid ${icon} me-2"></i> ${message}
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `;
    $('#alert-container').html(alertHtml);
}

function showRegistrationToast() {
    const toastElement = document.getElementById('registration-toast');
    if (!toastElement) {
        return;
    }

    if (window.bootstrap && typeof window.bootstrap.Toast !== 'undefined') {
        const toast = window.bootstrap.Toast.getOrCreateInstance(toastElement);
        toast.show();
    } else {
        showAlert('Account created successfully. Welcome aboard!', 'success');
    }
}

function updatePasswordHint() {
    const password = $('#register-password').val();
    const hint = $('#password-hint');

    if (!password) {
        hint.text('Use at least 8 characters with letters and numbers.').removeClass('text-success text-danger').addClass('text-secondary-dark');
        return;
    }

    const hasLetter = /[A-Za-z]/.test(password);
    const hasDigit = /\d/.test(password);
    const longEnough = password.length >= 8;

    if (longEnough && hasLetter && hasDigit) {
        hint.text('Strong password').removeClass('text-danger text-secondary-dark').addClass('text-success');
    } else {
        hint.text('Password should be at least 8 characters and include letters + numbers.').removeClass('text-success text-secondary-dark').addClass('text-danger');
    }
}

function switchPanel(panel) {
    if (panel === 'login') {
        $('#tab-login').addClass('active');
        $('#tab-register').removeClass('active');
        $('#login-panel').removeClass('d-none');
        $('#register-panel').addClass('d-none');
        $('#alert-container').empty();
    } else {
        $('#tab-register').addClass('active');
        $('#tab-login').removeClass('active');
        $('#register-panel').removeClass('d-none');
        $('#login-panel').addClass('d-none');
        $('#alert-container').empty();
    }
}

$(document).ready(function() {
    try {
        console.log('login.js: document ready');
        const badge = document.getElementById('js-health-badge');
        if (badge) { badge.textContent = 'JS: ready'; badge.classList.remove('bg-secondary'); badge.classList.add('bg-success'); }
    } catch (err) {
        console.error('login.js init error', err);
    }
    // Quick login presets autofill handler
    $('.demo-preset-btn').on('click', function() {
        const user = $(this).data('user');
        const pass = $(this).data('pass');

        $('#username').val(user);
        $('#password').val(pass);

        $('#username, #password').addClass('border-info');
        setTimeout(() => {
            $('#username, #password').removeClass('border-info');
        }, 800);
    });

    $('#tab-login').on('click', function() {
        switchPanel('login');
    });
    $('#tab-register').on('click', function() {
        switchPanel('register');
    });

    $('#register-password').on('input', updatePasswordHint);
    $('#register-confirm-password').on('input', function() {
        const password = $('#register-password').val();
        const confirmPassword = $('#register-confirm-password').val();
        const hint = $('#password-hint');
        if (confirmPassword && password !== confirmPassword) {
            hint.text('Passwords do not match.').removeClass('text-success text-secondary-dark').addClass('text-danger');
        } else {
            updatePasswordHint();
        }
    });

    $('#login-form').on('submit', function(e) {
        e.preventDefault();

        const username = $('#username').val().trim();
        const password = $('#password').val();
        const button = $(this).find('button[type="submit"]');
        const submitIcon = $('#login-icon');

        button.prop('disabled', true);
        submitIcon.removeClass('fa-arrow-right-to-bracket').addClass('fa-spinner fa-spin');
        $('#alert-container').empty();

        $.ajax({
            url: '/login',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                username: username,
                password: password
            }),
            success: function(response) {
                window.location.href = response.redirect;
            },
            error: function(xhr) {
                button.prop('disabled', false);
                submitIcon.removeClass('fa-spinner fa-spin').addClass('fa-arrow-right-to-bracket');
                const errorMessage = xhr.responseJSON?.message || 'Authentication failed. Please verify credentials.';
                showAlert(errorMessage, 'danger');
            }
        });
    });

    $('#register-form').on('submit', function(e) {
        e.preventDefault();

        const name = $('#register-name').val().trim();
        const email = $('#register-email').val().trim();
        const username = $('#register-username').val().trim();
        const password = $('#register-password').val();
        const confirmPassword = $('#register-confirm-password').val();
        const button = $(this).find('button[type="submit"]');
        const submitIcon = $('#register-icon');

        button.prop('disabled', true);
        submitIcon.removeClass('fa-user-plus').addClass('fa-spinner fa-spin');
        $('#alert-container').empty();

        $.ajax({
            url: '/register',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                name: name,
                email: email,
                username: username,
                password: password,
                confirm_password: confirmPassword
            }),
            success: function(response) {
                $('#register-form')[0].reset();
                showAlert('Account created successfully! Redirecting to storefront…', 'success');
                showRegistrationToast();
                setTimeout(() => {
                    window.location.href = response.redirect;
                }, 1400);
            },
            error: function(xhr) {
                button.prop('disabled', false);
                submitIcon.removeClass('fa-spinner fa-spin').addClass('fa-user-plus');
                const errorMessage = xhr.responseJSON?.message || 'Registration failed. Please review the form.';
                showAlert(errorMessage, 'danger');
            }
        });
    });

    switchPanel('login');
});
