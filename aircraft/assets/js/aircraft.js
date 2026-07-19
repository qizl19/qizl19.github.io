(() => {
  const form = document.querySelector("#aircraft-filters");
  if (!form) return;

  const search = document.querySelector("#aircraft-search");
  const nation = document.querySelector("#nation-filter");
  const category = document.querySelector("#category-filter");
  const cards = [...document.querySelectorAll("[data-aircraft-card]")];
  const count = document.querySelector("#result-count");
  const empty = document.querySelector("#empty-state");

  const apply = () => {
    const term = search.value.trim().toLowerCase();
    let visible = 0;
    cards.forEach((card) => {
      const matches =
        (!term || card.dataset.search.includes(term)) &&
        (!nation.value || card.dataset.nation === nation.value) &&
        (!category.value || card.dataset.category === category.value);
      card.hidden = !matches;
      if (matches) visible += 1;
    });
    count.textContent = String(visible);
    empty.hidden = visible !== 0;
  };

  form.addEventListener("input", apply);
  form.addEventListener("reset", () => window.setTimeout(apply, 0));
})();
