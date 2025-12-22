<script setup>
import ToastContainer from './components/layout/ToastContainer.vue';
import OfflineBanner from './components/layout/OfflineBanner.vue';
</script>

<template>
  <!-- Offline Banner (Global) -->
  <OfflineBanner />

  <!-- Toast Container (Global) -->
  <ToastContainer />

  <!-- Router View - handles all page routing -->
  <router-view />
</template>
