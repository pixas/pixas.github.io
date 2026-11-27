(() => {
  // ---------------------------------------------------------------------------
  // 1. Generic Tab Controller (Method, Insights, Case Studies, Quick Start)
  // ---------------------------------------------------------------------------
  document.querySelectorAll("[data-tab-group]").forEach((shell) => {
    const buttons = shell.querySelectorAll(".tab-btn[data-tab]");
    const panels = shell.querySelectorAll("[data-panel]");
    buttons.forEach((btn) => {
      btn.addEventListener("click", () => {
        const target = btn.getAttribute("data-tab");
        buttons.forEach((b) => b.classList.toggle("active", b === btn));
        panels.forEach((p) => p.classList.toggle("active", p.getAttribute("data-panel") === target));
      });
    });
  });

  // ---------------------------------------------------------------------------
  // 2. Interactive Benchmark SVG Bar Chart
  // ---------------------------------------------------------------------------
  const BENCHMARKS = [
    "AIME 25",
    "AIME 26",
    "HMMT Feb25",
    "HMMT Feb26",
    "BeyondAIME",
    "ArXiv 0526",
    "ArXiv 0626",
    "Micro Avg",
  ];

  const DATA = {
    stage2: {
      avg32: {
        title: "Stage-2 Scaling: FORGE-4B vs. Official Qwen3.5-4B & Base",
        subtitle: "Pass@1 (Avg@32, %) across 7 benchmarks & Micro Average (81,920-token budget, K=32)",
        series: [
          { name: "Qwen3.5-4B-Base", color: "#94a3b8", values: [81.35, 82.50, 74.27, 68.47, 56.66, 24.84, 10.91, 53.20] },
          { name: "Qwen3.5-4B (Official)", color: "#d97706", values: [85.00, 84.17, 76.46, 62.22, 56.31, 24.06, 12.63, 53.32] },
          { name: "FORGE-4B (Stage 2)", color: "#1e5aa8", values: [86.77, 89.48, 78.33, 69.70, 59.59, 34.92, 18.75, 58.37] },
        ],
      },
      pass32: {
        title: "Stage-2 Scaling: Multi-Sample Problem Coverage (Pass@32)",
        subtitle: "Pass@32 (%) across 7 benchmarks & Micro Average — FORGE expands coverage while official post-training narrows it",
        series: [
          { name: "Qwen3.5-4B-Base", color: "#94a3b8", values: [96.67, 96.67, 100.00, 87.88, 85.00, 62.50, 55.10, 81.41] },
          { name: "Qwen3.5-4B (Official)", color: "#d97706", values: [90.00, 93.33, 90.00, 84.85, 74.00, 50.00, 36.73, 71.15] },
          { name: "FORGE-4B (Stage 2)", color: "#1e5aa8", values: [96.67, 96.67, 93.33, 90.91, 87.00, 67.50, 61.22, 83.33] },
        ],
      },
    },
    stage1: {
      avg32: {
        title: "Stage-1 Controlled RL Comparison (350 Steps, 16K → 32K)",
        subtitle: "Pass@1 (Avg@32, %) from identical Qwen3.5-4B-Base initialization & 14,809-prompt budget",
        series: [
          { name: "GRPO", color: "#cbd5e1", values: [56.25, 64.48, 41.15, 41.10, 39.66, 18.75, 9.25, 36.48] },
          { name: "DAPO", color: "#94a3b8", values: [54.79, 67.08, 42.29, 46.12, 40.59, 20.31, 8.74, 37.65] },
          { name: "HATCH (ref-guided)", color: "#a78bfa", values: [58.54, 66.88, 38.44, 46.12, 40.75, 20.63, 9.25, 37.79] },
          { name: "SAGE (ref-guided)", color: "#f59e0b", values: [79.06, 82.60, 66.04, 60.61, 51.44, 27.34, 13.33, 50.39] },
          { name: "FORGE (Stage 1)", color: "#1e5aa8", values: [80.31, 82.71, 65.52, 62.88, 53.38, 28.75, 13.90, 51.60] },
        ],
      },
      pass32: {
        title: "Stage-1 Controlled RL Comparison: Exploration Coverage (Pass@32)",
        subtitle: "Pass@32 (%) at step 350 — FORGE beats reference-guided SAGE by +5.13 pp in Micro Pass@32",
        series: [
          { name: "GRPO", color: "#cbd5e1", values: [86.67, 86.67, 73.33, 84.85, 67.00, 47.50, 48.98, 67.95] },
          { name: "DAPO", color: "#94a3b8", values: [86.67, 90.00, 70.00, 81.82, 68.00, 50.00, 36.73, 66.35] },
          { name: "HATCH (ref-guided)", color: "#a78bfa", values: [83.33, 90.00, 70.00, 78.79, 71.00, 47.50, 42.86, 67.31] },
          { name: "SAGE (ref-guided)", color: "#f59e0b", values: [93.33, 96.67, 86.67, 90.91, 78.00, 67.50, 48.98, 77.56] },
          { name: "FORGE (Stage 1)", color: "#1e5aa8", values: [96.67, 96.67, 93.33, 87.88, 84.00, 70.00, 63.27, 82.69] },
        ],
      },
    },
  };

  let currentView = "stage2";
  let currentMetric = "avg32";

  const svg = document.getElementById("benchmarkChart");
  const legendEl = document.getElementById("chartLegend");
  const titleEl = document.getElementById("chartTitle");
  const subEl = document.getElementById("chartSubtitle");

  function svgEl(tag, attrs = {}, text = "") {
    const el = document.createElementNS("http://www.w3.org/2000/svg", tag);
    Object.entries(attrs).forEach(([k, v]) => el.setAttribute(k, String(v)));
    if (text) el.textContent = text;
    return el;
  }

  function renderChart() {
    if (!svg) return;
    const cfg = DATA[currentView][currentMetric];
    titleEl.textContent = cfg.title;
    subEl.textContent = cfg.subtitle;

    // Legend
    legendEl.innerHTML = cfg.series
      .map(
        (s) =>
          `<span class="legend-item"><span class="legend-swatch" style="background:${s.color}"></span>${s.name}</span>`
      )
      .join("");

    // Dimensions
    const W = 980;
    const H = 355;
    const pad = { top: 26, right: 20, bottom: 54, left: 48 };
    const plotW = W - pad.left - pad.right;
    const plotH = H - pad.top - pad.bottom;

    svg.innerHTML = "";

    // Subtle highlight background for Micro Avg group
    const nGroups = BENCHMARKS.length;
    const groupW = plotW / nGroups;
    const microX = pad.left + (nGroups - 1) * groupW;
    svg.appendChild(
      svgEl("rect", {
        x: microX + 4,
        y: pad.top - 8,
        width: groupW - 4,
        height: plotH + 14,
        rx: 8,
        fill: "#f1f6fe",
      })
    );

    // Horizontal grid lines (0, 20, 40, 60, 80, 100)
    [0, 20, 40, 60, 80, 100].forEach((tick) => {
      const y = pad.top + plotH * (1 - tick / 100);
      svg.appendChild(
        svgEl("line", {
          x1: pad.left,
          x2: W - pad.right,
          y1: y,
          y2: y,
          stroke: tick === 0 ? "#cbd5e1" : "#e2e8f0",
          "stroke-dasharray": tick === 0 ? "" : "3,4",
        })
      );
      svg.appendChild(
        svgEl(
          "text",
          {
            x: pad.left - 10,
            y: y + 4,
            "text-anchor": "end",
            fill: "#64748b",
            "font-size": 11,
            "font-family": "JetBrains Mono, monospace",
          },
          `${tick}%`
        )
      );
    });

    // Grouped bars
    const nSeries = cfg.series.length;
    const innerPad = nSeries <= 3 ? 18 : 11;
    const barGap = nSeries <= 3 ? 4 : 2.5;
    const barW = (groupW - innerPad * 2 - barGap * (nSeries - 1)) / nSeries;

    BENCHMARKS.forEach((bName, gIdx) => {
      const gx = pad.left + gIdx * groupW;
      cfg.series.forEach((s, sIdx) => {
        const val = s.values[gIdx];
        const barH = Math.max(2, (val / 100) * plotH);
        const bx = gx + innerPad + sIdx * (barW + barGap);
        const by = pad.top + plotH - barH;
        const isForge = sIdx === nSeries - 1;

        const rect = svgEl("rect", {
          x: bx,
          y: by,
          width: barW,
          height: barH,
          rx: 3.5,
          fill: s.color,
          opacity: isForge ? 1 : 0.9,
        });
        const title = svgEl("title", {}, `${s.name} — ${bName}: ${val.toFixed(2)}%`);
        rect.appendChild(title);
        svg.appendChild(rect);

        // Label FORGE values cleanly above each bar (and all 3 in stage2 view)
        if (isForge || (nSeries === 3 && gIdx === nGroups - 1)) {
          svg.appendChild(
            svgEl(
              "text",
              {
                x: bx + barW / 2,
                y: by - 6,
                "text-anchor": "middle",
                fill: isForge ? "#0f3d7a" : "#475569",
                "font-size": isForge ? 10.5 : 9.5,
                "font-weight": isForge ? 700 : 600,
                "font-family": "JetBrains Mono, monospace",
              },
              val.toFixed(1)
            )
          );
        }
      });

      // X-axis label
      svg.appendChild(
        svgEl(
          "text",
          {
            x: gx + groupW / 2,
            y: H - 22,
            "text-anchor": "middle",
            fill: gIdx === nGroups - 1 ? "#0f3d7a" : "#334155",
            "font-size": 11.5,
            "font-weight": gIdx === nGroups - 1 ? 700 : 600,
            "font-family": "Inter, sans-serif",
          },
          bName
        )
      );
    });
  }

  document.querySelectorAll("[data-view]").forEach((btn) => {
    btn.addEventListener("click", () => {
      currentView = btn.getAttribute("data-view");
      document.querySelectorAll("[data-view]").forEach((b) => b.classList.toggle("active", b === btn));
      renderChart();
    });
  });
  document.querySelectorAll("[data-metric]").forEach((btn) => {
    btn.addEventListener("click", () => {
      currentMetric = btn.getAttribute("data-metric");
      document.querySelectorAll("[data-metric]").forEach((b) => b.classList.toggle("active", b === btn));
      renderChart();
    });
  });
  renderChart();

  // ---------------------------------------------------------------------------
  // 3. Copy Buttons (Quick Start & BibTeX)
  // ---------------------------------------------------------------------------
  function wireCopy(btnId, getText) {
    const btn = document.getElementById(btnId);
    if (!btn) return;
    btn.addEventListener("click", async () => {
      const orig = btn.textContent;
      try {
        await navigator.clipboard.writeText(getText());
        btn.textContent = "Copied!";
      } catch {
        btn.textContent = "Copy failed";
      }
      setTimeout(() => {
        btn.textContent = orig;
      }, 1600);
    });
  }

  wireCopy("copyCodeBtn", () => {
    const active = document.querySelector('[data-tab-group="quickstart"] .code-block.active');
    return active ? active.innerText.trim() : "";
  });
  wireCopy("copyBibtexBtn", () => {
    const pre = document.getElementById("bibtexText");
    return pre ? pre.innerText.trim() : "";
  });

  // ---------------------------------------------------------------------------
  // 4. Figure Zoom Lightbox
  // ---------------------------------------------------------------------------
  const lightbox = document.getElementById("lightbox");
  const lightboxImg = document.getElementById("lightboxImg");
  const lightboxCap = document.getElementById("lightboxCap");
  const lightboxClose = document.getElementById("lightboxClose");

  function closeLightbox() {
    lightbox.classList.remove("open");
    lightbox.setAttribute("aria-hidden", "true");
  }

  document.querySelectorAll(".zoomable-img").forEach((img) => {
    img.addEventListener("click", () => {
      lightboxImg.src = img.src;
      lightboxImg.alt = img.alt;
      const cap = img.closest(".figure-card")?.querySelector(".figure-caption");
      lightboxCap.textContent = cap ? cap.innerText : img.alt;
      lightbox.classList.add("open");
      lightbox.setAttribute("aria-hidden", "false");
    });
  });

  lightboxClose?.addEventListener("click", closeLightbox);
  lightbox?.addEventListener("click", (e) => {
    if (e.target === lightbox) closeLightbox();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeLightbox();
  });

  // ---------------------------------------------------------------------------
  // 5. Navbar Scroll-Spy
  // ---------------------------------------------------------------------------
  const navLinks = Array.from(document.querySelectorAll(".nav-links a"));
  const sections = navLinks
    .map((a) => document.querySelector(a.getAttribute("href")))
    .filter(Boolean);

  window.addEventListener(
    "scroll",
    () => {
      const y = window.scrollY + 110;
      let activeId = "";
      for (const sec of sections) {
        if (sec.offsetTop <= y) activeId = sec.id;
      }
      navLinks.forEach((a) => {
        a.classList.toggle("active", a.getAttribute("href") === `#${activeId}`);
      });
    },
    { passive: true }
  );
})();
