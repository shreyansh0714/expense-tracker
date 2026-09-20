// main.js — students will add JavaScript here as features are built

(function () {
    const openBtn = document.getElementById("how-it-works-btn");
    const modal = document.getElementById("how-it-works-modal");
    if (!openBtn || !modal) return;

    const iframe = document.getElementById("how-it-works-iframe");
    const videoUrl = "https://www.youtube.com/embed/dQw4w9WgXcQ";

    function openModal() {
        iframe.src = videoUrl + "?autoplay=1";
        modal.hidden = false;
    }

    function closeModal() {
        modal.hidden = true;
        iframe.src = ""; // stop playback
    }

    openBtn.addEventListener("click", openModal);
    modal.querySelectorAll("[data-modal-close]").forEach(function (el) {
        el.addEventListener("click", closeModal);
    });
})();

// Auto-dismiss flashed toasts
(function () {
    var toasts = document.querySelectorAll(".toast");
    toasts.forEach(function (toast) {
        setTimeout(function () {
            toast.classList.add("is-hiding");
            setTimeout(function () {
                toast.remove();
            }, 300);
        }, 4000);
    });
})();

// Profile: edit-profile modal, opened from the header edit button
(function () {
    var openBtn = document.getElementById("open-edit-profile");
    var modal = document.getElementById("edit-profile-modal");
    if (!openBtn || !modal) return;

    var content = modal.querySelector(".modal-content");
    var ANIMATION_MS = 420;

    function openModal() {
        modal.hidden = false;
        if (content) {
            content.classList.remove("opening");
            void content.offsetWidth; // force reflow so the animation replays every open
            content.classList.add("opening");
            setTimeout(function () {
                content.classList.remove("opening");
            }, ANIMATION_MS);
        }
    }

    function closeModal() {
        modal.hidden = true;
    }

    openBtn.addEventListener("click", openModal);
    modal.querySelectorAll("[data-modal-close]").forEach(function (el) {
        el.addEventListener("click", closeModal);
    });
})();

// Profile: verification-code popup for email changes
(function () {
    var form = document.getElementById("profile-form");
    var emailInput = document.getElementById("email");
    var modal = document.getElementById("verification-modal");
    if (!form || !emailInput || !modal) return;

    var codeInput = document.getElementById("verification-code-input");
    var hiddenCode = document.getElementById("verification_code");
    var confirmBtn = document.getElementById("verification-confirm-btn");
    var verified = false;

    function openModal() {
        modal.hidden = false;
        codeInput.value = "";
        codeInput.focus();
    }

    function closeModal() {
        modal.hidden = true;
    }

    form.addEventListener("submit", function (e) {
        var emailChanged = emailInput.value !== emailInput.dataset.originalEmail;
        if (emailChanged && !verified) {
            e.preventDefault();
            openModal();
        }
    });

    confirmBtn.addEventListener("click", function () {
        hiddenCode.value = codeInput.value;
        verified = true;
        closeModal();
        form.submit();
    });

    modal.querySelectorAll("[data-modal-close]").forEach(function (el) {
        el.addEventListener("click", closeModal);
    });
})();

// Profile: open the date filter's calendar when anywhere on a From/To box is clicked
// (by default Chrome only opens it from the small calendar icon)
(function () {
    var inputs = document.querySelectorAll('.date-filter-custom input[type="date"]');
    if (!inputs.length) return;

    inputs.forEach(function (input) {
        input.addEventListener("click", function () {
            if (typeof input.showPicker !== "function") return;
            try {
                input.showPicker();
            } catch (e) {
                // Picker already open or not allowed here: the icon still works
            }
        });
    });
})();
