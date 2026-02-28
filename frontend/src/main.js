import "./style.css";
import { createApp } from "vue";
import App from "./App.vue";
import axios from "axios";

axios.defaults.withCredentials = true;

createApp(App).mount("#app");