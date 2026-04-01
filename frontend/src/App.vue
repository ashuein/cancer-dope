<script setup lang="ts">
import { RouterView } from "vue-router";
</script>

<template>
  <div id="app-root">
    <header>
      <nav>
        <router-link to="/" class="brand">PrecisionOncology</router-link>
      </nav>
    </header>
    <main>
      <RouterView />
    </main>
  </div>
</template>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

#app-root {
  font-family: system-ui, -apple-system, sans-serif;
  color: #1a1a2e;
}

header {
  background: #16213e;
  padding: 0.75rem 1.5rem;
}

nav {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.brand {
  color: #e2e8f0;
  text-decoration: none;
  font-size: 1rem;
  font-weight: 600;
  letter-spacing: 0.02em;
}

main {
  padding: 1.5rem;
  max-width: 1400px;
  margin: 0 auto;
}
</style>
