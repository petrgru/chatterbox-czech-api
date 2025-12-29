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
    <label>
      Speech speed: {{ speed.toFixed(1) }}x
      <input v-model.number="speed" type="range" min="0.7" max="1.3" step="0.1" />
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
const speed = ref(1.1);
const audioSrc = ref('');
const loading = ref(false);
const error = ref('');

// Try to auto-detect API base URL based on current origin
const API_BASE = import.meta.env.VITE_API_BASE || (() => {
  const protocol = window.location.protocol;
  const hostname = window.location.hostname;
  const port = hostname === 'localhost' ? '8000' : '8000';
  return `${protocol}//${hostname}:${port}`;
})();

async function synthesize() {
  loading.value = true;
  error.value = '';
  audioSrc.value = '';
  try {
    const res = await axios.post(`${API_BASE}/v1/chat`, {
      text: text.value,
      language: language.value,
      speed: speed.value,
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
:root {
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
}
.page {
  max-width: 600px;
  margin: 2rem auto;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 1rem;
}
textarea {
  width: 100%;
  font: inherit;
}
input {
  width: 8rem;
  font: inherit;
}
button {
  width: 10rem;
  padding: 0.5rem;
  font: inherit;
}
.error {
  color: #c00;
}
</style>
