import {
  ArcElement,
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Legend,
  LinearScale,
  LineElement,
  PointElement,
  Tooltip,
} from "chart.js";

// Registered once, imported (for its side effect) by every chart
// component below - Chart.js v4 requires explicit opt-in per element/
// scale/plugin used across all five charts.
ChartJS.register(ArcElement, BarElement, CategoryScale, LinearScale, LineElement, PointElement, Legend, Tooltip);

export { ChartJS };
