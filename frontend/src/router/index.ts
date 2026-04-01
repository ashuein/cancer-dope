import { createRouter, createWebHistory, type RouteRecordRaw } from "vue-router";

import CaseListView from "@/views/CaseListView.vue";
import CaseLayout from "@/views/CaseLayout.vue";
import OverviewView from "@/views/OverviewView.vue";
import TimelineView from "@/views/TimelineView.vue";
import Track1View from "@/views/Track1View.vue";
import Track2View from "@/views/Track2View.vue";
import BulkRnaView from "@/views/BulkRnaView.vue";
import ScRnaView from "@/views/ScRnaView.vue";
import GseaView from "@/views/GseaView.vue";
import CnvView from "@/views/CnvView.vue";
import BamView from "@/views/BamView.vue";
import VaccineView from "@/views/VaccineView.vue";
import ImagingView from "@/views/ImagingView.vue";
import SpatialView from "@/views/SpatialView.vue";
import CatalogView from "@/views/CatalogView.vue";

const routes: RouteRecordRaw[] = [
  { path: "/", name: "case-list", component: CaseListView },
  {
    path: "/cases/:caseId",
    component: CaseLayout,
    props: true,
    children: [
      { path: "", name: "case-overview", component: OverviewView },
      { path: "timeline", name: "case-timeline", component: TimelineView },
      { path: "track1", name: "case-track1", component: Track1View },
      { path: "track2", name: "case-track2", component: Track2View },
      { path: "bulk-rna", name: "case-bulk-rna", component: BulkRnaView },
      { path: "scrna", name: "case-scrna", component: ScRnaView },
      { path: "gsea", name: "case-gsea", component: GseaView },
      { path: "cnv", name: "case-cnv", component: CnvView },
      { path: "bam", name: "case-bam", component: BamView },
      { path: "vaccines", name: "case-vaccines", component: VaccineView },
      { path: "imaging", name: "case-imaging", component: ImagingView },
      { path: "spatial", name: "case-spatial", component: SpatialView },
      { path: "catalog", name: "case-catalog", component: CatalogView },
    ],
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;
