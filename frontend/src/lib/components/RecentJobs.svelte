<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api';

  let {
    onselect = undefined as ((jobId: string) => void) | undefined,
  } = $props();

  let jobs = $state<any[]>([]);

  onMount(async () => {
    try {
      jobs = (await api.listJobs(5)).slice(0, 5);
    } catch {}
  });

  const decisionColor: Record<string, string> = {
    COMPLETED: '#007518',
    FAILED: '#be2d06',
    PROCESSING: '#006f7c',
  };
</script>

{#if jobs.length > 0}
  <div class="mt-4">
    <div class="tag-label mb-2">RECENT_JOBS</div>
    {#each jobs as job}
      <button
        class="w-full text-left px-2 py-1.5 border-b cursor-pointer transition-colors hover:opacity-80"
        style="border-color: rgba(56,56,50,0.1);"
        onclick={() => onselect?.(job.job_id)}
      >
        <div class="flex items-center justify-between">
          <span class="text-[10px] font-bold truncate flex-1" style="color: var(--on-surface);">
            {job.pdf_name}
          </span>
          <div class="flex items-center gap-2 ml-2">
            {#if job.accuracy_percent != null}
              <span class="text-[9px] font-mono font-bold" style="color: {job.accuracy_percent >= 90 ? '#007518' : job.accuracy_percent >= 60 ? '#ff9d00' : '#be2d06'};">
                {job.accuracy_percent.toFixed(1)}%
              </span>
            {/if}
            <span class="text-[8px] font-black uppercase px-1 py-0.5 text-white"
                  style="background: {decisionColor[job.status] || '#65655e'};">
              {job.status === 'COMPLETED' ? '✓' : job.status === 'FAILED' ? '✗' : '◉'}
            </span>
          </div>
        </div>
      </button>
    {/each}
  </div>
{/if}
