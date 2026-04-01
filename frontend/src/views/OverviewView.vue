<script setup lang="ts">
import { onMounted } from "vue";
import { useRoute } from "vue-router";
import { useCaseStore } from "@/stores/caseStore";

const route = useRoute();
const store = useCaseStore();

onMounted(() => {
  const caseId = Number(route.params.caseId);
  if (!isNaN(caseId)) {
    store.fetchRuns(caseId);
  }
});
</script>

<template>
  <div class="page">
    <h1>Case Overview</h1>
    <div v-if="store.currentCase">
      <p><strong>Label:</strong> {{ store.currentCase.label }}</p>
      <p><strong>Created:</strong> {{ store.currentCase.created_at }}</p>
    </div>
    <h2>Analysis Runs</h2>
    <p v-if="store.currentRuns.length === 0">No runs yet.</p>
    <ul v-else>
      <li v-for="r in store.currentRuns" :key="r.id">
        Run #{{ r.id }} — {{ r.status }} ({{ r.created_at }})
      </li>
    </ul>
  </div>
</template>
