<script lang="ts">
  let {
    label = '',
    type = 'text' as 'text' | 'password' | 'email' | 'number',
    placeholder = '',
    value = $bindable(''),
    disabled = false,
  } = $props();
</script>

<div>
  {#if label}
    <div class="tag-label mb-1">{label}</div>
  {/if}
  <input
    {type}
    {placeholder}
    {disabled}
    bind:value
    class="w-full font-bold text-sm focus:outline-none"
    style="
      padding: 12px 16px;
      font-family: 'Space Grotesk', sans-serif;
      background: {disabled ? 'var(--surface-container-highest)' : 'white'};
      border: 2px solid var(--on-surface);
      color: {disabled ? 'var(--outline)' : 'var(--on-surface)'};
      {disabled ? 'cursor: not-allowed;' : ''}
    "
  />
</div>
