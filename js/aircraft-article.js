(() => {
  "use strict";

  const CHART_URL = "https://cdn.jsdelivr.net/npm/chart.js@4.5.1/dist/chart.umd.min.js";
  const MERMAID_URL = "https://cdn.jsdelivr.net/npm/mermaid@11.16.0/dist/mermaid.esm.min.mjs";
  const MODEL_VIEWER_URL = "https://cdn.jsdelivr.net/npm/@google/model-viewer@4.2.0/dist/model-viewer.min.js";
  const observers = new Set();
  const charts = new Set();
  let chartPromise;
  let mermaidPromise;
  let modelViewerPromise;
  let activeViewer = null;

  function statusOf(widget) {
    return widget.querySelector(".aircraft-widget-status");
  }

  function setStatus(widget, message, isError = false) {
    const status = statusOf(widget);
    if (!status) return;
    status.textContent = message;
    status.classList.toggle("is-error", isError);
  }

  function observeOnce(widget, callback) {
    if (!("IntersectionObserver" in window)) {
      callback();
      return;
    }
    const observer = new IntersectionObserver((entries) => {
      if (!entries.some((entry) => entry.isIntersecting)) return;
      observer.disconnect();
      observers.delete(observer);
      callback();
    }, { rootMargin: "280px 0px" });
    observers.add(observer);
    observer.observe(widget);
  }

  function loadClassicScript(url, globalName) {
    if (globalThis[globalName]) return Promise.resolve(globalThis[globalName]);
    const existing = document.querySelector(`script[data-aircraft-library="${globalName}"]`);
    if (existing) {
      return new Promise((resolve, reject) => {
        existing.addEventListener("load", () => resolve(globalThis[globalName]), { once: true });
        existing.addEventListener("error", reject, { once: true });
      });
    }
    return new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = url;
      script.async = true;
      script.dataset.aircraftLibrary = globalName;
      script.addEventListener("load", () => resolve(globalThis[globalName]), { once: true });
      script.addEventListener("error", () => reject(new Error(`${globalName} load failed`)), { once: true });
      document.head.append(script);
    });
  }

  function loadModelViewer() {
    if (customElements.get("model-viewer")) return Promise.resolve();
    if (!modelViewerPromise) {
      modelViewerPromise = new Promise((resolve, reject) => {
        const script = document.createElement("script");
        script.type = "module";
        script.src = MODEL_VIEWER_URL;
        script.dataset.aircraftLibrary = "model-viewer";
        script.addEventListener("load", () => customElements.whenDefined("model-viewer").then(resolve), { once: true });
        script.addEventListener("error", () => reject(new Error("model-viewer load failed")), { once: true });
        document.head.append(script);
      });
    }
    return modelViewerPromise;
  }

  function releaseViewer() {
    if (!activeViewer) return;
    activeViewer.removeAttribute("src");
    activeViewer.remove();
    activeViewer = null;
  }

  function initModel(widget) {
    if (widget.dataset.widgetInitialized === "true") return;
    widget.dataset.widgetInitialized = "true";
    const button = widget.querySelector(".aircraft-model-load");
    const host = widget.querySelector(".aircraft-model-host");
    const poster = widget.querySelector(".aircraft-model-poster");
    if (!button || !host || !poster) return;
    button.addEventListener("click", async () => {
      if (button.disabled) return;
      button.disabled = true;
      setStatus(widget, "正在加载三维查看器；模型文件将在查看器就绪后下载……");
      try {
        await loadModelViewer();
        releaseViewer();
        const viewer = document.createElement("model-viewer");
        viewer.src = button.dataset.modelSrc;
        viewer.alt = `${button.dataset.modelTitle}轻量三维外形示意`;
        viewer.setAttribute("camera-controls", "");
        viewer.setAttribute("touch-action", "pan-y");
        viewer.setAttribute("shadow-intensity", "0.8");
        viewer.setAttribute("environment-image", "neutral");
        viewer.setAttribute("loading", "eager");
        const mobile = matchMedia("(max-width: 768px)").matches;
        const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
        if (!mobile && !reduced) viewer.setAttribute("auto-rotate", "");
        viewer.addEventListener("load", () => setStatus(widget, "三维模型已加载。可拖动旋转、滚轮缩放；手机端默认不自动旋转。"), { once: true });
        viewer.addEventListener("error", () => {
          setStatus(widget, "模型加载失败，已保留静态预览和文字说明。", true);
          host.hidden = true;
          poster.hidden = false;
          button.disabled = false;
        }, { once: true });
        host.replaceChildren(viewer);
        host.hidden = false;
        poster.hidden = true;
        activeViewer = viewer;
      } catch (_) {
        setStatus(widget, "三维组件加载失败，已保留静态预览和文字说明。", true);
        button.disabled = false;
      }
    });
  }

  const comparisonRows = [
    ["首飞年份", "firstFlightYear", (value) => String(value)],
    ["长度", "lengthM", (value) => `${value} m`],
    ["翼展", "wingspanM", (value) => `${value} m`],
    ["最大起飞重量", "maxTakeoffWeightT", (value) => `${value} t`],
    ["速度公开口径", "speedLabel", (value) => value],
    ["航程公开口径", "rangeLabel", (value) => value],
  ];

  function initComparison(widget) {
    if (widget.dataset.widgetInitialized === "true") return;
    widget.dataset.widgetInitialized = "true";
    observeOnce(widget, async () => {
      try {
        const response = await fetch(widget.dataset.source, { credentials: "same-origin" });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const aircraft = await response.json();
        const selectA = widget.querySelector("[data-compare-a]");
        const selectB = widget.querySelector("[data-compare-b]");
        const body = widget.querySelector("[data-compare-body]");
        const heading = widget.querySelector("[data-compare-heading]");
        if (!selectA || !selectB || !body || !aircraft.length) throw new Error("comparison data incomplete");
        for (const select of [selectA, selectB]) {
          select.replaceChildren(...aircraft.map((item) => {
            const option = document.createElement("option");
            option.value = item.slug;
            option.textContent = item.name;
            return option;
          }));
        }
        const currentIndex = Math.max(0, aircraft.findIndex((item) => item.slug === widget.dataset.currentSlug));
        selectA.value = aircraft[currentIndex].slug;
        selectB.value = aircraft[(currentIndex + 1) % aircraft.length].slug;
        const render = () => {
          const first = aircraft.find((item) => item.slug === selectA.value);
          const second = aircraft.find((item) => item.slug === selectB.value);
          if (!first || !second) return;
          heading.textContent = second.name;
          body.replaceChildren(...comparisonRows.map(([label, key, format]) => {
            const row = document.createElement("tr");
            const head = document.createElement("th");
            const firstCell = document.createElement("td");
            const secondCell = document.createElement("td");
            head.textContent = label;
            firstCell.textContent = format(first[key]);
            secondCell.textContent = format(second[key]);
            row.append(head, firstCell, secondCell);
            return row;
          }));
          setStatus(widget, `正在比较 ${first.name} 与 ${second.name}；数据来自本站本地 JSON。`);
        };
        selectA.addEventListener("change", render);
        selectB.addEventListener("change", render);
        render();
      } catch (_) {
        setStatus(widget, "对比数据加载失败，已保留当前机型的普通参数表。", true);
      }
    });
  }

  function initChart(widget) {
    if (widget.dataset.widgetInitialized === "true") return;
    widget.dataset.widgetInitialized = "true";
    observeOnce(widget, async () => {
      try {
        chartPromise ||= loadClassicScript(CHART_URL, "Chart");
        const Chart = await chartPromise;
        const payload = JSON.parse(widget.dataset.chart);
        const canvas = widget.querySelector("canvas");
        const chart = new Chart(canvas, {
          type: "bar",
          data: {
            labels: payload.labels,
            datasets: [{
              label: "米",
              data: payload.values,
              backgroundColor: ["rgba(34, 166, 179, .72)", "rgba(69, 123, 157, .72)"],
              borderColor: ["#1697a5", "#386d98"],
              borderWidth: 1,
            }],
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: matchMedia("(prefers-reduced-motion: reduce)").matches ? false : { duration: 500 },
            plugins: { legend: { display: false }, title: { display: true, text: payload.title } },
            scales: { y: { beginAtZero: true, title: { display: true, text: "米" } } },
          },
        });
        charts.add(chart);
        widget.classList.add("is-rendered");
        setStatus(widget, "Chart.js 图表已按需加载；普通表格仍保留为可访问后备内容。");
      } catch (_) {
        setStatus(widget, "图表组件加载失败，已保留普通尺寸表格。", true);
      }
    });
  }

  function initMermaid(widget) {
    if (widget.dataset.widgetInitialized === "true") return;
    widget.dataset.widgetInitialized = "true";
    observeOnce(widget, async () => {
      try {
        mermaidPromise ||= import(MERMAID_URL).then((module) => module.default);
        const mermaid = await mermaidPromise;
        mermaid.initialize({ startOnLoad: false, securityLevel: "strict", theme: "neutral" });
        const source = widget.querySelector(".aircraft-mermaid-source")?.textContent || "";
        const output = widget.querySelector(".aircraft-mermaid-output");
        const id = `aircraft-mermaid-${Date.now()}-${Math.floor(Math.random() * 1000)}`;
        const result = await mermaid.render(id, source);
        output.innerHTML = result.svg;
        result.bindFunctions?.(output);
        widget.classList.add("is-rendered");
        setStatus(widget, "Mermaid 工程关系图已在进入视口后渲染。文本链路仍作为后备内容保留。 ");
      } catch (_) {
        setStatus(widget, "工程图组件加载失败，已保留可阅读的文字链路。", true);
      }
    });
  }

  function cleanup() {
    observers.forEach((observer) => observer.disconnect());
    observers.clear();
    charts.forEach((chart) => chart.destroy());
    charts.clear();
    releaseViewer();
  }

  function init() {
    document.querySelectorAll("[data-aircraft-model]").forEach(initModel);
    document.querySelectorAll("[data-aircraft-comparison]").forEach(initComparison);
    document.querySelectorAll("[data-aircraft-chart]").forEach(initChart);
    document.querySelectorAll("[data-aircraft-mermaid]").forEach(initMermaid);
  }

  init();
  document.addEventListener("pjax:complete", init);
  document.addEventListener("pjax:send", cleanup);
  window.addEventListener("pagehide", cleanup);
})();
