import { createApp } from 'vue';
import router from './router';
import AppRoot from './AppRoot.vue';

createApp(AppRoot).use(router).mount('#app');
