(() => {
  const body = document.body;
  const lamp = document.getElementById("mode");
  if (lamp) {
    lamp.hidden = false;
    const updateLabel = () => {
      const dark = body.dataset.theme === "dark";
      lamp.setAttribute("aria-pressed", String(dark));
      lamp.setAttribute("aria-label", dark ? "Switch to light mode" : "Switch to dark mode");
    };
    updateLabel();
    lamp.addEventListener("click", () => {
      body.dataset.theme = body.dataset.theme === "dark" ? "light" : "dark";
      try { localStorage.setItem("theme", body.dataset.theme); } catch (_) {}
      updateLabel();
    });
  }

  const toggle = document.querySelector(".nav-toggle");
  const links = document.getElementById("nav-links");
  if (toggle && links) {
    toggle.hidden = false;
    body.classList.add("nav-enhanced");
    const closeMenu = () => toggle.setAttribute("aria-expanded", "false");
    toggle.addEventListener("click", () => {
      toggle.setAttribute("aria-expanded", String(toggle.getAttribute("aria-expanded") !== "true"));
    });
    links.addEventListener("click", (event) => { if (event.target.closest("a")) closeMenu(); });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && toggle.getAttribute("aria-expanded") === "true") {
        closeMenu();
        toggle.focus();
      }
    });
    document.addEventListener("click", (event) => { if (!event.target.closest(".site-nav")) closeMenu(); });
  }

  const toc = document.querySelector(".article-toc");
  const headings = document.querySelectorAll(".article-body h2[id]");
  if (toc && headings.length > 2) {
    const list = document.createElement("ul");
    headings.forEach((heading) => {
      const item = document.createElement("li");
      const link = document.createElement("a");
      link.href = "#" + heading.id;
      link.textContent = heading.textContent.trim();
      item.appendChild(link);
      list.appendChild(item);
    });
    toc.querySelector("nav").appendChild(list);
    toc.hidden = false;
  }

  document.querySelectorAll(".page-content pre").forEach((block) => {
    block.tabIndex = 0;
  });

  document.querySelectorAll(".page-content table").forEach((table) => {
    const region = document.createElement("div");
    region.className = "table-scroll";
    region.tabIndex = 0;
    region.setAttribute("role", "region");
    region.setAttribute("aria-label", document.documentElement.lang.startsWith("fr") ? "Tableau à défilement horizontal" : "Horizontally scrollable table");
    table.before(region);
    region.appendChild(table);
  });
})();
