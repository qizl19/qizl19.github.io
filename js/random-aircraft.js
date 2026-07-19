(() => {
  "use strict";

  function init() {
    const button = document.querySelector(".random-aircraft-button");
    if (!button || button.dataset.randomReady === "true") return;
    button.dataset.randomReady = "true";
    const status = document.querySelector(".random-aircraft-status");
    button.addEventListener("click", () => {
      let choices = [];
      try {
        choices = JSON.parse(button.dataset.aircraftChoices || "[]");
      } catch (_) {
        // The visible status below remains the non-JavaScript fallback.
      }
      if (!choices.length) {
        if (status) status.textContent = "暂时没有可随机选择的飞机文章。";
        return;
      }
      const random = globalThis.crypto?.getRandomValues
        ? globalThis.crypto.getRandomValues(new Uint32Array(1))[0] / 4294967296
        : Math.random();
      const selected = choices[Math.floor(random * choices.length)];
      if (status) status.textContent = `正在前往：${selected.title}`;
      window.location.assign(selected.url);
    });
  }

  init();
  document.addEventListener("pjax:complete", init);
})();
