<script lang="ts">
  let {
    text = '',
    variant = 'info' as 'critical' | 'warning' | 'info' | 'success' | 'normal' | 'secondary' | 'tertiary',
    size = 'sm' as 'sm' | 'md',
  } = $props();

  const colorMap: Record<string, string> = {
    critical: '#be2d06',
    warning: '#ff9d00',
    info: '#65655e',
    success: '#007518',
    normal: '#9d9d91',
    secondary: '#006f7c',
    tertiary: '#9d4867',
  };

  const bg = $derived(colorMap[variant] || '#65655e');
  const pad = $derived(size === 'sm' ? 'padding: 2px 6px; font-size: 9px;' : 'padding: 2px 10px; font-size: 0.75rem;');
</script>

<span
  class="inline-block font-black uppercase text-white"
  style="{pad} background: {bg};"
>
  {text}
</span>
