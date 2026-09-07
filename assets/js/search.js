(() => {
  const input = document.getElementById("search-input");
  const status = document.getElementById("search-status");
  const results = Array.from(document.querySelectorAll(".search-result"));
  const normalize = (value) => value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
  const index = results.map((result) => normalize(result.dataset.search));
  input.disabled = false;
  const filter = () => {
    const terms = normalize(input.value.trim()).split(/\s+/).filter(Boolean);
    let count = 0;
    results.forEach((result, i) => {
      result.hidden = !terms.every((term) => index[i].includes(term));
      if (!result.hidden) count++;
    });
    status.textContent = count ? count + (count === 1 ? " article found." : " articles found.") : "No matching articles. Try a broader keyword.";
  };
  input.addEventListener("input", filter);
  filter();
})();
