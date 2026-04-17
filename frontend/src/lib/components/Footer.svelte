<script lang="ts">
  let {
    pipelineStatus = 'IDLE',
    model = 'GEMINI-3.1-FLASH-LITE',
    totalJobs = 0,
    totalCost = 0,
  } = $props();
</script>

<footer class="fixed bottom-0 left-0 w-full h-10 z-50 flex items-stretch overflow-hidden"
        style="background: var(--surface); border-top: 3px solid var(--on-surface);">
  <!-- SYS_OK segment -->
  <div class="flex items-center px-4 h-full font-mono text-[11px] font-bold tracking-widest uppercase text-white"
       style="background: var(--primary); border-right: 2px solid var(--on-surface);">
    SYS_OK
  </div>

  <!-- Pipeline status -->
  <div class="flex items-center px-4 h-full font-mono text-[11px] font-bold tracking-widest uppercase"
       style="color: var(--on-surface); border-right: 2px solid var(--on-surface);">
    PIPELINE: {pipelineStatus}
  </div>

  <!-- Model -->
  <div class="flex items-center px-4 h-full font-mono text-[11px] font-bold tracking-widest uppercase"
       style="color: var(--on-surface); border-right: 2px solid var(--on-surface);">
    MODEL: {model}
  </div>

  <!-- DB status -->
  <div class="flex items-center px-4 h-full font-mono text-[11px] font-bold tracking-widest uppercase"
       style="color: var(--on-surface); border-right: 2px solid var(--on-surface);">
    DB: WAL_ACTIVE
  </div>

  <!-- Jobs + Cost -->
  <div class="flex items-center px-4 h-full font-mono text-[11px] font-bold tracking-widest uppercase"
       style="color: var(--on-surface); border-right: 2px solid var(--on-surface);">
    JOBS: {totalJobs}
  </div>
  <div class="flex items-center px-4 h-full font-mono text-[11px] font-bold tracking-widest uppercase"
       style="color: #fbbf24; border-right: 2px solid var(--on-surface);">
    COST: ${totalCost.toFixed(3)}
  </div>

  <!-- Spacer -->
  <div class="flex-1"></div>

  <!-- LIVE_FEED -->
  <div class="flex items-center px-4 h-full">
    <span class="text-[10px] font-bold uppercase text-white animate-pulse px-2 py-0.5"
          style="background: var(--tertiary); border: 1px solid var(--on-surface);">
      LIVE_FEED
    </span>
  </div>
</footer>
