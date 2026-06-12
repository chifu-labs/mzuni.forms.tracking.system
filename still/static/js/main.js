// ── NAV HELPERS ──
function toggleNav() {
    document.querySelector('.nav-links').classList.toggle('open');
}
function toggleUserMenu() {
    document.getElementById('userDropdown').classList.toggle('show');
}
document.addEventListener('click', function(e) {
    const menu = document.querySelector('.nav-user-menu');
    if (menu && !menu.contains(e.target)) {
        document.getElementById('userDropdown')?.classList.remove('show');
    }
});

// ── SIGNATURE CANVAS ──
let sigCanvas, sigCtx, drawing = false, lastX, lastY;

function initSignatureCanvas(canvasId) {
    sigCanvas = document.getElementById(canvasId);
    if (!sigCanvas) return;
    sigCtx = sigCanvas.getContext('2d');
    sigCtx.strokeStyle = '#000';
    sigCtx.lineWidth = 2;
    sigCtx.lineCap = 'round';

    const getPos = (e) => {
        const rect = sigCanvas.getBoundingClientRect();
        const scaleX = sigCanvas.width / rect.width;
        const scaleY = sigCanvas.height / rect.height;
        if (e.touches) {
            return { x: (e.touches[0].clientX - rect.left) * scaleX, y: (e.touches[0].clientY - rect.top) * scaleY };
        }
        return { x: (e.clientX - rect.left) * scaleX, y: (e.clientY - rect.top) * scaleY };
    };

    const start = (e) => { e.preventDefault(); drawing = true; const p = getPos(e); [lastX, lastY] = [p.x, p.y]; };
    const draw  = (e) => {
        if (!drawing) return; e.preventDefault();
        const p = getPos(e);
        sigCtx.beginPath();
        sigCtx.moveTo(lastX, lastY);
        sigCtx.lineTo(p.x, p.y);
        sigCtx.stroke();
        [lastX, lastY] = [p.x, p.y];
    };
    const stop  = () => { drawing = false; };

    sigCanvas.addEventListener('mousedown', start);
    sigCanvas.addEventListener('mousemove', draw);
    sigCanvas.addEventListener('mouseup', stop);
    sigCanvas.addEventListener('mouseleave', stop);
    sigCanvas.addEventListener('touchstart', start, { passive: false });
    sigCanvas.addEventListener('touchmove', draw, { passive: false });
    sigCanvas.addEventListener('touchend', stop);
}

function clearSignature(canvasId) {
    const canvas = document.getElementById(canvasId);
    if (canvas) canvas.getContext('2d').clearRect(0, 0, canvas.width, canvas.height);
}

function saveSignature(canvasId, inputId) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const data = canvas.toDataURL('image/png');
    const input = document.getElementById(inputId);
    if (input) input.value = data;
    return data;
}

// ── MODAL ──
function openModal(id) { document.getElementById(id)?.classList.add('show'); }
function closeModal(id) { document.getElementById(id)?.classList.remove('show'); }

// ── REJECT MODAL ──
function openRejectModal(subId) {
    document.getElementById('rejectSubId').value = subId;
    openModal('rejectModal');
}

// ── TABLE ROW ADDITION ──
function addTableRow(tbodyId) {
    const tbody = document.getElementById(tbodyId);
    if (!tbody) return;
    const row = tbody.rows[0].cloneNode(true);
    row.querySelectorAll('input').forEach(inp => { inp.value = ''; inp.removeAttribute('readonly'); });
    tbody.appendChild(row);
}

// ── PASSWORD TOGGLE ──
function togglePassword(inputId, btn) {
    const input = document.getElementById(inputId);
    if (!input) return;
    if (input.type === 'password') {
        input.type = 'text';
        btn.innerHTML = '<i class="fas fa-eye-slash"></i>';
    } else {
        input.type = 'password';
        btn.innerHTML = '<i class="fas fa-eye"></i>';
    }
}

// ── AUTO-DISMISS ALERTS ──
setTimeout(() => {
    document.querySelectorAll('.alert').forEach(a => {
        a.style.transition = 'opacity 0.5s';
        a.style.opacity = '0';
        setTimeout(() => a.remove(), 500);
    });
}, 5000);

// ── PRINT FORM ──
function printForm() { window.print(); }

// ── CONFIRM APPROVAL ──
function confirmApproval(formId) {
    if (confirm('Are you sure you want to approve this form? Your digital signature will be applied.')) {
        document.getElementById(formId).submit();
    }
}

// ── AUTO-FILL TODAY'S DATE ──
// Fills any empty date input that is not readonly with today's date
document.addEventListener('DOMContentLoaded', function () {
    const today = new Date().toISOString().split('T')[0];
    document.querySelectorAll('input[type="date"]:not([readonly])').forEach(function (inp) {
        if (!inp.value) {
            inp.value = today;
        }
    });
});
