<template>
  <router-view />
</template>

<script setup>
</script>

<style>
* {
  box-sizing: border-box;
}

body {
  margin: 0;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  background: #fff;
}

#app {
  min-height: 100vh;
}

label {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  font-weight: 500;
}
</style>
