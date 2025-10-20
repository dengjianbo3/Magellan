<!-- src/components/GlassPaper.vue -->
<template>
  <div class="glass-paper">
    <slot></slot>
  </div>
</template>

<style scoped>
.glass-paper {
  /* The Glassmorphism Effect */
  background: var(--glass-bg);
  backdrop-filter: var(--glass-blur);
  -webkit-backdrop-filter: var(--glass-blur);

  /* Styling */
  border-radius: 16px;
  border: var(--glass-border);
  box-shadow: var(--glass-shadow);
  
  /* Content Padding */
  padding: 2rem;
}
</style>
