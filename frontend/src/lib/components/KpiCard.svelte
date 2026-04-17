<script lang="ts">
  let {
    title = '',
    value = '',
    unit = '',
    subtitle = '',
    icon = '',
    progress = -1,
    accent = '#007518',
  } = $props();
</script>

<div class="ink-border stamp-shadow bg-white p-4">
  <div class="flex justify-between items-start mb-2">
    <span class="tag-label">{title}</span>
    {#if icon}
      <span class="material-symbols-outlined text-lg" style="color: {accent};">{icon}</span>
    {/if}
  </div>

  <div class="text-4xl font-black tracking-tighter" style="color: var(--on-surface);">
    {value}{#if unit}<span class="text-lg">{unit}</span>{/if}
  </div>

  {#if progress >= 0}
    <div class="mt-3 h-2 border border-[var(--on-surface)]" style="background: var(--surface-container-highest);">
      <div class="h-full transition-all" style="width: {Math.min(progress, 100)}%; background: {accent};"></div>
    </div>
  {/if}

  {#if subtitle}
    <div class="mt-2 text-[10px] uppercase opacity-60 font-bold" style="color: var(--on-surface);">
      {subtitle}
    </div>
  {/if}
</div>
