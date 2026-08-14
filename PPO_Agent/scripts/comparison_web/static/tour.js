// Floating step-by-step guided tour -- spotlights each section of the page
// in turn, reusing the .help-text already written under each heading so
// there is exactly one source of truth for the wording. No framework, no
// build step, matches the rest of this app. Auto-starts on every page load
// (not just the first visit) -- "Skip guide" only dismisses it for the
// current view, it does not suppress future auto-starts.

(function () {
  function buildSteps() {
    const els = Array.from(document.querySelectorAll("[data-tour-step]")).sort(
      (a, b) => Number(a.dataset.tourStep) - Number(b.dataset.tourStep)
    );
    return els.map((el) => {
      const helpEl = el.querySelector(".help-text");
      return {
        el,
        title: el.dataset.tourTitle || "",
        text: helpEl ? helpEl.textContent.trim() : "",
      };
    });
  }

  let steps = [];
  let current = 0;
  let active = false;

  const highlight = document.createElement("div");
  highlight.className = "tour-highlight";

  const tooltip = document.createElement("div");
  tooltip.className = "tour-tooltip";
  tooltip.innerHTML =
    '<div class="tour-step-count"></div>' +
    '<h3 class="tour-title"></h3>' +
    '<p class="tour-text"></p>' +
    '<div class="tour-controls">' +
    '<button class="btn btn-small tour-skip">Skip guide</button>' +
    '<div class="tour-nav">' +
    '<button class="btn btn-small tour-prev">Previous</button>' +
    '<button class="btn btn-primary btn-small tour-next">Next</button>' +
    "</div>" +
    "</div>";

  const stepCountEl = tooltip.querySelector(".tour-step-count");
  const titleEl = tooltip.querySelector(".tour-title");
  const textEl = tooltip.querySelector(".tour-text");
  const prevBtn = tooltip.querySelector(".tour-prev");
  const nextBtn = tooltip.querySelector(".tour-next");
  const skipBtn = tooltip.querySelector(".tour-skip");

  function position() {
    const step = steps[current];
    if (!step) return;
    const rect = step.el.getBoundingClientRect();
    const pad = 8;
    highlight.style.top = rect.top - pad + "px";
    highlight.style.left = rect.left - pad + "px";
    highlight.style.width = rect.width + pad * 2 + "px";
    highlight.style.height = rect.height + pad * 2 + "px";

    const tooltipHeight = tooltip.offsetHeight || 180;
    const tooltipWidth = tooltip.offsetWidth || 360;
    let top = rect.bottom + pad + 12;
    if (top + tooltipHeight > window.innerHeight - 12) {
      top = Math.max(12, rect.top - pad - tooltipHeight - 12);
    }
    let left = Math.min(rect.left, window.innerWidth - tooltipWidth - 12);
    left = Math.max(12, left);
    tooltip.style.top = top + "px";
    tooltip.style.left = left + "px";
  }

  function showStep(n) {
    current = Math.max(0, Math.min(n, steps.length - 1));
    const step = steps[current];
    stepCountEl.textContent = "Step " + (current + 1) + " of " + steps.length;
    titleEl.textContent = step.title;
    textEl.textContent = step.text;
    prevBtn.disabled = current === 0;
    nextBtn.textContent = current === steps.length - 1 ? "Done" : "Next";
    step.el.scrollIntoView({ behavior: "smooth", block: "center" });
    requestAnimationFrame(function () {
      requestAnimationFrame(position);
    });
  }

  function startTour() {
    steps = buildSteps();
    if (steps.length === 0) return;
    active = true;
    document.body.appendChild(highlight);
    document.body.appendChild(tooltip);
    showStep(0);
  }

  function endTour() {
    active = false;
    if (highlight.parentNode) highlight.parentNode.removeChild(highlight);
    if (tooltip.parentNode) tooltip.parentNode.removeChild(tooltip);
  }

  prevBtn.addEventListener("click", function () {
    showStep(current - 1);
  });
  nextBtn.addEventListener("click", function () {
    if (current === steps.length - 1) endTour();
    else showStep(current + 1);
  });
  skipBtn.addEventListener("click", endTour);

  window.addEventListener("resize", function () {
    if (active) position();
  });
  window.addEventListener(
    "scroll",
    function () {
      if (active) position();
    },
    true
  );

  document.addEventListener("keydown", function (e) {
    if (!active) return;
    if (e.key === "Escape") endTour();
    else if (e.key === "ArrowRight") nextBtn.click();
    else if (e.key === "ArrowLeft" && !prevBtn.disabled) prevBtn.click();
  });

  const tourBtn = document.getElementById("tour-btn");
  if (tourBtn) tourBtn.addEventListener("click", startTour);

  // Auto-start every time the page loads, not just the first visit.
  setTimeout(startTour, 600);
})();
