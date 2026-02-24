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
      const datasets = (config.datasets || []).map((dataset, index) => {
        const baseColor = palette[index % palette.length];
        return {
          label: dataset.label || `Series ${index + 1}`,
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
          plugins: { legend: { position: "bottom" } },
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
  props: { cards: { type: Array, default: () => [] } },
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
      title: "Performance Radar",
      labels: ["U", "R", "D", "L"],
      datasets: [{ label: "Sample", values: [2, 3, 4, 1], max: 5 }],
      step: 1,
      max: 5,
    });

    const refreshedAt = computed(() => formatTimestamp(timestamp.value));
    const heroText = computed(() => `This starter page now runs on Vue 3 + Flask ${flaskVersion.value}.`);

    const cardWall = ref([
      {
        id: "skills-radar",
        type: "radar",
        title: "Skills Radar",
        badge: "Chart",
        body: "Visualize skill balance across tracks.",
        chart: radarChart.value,
      },
      {
        id: "backend-tasks",
        type: "list",
        title: "Backend Tasks",
        items: [
          { label: "API contracts", value: "Done" },
          { label: "Auth flow", value: "In review" },
          { label: "Logging", value: "Pending" },
        ],
      },
      {
        id: "deploy-status",
        type: "stat",
        title: "Deploys this week",
        value: "5",
        badge: "CI/CD",
      },
    ]);

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
    };
  },
  template: `
    <div class="d-flex flex-column gap-3">
      <Breadcrumbs :items="breadcrumbs" />

      <header class="d-flex justify-content-between align-items-center mb-1">
        <div>
          <h1 class="h4 mb-0">{{ pageTitle }}</h1>
          <p class="text-muted mb-0">Starter interface powered by Vue 3 + Bootstrap 5</p>
        </div>
        <span class="badge text-bg-primary">Vue</span>
      </header>

      <div class="row row-cols-1 row-cols-md-2 g-3">
        <div class="col">
          <InfoCard title="Welcome" :body="heroText" :meta="'Last refreshed: ' + refreshedAt" />
        </div>
        <div class="col">
          <InfoCard title="What is this?" body="A Vue-powered dashboard scaffold you can extend with components, charts, and API data." />
        </div>
      </div>

      <CardGrid :cards="cardWall" />
    </div>
  `,
});

createApp(App).mount("#app");
