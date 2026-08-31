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
