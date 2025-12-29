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
    <div class="file-upload-section">
      <label class="file-upload-label">
        Or upload text file (min 200kB recommended)
        <input 
          type="file" 
          accept=".txt,.md,.text" 
          @change="handleTextFileUpload"
          ref="textFileInput"
        />
        <span class="file-upload-button">📄 Choose Text File</span>
      </label>
      <p v-if="uploadedFileName" class="uploaded-file-info">
        Loaded: {{ uploadedFileName }} ({{ uploadedFileSize }})
      </p>
    </div>
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
    <div v-if="audioSrc" class="audio-section">
      <audio :src="audioSrc" controls></audio>
      <button @click="downloadAudio" class="download-button">
        💾 Download WAV
      </button>
    </div>
  </main>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import axios from 'axios';

const API_BASE = window.location.origin.includes('localhost')
  ? 'http://localhost:8000'
  : window.location.origin.replace(/:\d+/, ':8000');

const text = ref('Třetí přání je výkon pohřební služby');
const language = ref('cs');
const speed = ref(1.1);
const selectedVoiceSample = ref('');
const voiceSamples = ref([]);
const audioSrc = ref('');
const loading = ref(false);
const error = ref('');
const textFileInput = ref(null);
const uploadedFileName = ref('');
const uploadedFileSize = ref('');
const audioBlob = ref(null);

async function loadVoiceSamples() {
  try {
    const res = await axios.get(`${API_BASE}/v1/voice-samples`);
    voiceSamples.value = res.data.samples;
  } catch (err) {
    console.error('Failed to load voice samples:', err);
  }
}

function handleTextFileUpload(event) {
  const file = event.target.files[0];
  if (!file) return;
  
  const sizeKB = (file.size / 1024).toFixed(1);
  uploadedFileName.value = file.name;
  uploadedFileSize.value = `${sizeKB} KB`;
  
  if (file.size < 200 * 1024) {
    error.value = `Warning: File is only ${sizeKB} KB. For best results, use files larger than 200 KB.`;
    setTimeout(() => { error.value = ''; }, 5000);
  }
  
  const reader = new FileReader();
  reader.onload = (e) => {
    text.value = e.target.result;
  };
  reader.readAsText(file);
}

function downloadAudio() {
  if (!audioSrc.value) return;
  
  // Create download link
  const link = document.createElement('a');
  link.href = audioSrc.value;
  
  // Generate filename with timestamp
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
  const voiceName = selectedVoiceSample.value 
    ? voiceSamples.value.find(s => s.id === selectedVoiceSample.value)?.name || 'default'
    : 'default';
  link.download = `tts-${voiceName}-${timestamp}.wav`;
  
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

async function synthesize() {
  loading.value = true;
  error.value = '';
  audioSrc.value = '';
  audioBlob.value = null;
  
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
label {
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
  padding: 0.5rem 1rem;
  font: inherit;
  cursor: pointer;
  border: none;
  border-radius: 4px;
  background: #4a90e2;
  color: white;
  transition: background 0.2s;
}
button:hover:not(:disabled) {
  background: #357abd;
}
button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  background: #999;
}
.error {
  color: #c00;
}
.file-upload-section {
  padding: 1rem;
  background: #f9f9f9;
  border-radius: 6px;
  border: 1px dashed #ddd;
}
.file-upload-label {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  cursor: pointer;
}
.file-upload-label input[type="file"] {
  display: none;
}
.file-upload-button {
  display: inline-block;
  padding: 0.75rem 1.5rem;
  background: #6c757d;
  color: white;
  border-radius: 4px;
  text-align: center;
  transition: background 0.2s;
}
.file-upload-button:hover {
  background: #5a6268;
}
.uploaded-file-info {
  margin: 0.5rem 0 0 0;
  font-size: 0.9rem;
  color: #27ae60;
  font-weight: 500;
}
.audio-section {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 1rem;
  background: #f9f9f9;
  border-radius: 6px;
}
.audio-section audio {
  width: 100%;
}
.download-button {
  background: #27ae60;
}
.download-button:hover:not(:disabled) {
  background: #229954;
}
</style>
