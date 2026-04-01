<script setup lang="ts">
import { onMounted, watch } from "vue";
import { useRoute } from "vue-router";
import { useCaseStore } from "@/stores/caseStore";

const props = defineProps<{ caseId: string }>();
const route = useRoute();
const store = useCaseStore();

async function loadCase() {
  const id = Number(props.caseId);
  if (!isNaN(id)) {
    await store.fetchCase(id);
  }
}

onMounted(loadCase);
watch(() => props.caseId, loadCase);
</script>

<template>
  <div>
    <nav class="case-nav">
      <router-link :to="{ name: 'case-list' }">All Cases</router-link>
      <span class="sep">/</span>
      <span class="case-label">{{ store.currentCase?.label ?? `Case ${caseId}` }}</span>
      <span class="sep">|</span>
      <router-link :to="{ name: 'case-overview', params: { caseId } }">Overview</router-link>
      <router-link :to="{ name: 'case-timeline', params: { caseId } }">Timeline</router-link>
      <router-link :to="{ name: 'case-track1', params: { caseId } }">Track 1</router-link>
      <router-link :to="{ name: 'case-track2', params: { caseId } }">Track 2</router-link>
      <router-link :to="{ name: 'case-bulk-rna', params: { caseId } }">Bulk RNA</router-link>
      <router-link :to="{ name: 'case-scrna', params: { caseId } }">scRNA</router-link>
      <router-link :to="{ name: 'case-gsea', params: { caseId } }">GSEA</router-link>
      <router-link :to="{ name: 'case-cnv', params: { caseId } }">CNV</router-link>
      <router-link :to="{ name: 'case-bam', params: { caseId } }">BAM</router-link>
      <router-link :to="{ name: 'case-vaccines', params: { caseId } }">Vaccines</router-link>
      <router-link :to="{ name: 'case-imaging', params: { caseId } }">Imaging</router-link>
      <router-link :to="{ name: 'case-spatial', params: { caseId } }">Spatial</router-link>
      <router-link :to="{ name: 'case-catalog', params: { caseId } }">Catalog</router-link>
    </nav>
    <router-view />
  </div>
</template>

<style scoped>
.case-nav {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
  padding: 0.5rem 0;
  margin-bottom: 1rem;
  border-bottom: 1px solid #e2e8f0;
  font-size: 0.875rem;
}

.case-nav a {
  color: #4a6fa5;
  text-decoration: none;
  padding: 0.2rem 0.4rem;
  border-radius: 3px;
}

.case-nav a:hover,
.case-nav a.router-link-exact-active {
  background: #e8eef6;
  color: #16213e;
}

.sep {
  color: #cbd5e1;
}

.case-label {
  font-weight: 600;
  color: #1a1a2e;
}
</style>
