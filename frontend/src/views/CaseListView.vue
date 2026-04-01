<script setup lang="ts">
import { onMounted } from "vue";
import { useCaseStore } from "@/stores/caseStore";

const store = useCaseStore();

onMounted(() => {
  store.fetchCases();
});
</script>

<template>
  <div class="page">
    <h1>Cases</h1>
    <p v-if="store.loading">Loading cases...</p>
    <p v-else-if="store.error">Error: {{ store.error }}</p>
    <p v-else-if="store.cases.length === 0">No cases yet. Create one to get started.</p>
    <ul v-else>
      <li v-for="c in store.cases" :key="c.id">
        <router-link :to="{ name: 'case-overview', params: { caseId: c.id } }">
          {{ c.label }}
        </router-link>
        <span class="meta"> — {{ c.created_at }}</span>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.meta {
  color: #666;
  font-size: 0.85rem;
}
</style>
