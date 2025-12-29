<template>
  <main class="page">
    <header class="header">
      <h1>Voice Samples Settings</h1>
      <router-link to="/" class="back-link">← Back to TTS</router-link>
    </header>

    <section class="upload-section">
      <h2>Upload Voice Sample</h2>
      
      <div class="upload-methods">
        <!-- File Upload -->
        <div class="upload-method">
          <h3>From File</h3>
          <label class="file-label">
            <input 
              type="file" 
              accept="audio/wav,audio/mp3,audio/*" 
              @change="handleFileSelect"
              ref="fileInput"
            />
            <span class="file-button">Choose Audio File</span>
          </label>
          <p v-if="selectedFileName" class="file-name">{{ selectedFileName }}</p>
        </div>

        <!-- Microphone Recording -->
        <div class="upload-method">
          <h3>Record from Microphone</h3>
          <button 
            @click="toggleRecording" 
            :class="['record-button', { recording: isRecording }]"
            :disabled="uploading"
          >
            {{ isRecording ? '⏹ Stop Recording' : '🎤 Start Recording' }}
          </button>
          <p v-if="recordingDuration > 0" class="recording-duration">
            Duration: {{ recordingDuration }}s
          </p>
          <audio v-if="recordedAudioUrl" :src="recordedAudioUrl" controls class="audio-preview"></audio>
          <p v-if="recordedAudioUrl && audioData" class="ready-indicator">✓ Ready to upload</p>
        </div>
      </div>

      <!-- Sample Name Input -->
      <div v-if="audioData" class="name-input-section">
        <label>
          Sample Name
          <input 
            v-model="sampleName" 
            placeholder="Enter a name for this voice sample..."
            @keyup.enter="uploadSample"
          />
        </label>
        <button 
          @click="uploadSample" 
          :disabled="uploading || !sampleName.trim()"
          class="upload-button"
        >
          {{ uploading ? 'Uploading...' : 'Upload Sample' }}
        </button>
      </div>

      <p v-if="uploadError" class="error">{{ uploadError }}</p>
      <p v-if="uploadSuccess" class="success">{{ uploadSuccess }}</p>
    </section>

    <section class="samples-section">
      <h2>Saved Voice Samples</h2>
      <p v-if="loading" class="loading">Loading samples...</p>
      <p v-if="samplesError" class="error">{{ samplesError }}</p>
      
      <div v-if="!loading && samples.length === 0" class="no-samples">
        No voice samples yet. Upload one above!
      </div>

      <div v-else class="samples-list">
        <div 
          v-for="sample in samples" 
          :key="sample.id" 
          class="sample-item"
        >
          <div class="sample-info">
            <h3>{{ sample.name }}</h3>
            <p class="sample-meta">
              Created: {{ formatDate(sample.created_at) }} • 
              Size: {{ formatSize(sample.file_size) }}
            </p>
          </div>
          <button 
            @click="deleteSample(sample.id)" 
            class="delete-button"
            :disabled="deleting === sample.id"
          >
            {{ deleting === sample.id ? 'Deleting...' : '🗑 Delete' }}
          </button>
        </div>
      </div>
    </section>
  </main>
</template>

<script setup>
import axios from 'axios';
import { ref, onMounted, onUnmounted } from 'vue';

const API_BASE = import.meta.env.VITE_API_BASE || (() => {
  const protocol = window.location.protocol;
  const hostname = window.location.hostname;
  const port = hostname === 'localhost' ? '8000' : '8000';
  return `${protocol}//${hostname}:${port}`;
})();

// File upload state
const fileInput = ref(null);
const selectedFileName = ref('');
const audioData = ref('');
const sampleName = ref('');
const uploading = ref(false);
const uploadError = ref('');
const uploadSuccess = ref('');

// Recording state
const isRecording = ref(false);
const recordingDuration = ref(0);
const recordedAudioUrl = ref('');
const mediaRecorder = ref(null);
const audioChunks = ref([]);
const recordingInterval = ref(null);

// Samples list state
const samples = ref([]);
const loading = ref(false);
const samplesError = ref('');
const deleting = ref(null);

// File upload handler
function handleFileSelect(event) {
  const file = event.target.files[0];
  if (!file) return;
  
  selectedFileName.value = file.name;
  const reader = new FileReader();
  
  reader.onload = (e) => {
    const arrayBuffer = e.target.result;
    const base64 = btoa(
      new Uint8Array(arrayBuffer).reduce((data, byte) => data + String.fromCharCode(byte), '')
    );
    audioData.value = base64;
    recordedAudioUrl.value = ''; // Clear recorded audio
  };
  
  reader.readAsArrayBuffer(file);
}

// Microphone recording
async function toggleRecording() {
  if (isRecording.value) {
    stopRecording();
  } else {
    await startRecording();
  }
}

async function startRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    
    // Try to use WAV codec if available, otherwise use default
    let options = { mimeType: 'audio/webm' };
    if (!MediaRecorder.isTypeSupported('audio/webm')) {
      options = {};
    }
    
    mediaRecorder.value = new MediaRecorder(stream, options);
    audioChunks.value = [];
    
    mediaRecorder.value.ondataavailable = (event) => {
      if (event.data.size > 0) {
        audioChunks.value.push(event.data);
      }
    };
    
    mediaRecorder.value.onstop = async () => {
      const mimeType = mediaRecorder.value.mimeType || 'audio/webm';
      const audioBlob = new Blob(audioChunks.value, { type: mimeType });
      recordedAudioUrl.value = URL.createObjectURL(audioBlob);
      
      // Convert to base64
      const arrayBuffer = await audioBlob.arrayBuffer();
      const base64 = btoa(
        new Uint8Array(arrayBuffer).reduce((data, byte) => data + String.fromCharCode(byte), '')
      );
      audioData.value = base64;
      selectedFileName.value = ''; // Clear file selection
      
      // Auto-fill sample name if empty
      if (!sampleName.value.trim()) {
        const timestamp = new Date().toLocaleString('cs-CZ');
        sampleName.value = `Recorded ${timestamp}`;
      }
      
      console.log('Audio recorded:', {
        size: audioBlob.size,
        type: mimeType,
        base64Length: base64.length,
        hasData: !!audioData.value
      });
      
      // Stop all tracks
      stream.getTracks().forEach(track => track.stop());
    };
    
    mediaRecorder.value.start();
    isRecording.value = true;
    recordingDuration.value = 0;
    
    recordingInterval.value = setInterval(() => {
      recordingDuration.value++;
    }, 1000);
  } catch (err) {
    uploadError.value = 'Failed to access microphone: ' + err.message;
  }
}

function stopRecording() {
  if (mediaRecorder.value && isRecording.value) {
    mediaRecorder.value.stop();
    isRecording.value = false;
    if (recordingInterval.value) {
      clearInterval(recordingInterval.value);
    }
  }
}

// Upload sample
async function uploadSample() {
  if (!audioData.value || !sampleName.value.trim()) return;
  
  uploading.value = true;
  uploadError.value = '';
  uploadSuccess.value = '';
  
  try {
    await axios.post(`${API_BASE}/v1/voice-samples`, {
      name: sampleName.value,
      audio_base64: audioData.value
    });
    
    uploadSuccess.value = 'Voice sample uploaded successfully!';
    
    // Reset form
    audioData.value = '';
    sampleName.value = '';
    selectedFileName.value = '';
    recordedAudioUrl.value = '';
    recordingDuration.value = 0;
    if (fileInput.value) {
      fileInput.value.value = '';
    }
    
    // Reload samples list
    await loadSamples();
    
    setTimeout(() => {
      uploadSuccess.value = '';
    }, 3000);
  } catch (err) {
    uploadError.value = err?.response?.data?.detail || err.message || 'Upload failed';
  } finally {
    uploading.value = false;
  }
}

// Load samples
async function loadSamples() {
  loading.value = true;
  samplesError.value = '';
  
  try {
    const res = await axios.get(`${API_BASE}/v1/voice-samples`);
    samples.value = res.data.samples;
  } catch (err) {
    samplesError.value = err?.response?.data?.detail || err.message || 'Failed to load samples';
  } finally {
    loading.value = false;
  }
}

// Delete sample
async function deleteSample(id) {
  if (!confirm('Are you sure you want to delete this voice sample?')) return;
  
  deleting.value = id;
  
  try {
    await axios.delete(`${API_BASE}/v1/voice-samples/${id}`);
    await loadSamples();
  } catch (err) {
    samplesError.value = err?.response?.data?.detail || err.message || 'Failed to delete sample';
  } finally {
    deleting.value = null;
  }
}

// Utility functions
function formatDate(isoString) {
  return new Date(isoString).toLocaleString();
}

function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

// Lifecycle
onMounted(() => {
  loadSamples();
});

onUnmounted(() => {
  if (recordingInterval.value) {
    clearInterval(recordingInterval.value);
  }
  if (recordedAudioUrl.value) {
    URL.revokeObjectURL(recordedAudioUrl.value);
  }
});
</script>

<style scoped>
.page {
  max-width: 900px;
  margin: 2rem auto;
  padding: 1rem;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

.back-link {
  color: #4a90e2;
  text-decoration: none;
  font-weight: 500;
}

.back-link:hover {
  text-decoration: underline;
}

section {
  background: #f9f9f9;
  padding: 1.5rem;
  border-radius: 8px;
  margin-bottom: 2rem;
}

h2 {
  margin-top: 0;
  margin-bottom: 1rem;
  color: #333;
}

.upload-methods {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2rem;
  margin-bottom: 1.5rem;
}

.upload-method h3 {
  margin-top: 0;
  margin-bottom: 1rem;
  font-size: 1rem;
  color: #555;
}

.file-label {
  display: block;
}

.file-label input[type="file"] {
  display: none;
}

.file-button {
  display: inline-block;
  padding: 0.75rem 1.5rem;
  background: #4a90e2;
  color: white;
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.2s;
}

.file-button:hover {
  background: #357abd;
}

.file-name {
  margin-top: 0.5rem;
  font-size: 0.9rem;
  color: #666;
}

.record-button {
  padding: 0.75rem 1.5rem;
  background: #e74c3c;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font: inherit;
  transition: background 0.2s;
}

.record-button:hover:not(:disabled) {
  background: #c0392b;
}

.record-button.recording {
  background: #e67e22;
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

.record-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.recording-duration {
  margin-top: 0.5rem;
  font-weight: bold;
  color: #e74c3c;
}

.audio-preview {
  margin-top: 1rem;
  width: 100%;
  max-width: 300px;
}

.ready-indicator {
  margin-top: 0.5rem;
  color: #27ae60;
  font-weight: 500;
  font-size: 0.9rem;
}

.name-input-section {
  display: flex;
  gap: 1rem;
  align-items: flex-end;
}

.name-input-section label {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.name-input-section input {
  width: 100%;
  padding: 0.75rem;
  font: inherit;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.upload-button {
  padding: 0.75rem 1.5rem;
  background: #27ae60;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font: inherit;
  white-space: nowrap;
  transition: background 0.2s;
}

.upload-button:hover:not(:disabled) {
  background: #229954;
}

.upload-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.error {
  color: #e74c3c;
  margin-top: 1rem;
}

.success {
  color: #27ae60;
  margin-top: 1rem;
  font-weight: 500;
}

.loading {
  color: #666;
  font-style: italic;
}

.no-samples {
  text-align: center;
  padding: 2rem;
  color: #999;
}

.samples-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.sample-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background: white;
  border-radius: 6px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.sample-info h3 {
  margin: 0 0 0.25rem 0;
  font-size: 1.1rem;
  color: #333;
}

.sample-meta {
  margin: 0;
  font-size: 0.85rem;
  color: #999;
}

.delete-button {
  padding: 0.5rem 1rem;
  background: #e74c3c;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font: inherit;
  transition: background 0.2s;
}

.delete-button:hover:not(:disabled) {
  background: #c0392b;
}

.delete-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

@media (max-width: 768px) {
  .upload-methods {
    grid-template-columns: 1fr;
  }
  
  .name-input-section {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
