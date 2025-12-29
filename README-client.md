# Client Guide (Vue + Node, Docker, Compose)

A minimal Vue single-page client that calls this TTS backend and plays the returned audio. The client runs in its own Node-based container and client and tts backend can be orchestrated with the API using `docker compose`.

## Overview
- Frontend: Vue 3 + Vite (single page: text input, "Synthesize" button, audio player bound to backend response).
- Backend API: existing FastAPI TTS service (running separately, e.g., `chatterbox-czech-api` image).
- Transport: POST JSON `{ text, language }` to `/v1/chat`; read `wav_base64` and feed to an `<audio>` tag via `data:audio/wav;base64,...`.
- Orchestration: Dockerfile for the client; `compose.yaml` ties client + API; models mounted only into API container.

## Files to add (client)
```
client/
  package.json
  package-lock.json (generated)
  vite.config.js
  index.html
  src/
    main.js
    App.vue
  Dockerfile.client
```

## Example client implementation (Vue 3 + Vite)
Create these files under `client/`:

`package.json`
```json
{
  "name": "tts-client",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "axios": "^1.6.8",
    "vue": "^3.4.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.0.0",
    "vite": "^5.0.0"
  }
}
```

`vite.config.js`
```js
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    port: 4173
  }
});
```

`index.html`
```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>TTS Client</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.js"></script>
  </body>
</html>
```

`src/main.js`
```js
import { createApp } from 'vue';
import App from './App.vue';
createApp(App).mount('#app');
```

`src/App.vue`
```vue
<template>
  <main class="page">
    <h1>Czech TTS Demo</h1>
    <label>
      Text to synthesize
      <textarea v-model="text" rows="4" placeholder="Napište text..."></textarea>
    </label>
    <label>
      Language code
      <input v-model="language" />
    </label>
    <button :disabled="loading || !text.trim()" @click="synthesize">
      {{ loading ? 'Working...' : 'Synthesize' }}
    </button>
    <p v-if="error" class="error">{{ error }}</p>
    <audio v-if="audioSrc" :src="audioSrc" controls></audio>
  </main>
</template>

<script setup>
import axios from 'axios';
import { ref } from 'vue';

const text = ref('Třetí přání je výkon pohřební služby');
const language = ref('cs');
const audioSrc = ref('');
const loading = ref(false);
const error = ref('');

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

async function synthesize() {
  loading.value = true;
  error.value = '';
  audioSrc.value = '';
  try {
    const res = await axios.post(`${API_BASE}/v1/chat`, {
      text: text.value,
      language: language.value
    });
    const { wav_base64 } = res.data;
    if (!wav_base64) throw new Error('No audio returned');
    audioSrc.value = `data:audio/wav;base64,${wav_base64}`;
  } catch (err) {
    error.value = err?.response?.data?.detail || err.message || 'Request failed';
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
:root { font-family: system-ui, -apple-system, "Segoe UI", sans-serif; }
.page { max-width: 600px; margin: 2rem auto; display: flex; flex-direction: column; gap: 0.75rem; padding: 1rem; }
textarea { width: 100%; font: inherit; }
input { width: 8rem; font: inherit; }
button { width: 10rem; padding: 0.5rem; font: inherit; }
.error { color: #c00; }
</style>
```

`client/Dockerfile`
```Dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build
EXPOSE 4173
CMD ["npm", "run", "preview", "--", "--host", "0.0.0.0", "--port", "4173"]
```

## Compose setup (client + API)
Add `compose.yaml` at repo root:
```yaml
version: "3.9"
services:
  api:
    image: chatterbox-czech-api:latest
    environment:
      DEVICE: cuda
      MODEL_DIR: /model
    volumes:
      - ./model:/model:ro
    ports:
      - "8000:8000"
    deploy:
      resources:
        reservations:
          devices:
            - capabilities: [gpu]
  client:
    build: ./client
    environment:
      VITE_API_BASE: http://api:8000
    ports:
      - "4173:4173"
    depends_on:
      - api
```

## Build and run
```bash
# Build images
docker build -t chatterbox-czech-api:latest .
docker compose build

# Run both
docker compose up
```
Then open http://localhost:4173 and synthesize speech.

## Notes
- The client is static and only needs network access to the API; no model is mounted into the client container.
- Ensure the model file `t3_cs.safetensors` is available on the host under `./model` before `docker compose up`.
- Adjust `DEVICE` in compose to `cpu` if GPU is unavailable.
- Ports: API on 8000, client on 4173.
