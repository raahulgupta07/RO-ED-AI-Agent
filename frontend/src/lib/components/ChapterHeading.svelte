<script lang="ts">
  let {
    icon = '',
    title = '',
    subtitle = '',
    question = '',
  } = $props();
</script>

<div class="mb-3" style="background: var(--on-surface); color: var(--surface);">
  <div class="px-4 py-3 flex items-center gap-3">
    {#if icon}
      <span class="material-symbols-outlined text-2xl" style="color: #ff9d00;">{icon}</span>
    {/if}
    <div>
      <div class="font-black uppercase text-sm">{title}</div>
      {#if subtitle}
        <div class="text-[10px] opacity-75">{subtitle}</div>
      {/if}
    </div>
  </div>
  {#if question}
    <div class="px-4 pb-3 font-mono text-xs" style="padding-left: 52px; color: #00fc40;">
      ? {question}
    </div>
  {/if}
</div>
