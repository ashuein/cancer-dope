import { defineStore } from "pinia";
import { ref } from "vue";
import apiClient from "@/api/client";
import type { Case, AnalysisRun } from "@/types";

export const useCaseStore = defineStore("case", () => {
  const cases = ref<Case[]>([]);
  const currentCase = ref<Case | null>(null);
  const currentRuns = ref<AnalysisRun[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);

  async function fetchCases() {
    loading.value = true;
    error.value = null;
    try {
      const { data } = await apiClient.get<Case[]>("/cases");
      cases.value = data;
    } catch (e: any) {
      error.value = e.message;
    } finally {
      loading.value = false;
    }
  }

  async function fetchCase(caseId: number) {
    loading.value = true;
    error.value = null;
    try {
      const { data } = await apiClient.get<Case>(`/cases/${caseId}`);
      currentCase.value = data;
    } catch (e: any) {
      error.value = e.message;
    } finally {
      loading.value = false;
    }
  }

  async function fetchRuns(caseId: number) {
    try {
      const { data } = await apiClient.get<AnalysisRun[]>(
        `/cases/${caseId}/runs`
      );
      currentRuns.value = data;
    } catch (e: any) {
      error.value = e.message;
    }
  }

  return { cases, currentCase, currentRuns, loading, error, fetchCases, fetchCase, fetchRuns };
});
