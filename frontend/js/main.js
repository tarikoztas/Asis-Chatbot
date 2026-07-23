// Genel site scripti: navigasyonda aktif sayfayı vurgular.
document.addEventListener("DOMContentLoaded", () => {
  const current = window.location.pathname.replace(/\/$/, "") || "/index.html";
  document.querySelectorAll(".nav-links a").forEach((link) => {
    const href = link.getAttribute("href");
    if (
      href === current ||
      (current === "/index.html" && href === "/") ||
      (current === "" && href === "/")
    ) {
      link.classList.add("active");
    }
  });
});
