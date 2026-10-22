/**
 * Smart Student Management System (SSMS) - Main Client-Side Logic
 */

document.addEventListener('DOMContentLoaded', function () {
    // 1. Auto-dismiss flash alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(function (alert) {
        setTimeout(function () {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            bsAlert.close();
        }, 5000);
    });

    // 2. Marks Entry Real-Time Total & Grade Preview
    const markInputs = document.querySelectorAll('.mark-input');
    markInputs.forEach(input => {
        input.addEventListener('input', function () {
            const studentId = this.id.split('_')[1];
            const intInput = document.getElementById(`int_${studentId}`);
            const extInput = document.getElementById(`ext_${studentId}`);
            const totalCell = document.getElementById(`total_${studentId}`);

            if (intInput && extInput && totalCell) {
                const internal = parseFloat(intInput.value) || 0;
                const external = parseFloat(extInput.value) || 0;
                const total = (internal + external).toFixed(1);
                totalCell.textContent = total;
            }
        });
    });
});
