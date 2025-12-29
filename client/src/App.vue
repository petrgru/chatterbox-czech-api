<template>
  <main class="page">
    <header class="header">
      <h1>Czech TTS Demo</h1>
      <router-link to="/settings" class="settings-link">⚙️ Voice Samples</router-link>
    </header>
    
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
    <label>
      Voice Sample
      <select v-model="selectedVoiceSample">
        <option value="">Default Voice</option>
        <option v-for="sample in voiceSamples" :key="sample.id" :value="sample.id">
          {{ sample.name }}
        </option>
      </select>
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
import { ref, onMounted } from 'vue';

const text = ref('Třetí přání je výkon pohřební služby');
const language = ref('cs');
const speed = ref(1.1);
const selectedVoiceSample = ref('');
const voiceSamples = ref([]);
const audioSrc = ref('');
const loading = ref(false);
const error = ref('');

const API_BASE = import.meta.env.VITE_API_BASE || (() => {
  const protocol = window.location.protocol;
  const hostname = window.location.hostname;
  const port = hostname === 'localhost' ? '8000' : '8000';
  return `${protocol}//${hostname}:${port}`;
})();

async function loadVoiceSamples() {
  try {
    const res = await axios.get(`${API_BASE}/v1/voice-samples`);
    voiceSamples.value = res.data.samples;
  } catch (err) {
    console.error('Failed to load voice samples:', err);
  }
}

async function synthesize() {
  loading.value = true;
  error.value = '';
  audioSrc.value = '';
  try {
    const payload = {
      text: text.value,
      language: language.value,
      speed: speed.value,
    };
    
    if (selectedVoiceSample.value) {
      payload.voice_sample_id = selectedVoiceSample.value;
    }
    
    const res = await axios.post(`${API_BASE}/v1/chat`, payload);
    const { wav_base64 } = res.data;
    if (!wav_base64) throw new Error('No audio returned');
    audioSrc.value = `data:audio/wav;base64,${wav_base64}`;
  } catch (err) {
    error.value = err?.response?.data?.detail || err.message || 'Request failed';
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  loadVoiceSamples();
});
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
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}
.header h1 {
  margin: 0;
}
.settings-link {
  color: #4a90e2;
  text-decoration: none;
  font-weight: 500;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  transition: background 0.2s;
}
.settings-link:hover {
  background: #f0f0f0;
}
textarea {
  width: 100%;
  font: inherit;
}
input, select {
  width: 100%;
  font: inherit;
  padding: 0.5rem;
}
select {
  width: calc(100% + 1rem);
  margin-left: -0.5rem;
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
