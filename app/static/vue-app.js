/* Vue 3 single-page experience mounted inside Flask template */

const { createApp, ref, computed, onMounted, defineComponent } = Vue;

const formatTimestamp = (value) => {
  const parsed = value ? new Date(value) : new Date();
  return parsed.toLocaleString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
};

const Breadcrumbs = defineComponent({
  name: "Breadcrumbs",
  props: { items: { type: Array, default: () => [] } },
  template: "#tpl-breadcrumbs",
});

const RadarChart = defineComponent({
  name: "RadarChart",
  props: {
    chart: { type: Object, required: true },
  },
  mounted() {
    const config = this.chart || {};
    const palette = [
      "#0d6efd", "#6610f2", "#6f42c1", "#d63384", "#dc3545", "#fd7e14",
      "#ffc107", "#198754", "#20c997", "#0dcaf0", "#adb5bd", "#343a40",
    ];

    const toRgba = (hex, alpha) => {
      const parsed = /^#?([a-f\\d]{2})([a-f\\d]{2})([a-f\\d]{2})$/i.exec(hex);
      if (!parsed) return "rgba(13,110,253,0.2)";
      const [_, r, g, b] = parsed;
      return `rgba(${parseInt(r, 16)}, ${parseInt(g, 16)}, ${parseInt(b, 16)}, ${alpha})`;
    };

    const renderChart = () => {
      const rawDatasets = config.datasets || [];
      const showLegend = rawDatasets.length > 1;
      const datasets = rawDatasets.map((dataset, index) => {
        const baseColor = palette[index % palette.length];
        return {
          label: showLegend ? dataset.label || `Series ${index + 1}` : "",
          data: dataset.values || [],
          backgroundColor: toRgba(baseColor, 0.2),
          borderColor: baseColor,
          pointBackgroundColor: baseColor,
          pointBorderColor: "#fff",
          pointHoverBackgroundColor: "#fff",
          pointHoverBorderColor: baseColor,
          borderWidth: 2,
          fill: true,
        };
      });

      const ctx = document.getElementById(config.id || "radarChartCanvas");
      if (!ctx) return;

      new Chart(ctx, {
        type: "radar",
        data: { labels: config.labels || [], datasets },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          aspectRatio: 1,
          scales: {
            r: {
              beginAtZero: true,
              ticks: {
                suggestedMax: config.max || 5,
                stepSize: config.step || 1,
              },
            },
          },
          plugins: { legend: { display: showLegend, position: "bottom" } },
        },
      });
    };

    const waitForChart = () => {
      if (typeof Chart !== "undefined") {
        renderChart();
      } else {
        requestAnimationFrame(waitForChart);
      }
    };

    waitForChart();
  },
  template: "#tpl-radar-chart",
});

const InfoCard = defineComponent({
  name: "InfoCard",
  props: {
    title: String,
    body: String,
    meta: String,
  },
  template: "#tpl-info-card",
});

const CardGrid = defineComponent({
  name: "CardGrid",
  components: { RadarChart },
  emits: ["reorder"],
  props: { cards: { type: Array, default: () => [] } },
  setup(_, { emit }) {
    const dragIndex = ref(null);
    const dragOverIndex = ref(null);
    const dragImageEl = ref(null);

    const onDragStart = (event, index) => {
      dragIndex.value = index;
      dragOverIndex.value = index;
      if (event.dataTransfer) {
        event.dataTransfer.setData("text/plain", String(index));
        event.dataTransfer.effectAllowed = "move";
      }
      const target = event.currentTarget;
      if (target) {
        const clone = target.cloneNode(true);
        if (clone instanceof HTMLElement) {
          clone.classList.add("drag-preview");
          clone.style.position = "absolute";
          clone.style.top = "-9999px";
          clone.style.left = "-9999px";
          clone.style.width = `${target.offsetWidth}px`;
          clone.style.height = `${target.offsetHeight}px`;
          clone.style.zIndex = "9999";
          document.body.appendChild(clone);
          dragImageEl.value = clone;
          event.dataTransfer?.setDragImage(clone, clone.offsetWidth / 2, clone.offsetHeight / 2);
        }
      }
    };

    const onDrop = (event, index) => {
      event.preventDefault();
      dragOverIndex.value = null;
      if (dragIndex.value !== null && dragIndex.value !== index) {
        emit("reorder", { from: dragIndex.value, to: index });
      }
    };

    const onDragEnd = () => {
      dragIndex.value = null;
      dragOverIndex.value = null;
      if (dragImageEl.value) {
        document.body.removeChild(dragImageEl.value);
        dragImageEl.value = null;
      }
    };

    const onDragOver = (event, index) => {
      event.preventDefault();
      dragOverIndex.value = index;
      if (event.dataTransfer) {
        event.dataTransfer.dropEffect = "move";
      }
    };

    const onDragEnter = (index) => {
      dragOverIndex.value = index;
    };

    const onDragLeave = (index) => {
      if (dragOverIndex.value === index) {
        dragOverIndex.value = null;
      }
    };

    const summarizeCard = async (card) => {
      if (!card) return;
      card.status = "loading";
      card.error = "";
      card.analysis = null;
      try {
        const response = await fetch("/api/generate-summary", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            text: card.query || "",
            name: card.playerName || "",
            position: card.playerPosition || "",
          }),
        });
        if (!response.ok) {
          throw new Error("Server returned an error");
        }
        card.analysis = await response.json();
        card.status = "done";
      } catch (error) {
        card.status = "error";
        card.error = error instanceof Error ? error.message : "Unable to summarize text";
      }
    };

    const copySummary = async (card) => {
      const text = card?.analysis?.summary;
      if (!text || typeof navigator === "undefined" || !navigator.clipboard) return;
      try {
        await navigator.clipboard.writeText(text);
        card.copyStatus = "copied";
        setTimeout(() => {
          card.copyStatus = "";
        }, 1400);
      } catch (err) {
        card.copyStatus = "failed";
      }
    };

    return {
      onDragStart,
      onDrop,
      onDragEnd,
      onDragOver,
      onDragEnter,
      onDragLeave,
      dragIndex,
      dragOverIndex,
      summarizeCard,
      copySummary,
    };
  },
  template: "#tpl-card-grid",
});

const App = defineComponent({
  name: "DashboardApp",
  components: { Breadcrumbs, InfoCard, CardGrid },
  setup() {
    const dataEl = document.getElementById("page-data");
    const parsed = dataEl ? JSON.parse(dataEl.textContent || "{}") : {};

    const pageTitle = ref(parsed.page_title || "Dashboard");
    const breadcrumbs = ref(parsed.breadcrumbs || []);
    const flaskVersion = ref(parsed.flask_version || "");
    const timestamp = ref(parsed.timestamp || new Date().toISOString());
    const radarChart = ref(parsed.radar_chart || {
      id: "radarChartCanvas",
      title: "Player Comparison",
      labels: ["Finishing", "Playmaking", "Agility", "Mentality", "Defense"],
      datasets: [
        { label: "Player A", values: [4, 5, 4, 4, 3], max: 5 },
        { label: "Player B", values: [3, 4, 3, 5, 2], max: 5 },
      ],
      step: 1,
      max: 5,
    });

    const refreshedAt = computed(() => formatTimestamp(timestamp.value));
    const heroText = computed(
      () => `Hashmark keeps your college football recruiting intel and analytics in sync with Flask ${flaskVersion.value}.`
    );

    const playerChart = {
      id: "playerRadarChart",
      title: "Season Snapshot",
      labels: ["Finishing", "Playmaking", "Agility", "Mentality", "Defense"],
      datasets: [{ label: "2026 Season", values: [4, 5, 4, 4, 3], max: 5 }],
      step: 1,
      max: 5,
    };

    const defaultCards = [
      {
        id: "player-profile",
        type: "player",
        title: "Player Profile",
        badge: "Stars",
        body: "A two-way forward who can finish, create, and help organize from the wings.",
        name: "Jordan Miles",
        role: "Wing Forward / Playmaker",
        avatar:
          "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 120 120'%3E%3Crect width='120' height='120' fill='%23e9ecef'/%3E%3Ccircle cx='60' cy='40' r='26' fill='%23adb5bd'/%3E%3Cpath d='M20 98c0-22 18-40 40-40s40 18 40 40z' fill='%23adb5bd'/%3E%3C/svg%3E",
        chart: playerChart,
      },
      {
        id: "skills-radar",
        type: "radar",
        title: "Skills Radar",
        badge: "Chart",
        body: "Visualize skill balance across tracks.",
        chart: radarChart.value,
      },
      {
        id: "visit-schedule",
        type: "list",
        title: "Upcoming Visits",
        items: [
          { label: "Northwestern Visit", value: "Confirmed" },
          { label: "Spring Camp", value: "Pending" },
          { label: "Highlight Tape Drop", value: "Processing" },
        ],
      },
      {
        id: "recruit-score",
        type: "stat",
        title: "Scout Wins",
        value: "12",
        badge: "Season",
      },
      {
        id: "text-analyzer",
        type: "analysis",
        title: "Evaluation Summary",
        badge: "Server",
        body: "",
        query: "",
        status: "idle",
        analysis: null,
        error: "",
        playerName: "",
        playerPosition: "",
        copyStatus: "",
      },
    ];

    const cardOrderStorageKey = "hashmark-card-order";

    const getSavedOrder = () => {
      if (typeof window === "undefined") return null;
      try {
        return JSON.parse(window.localStorage.getItem(cardOrderStorageKey) || "null");
      } catch (error) {
        return null;
      }
    };

    const buildCardsFromOrder = () => {
      const saved = getSavedOrder();
      if (!Array.isArray(saved)) return [...defaultCards];
      const cardMap = new Map(defaultCards.map((card) => [card.id, card]));
      const ordered = saved.map((id) => cardMap.get(id)).filter(Boolean);
      const remaining = defaultCards.filter((card) => !saved.includes(card.id));
      return [...ordered, ...remaining];
    };

    const cardWall = ref(buildCardsFromOrder());

    const persistOrder = () => {
      if (typeof window === "undefined") return;
      window.localStorage.setItem(cardOrderStorageKey, JSON.stringify(cardWall.value.map((card) => card.id)));
    };

    const moveCard = ({ from, to }) => {
      const updated = [...cardWall.value];
      const [moved] = updated.splice(from, 1);
      updated.splice(to, 0, moved);
      cardWall.value = updated;
      persistOrder();
    };

    const addCard = (card) => {
      cardWall.value = [...cardWall.value, card];
      persistOrder();
    };

    onMounted(() => {
      document.title = `${pageTitle.value} | Vue Dashboard`;
    });

    return {
      pageTitle,
      breadcrumbs,
      flaskVersion,
      radarChart,
      refreshedAt,
      heroText,
      cardWall,
      moveCard,
      addCard,
    };
  },
  template: `
    <div class="d-flex flex-column gap-3">
      <Breadcrumbs :items="breadcrumbs" />

      <CardGrid :cards="cardWall" @reorder="moveCard" />
    </div>
  `,
});

createApp(App).mount("#app");
