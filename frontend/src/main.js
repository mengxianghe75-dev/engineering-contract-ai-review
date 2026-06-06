import { createApp } from "vue";
import ElementPlus from "element-plus";
import "element-plus/dist/index.css";

import App from "./App.vue";
import router from "./router";
import "./assets/main.css";

const app = createApp(App);

app.use(router).use(ElementPlus).mount("#app");

// Pinia（可选）：执行 `npm install pinia` 后，取消下方注释即可启用 store 模式：
//
// import { createPinia } from "pinia";
// app.use(createPinia());
