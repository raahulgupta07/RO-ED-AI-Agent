<script lang="ts">
  let {
    filename = '',
    lines = [] as { text: string; type: string }[],
    running = false,
    summary = null as any,
  } = $props();

  let terminal: HTMLDivElement;

  // Auto-scroll to bottom on new lines
  $effect(() => {
    if (lines.length && terminal) {
      requestAnimationFrame(() => { terminal.scrollTop = terminal.scrollHeight; });
    }
  });

  // Spinner animation
  let frame = $state(0);
  const spinChars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'];
  const spin = $derived(spinChars[frame % spinChars.length]);

  $effect(() => {
    if (running) {
      const iv = setInterval(() => { frame++; }, 80);
      return () => clearInterval(iv);
    }
  });

  function lineColor(type: string): string {
    if (type === 'success') return '#22c55e';
    if (type === 'warning') return '#eab308';
    if (type === 'error') return '#ef4444';
    if (type === 'data') return '#6b7280';
    if (type === 'header') return '#e5e7eb';
    return '#9ca3af';
  }
</script>

<div style="border: 2px solid #383832; box-shadow: 4px 4px 0px 0px #383832;">
  <!-- Title bar -->
  <div style="background: #111118; border-bottom: 1px solid #1a1a2e; padding: 6px 12px; display: flex; align-items: center; justify-content: space-between;">
    <div style="display: flex; align-items: center; gap: 8px;">
      <div style="display: flex; gap: 4px;">
        <span style="width: 8px; height: 8px; border-radius: 50%; background: #ef4444; display: inline-block;"></span>
        <span style="width: 8px; height: 8px; border-radius: 50%; background: #eab308; display: inline-block;"></span>
        <span style="width: 8px; height: 8px; border-radius: 50%; background: #22c55e; display: inline-block;"></span>
      </div>
      <span style="color: #4b5563; font-family: monospace; font-size: 10px; font-weight: bold;">
        ro-ed-agent — {filename || 'idle'}
      </span>
    </div>
    <div style="display: flex; align-items: center; gap: 12px; font-family: monospace; font-size: 9px;">
      {#if running}
        <span style="color: #38bdf8;">{spin} RUNNING</span>
      {:else if summary}
        <span style="color: #22c55e;">● DONE</span>
      {/if}
    </div>
  </div>

  <!-- Terminal body -->
  <div
    bind:this={terminal}
    style="
      background: #0a0a0f;
      height: 520px;
      overflow-y: auto;
      font-family: 'SF Mono', 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
      font-size: 11px;
      line-height: 1.6;
      padding: 12px 14px;
      color: #9ca3af;
    "
  >
    <!-- Each log line -->
    {#each lines as line, i}
      {#if line.type === 'header'}
        <div style="color: #1e1e2e; margin-top: 6px;">────────────────────────────────────────────</div>
        <div style="color: #e5e7eb; font-weight: bold; margin-bottom: 2px;">{line.text}</div>
      {:else if line.type === 'success' && line.text.includes('═')}
        <div style="color: #22c55e; font-weight: bold; margin-top: 8px;">{line.text}</div>
      {:else if line.type === 'success'}
        <div style="color: #22c55e;">{line.text}</div>
      {:else if line.type === 'warning'}
        <div style="color: #eab308;">{line.text}</div>
      {:else if line.type === 'error'}
        <div style="color: #ef4444;">{line.text}</div>
      {:else if line.type === 'data'}
        <div style="color: #6b7280; padding-left: 4px;">{line.text}</div>
      {:else}
        <div style="color: #9ca3af;">{line.text}</div>
      {/if}
    {/each}

    <!-- Animated spinner + cursor while running -->
    {#if running}
      <div style="margin-top: 4px; display: flex; align-items: center; gap: 8px;">
        <span style="color: #38bdf8; font-size: 13px;">{spin}</span>
        <span style="color: #38bdf8; font-size: 10px;">Processing...</span>
        <span class="animate-pulse" style="display: inline-block; width: 6px; height: 12px; background: #38bdf8;"></span>
      </div>
    {/if}

    <!-- Completion box -->
    {#if summary && !running}
      <div style="margin-top: 8px; border: 1px solid #14532d; background: #052e16; padding: 8px 12px;">
        <div style="color: #22c55e; font-weight: bold; font-size: 11px;">✓ EXTRACTION COMPLETE</div>
        <div style="margin-top: 4px; color: #4b5563; font-size: 10px; display: grid; grid-template-columns: repeat(3, 1fr); gap: 1px 12px;">
          <div>Items <span style="color: #d1d5db; font-weight: bold;">{summary.items}</span></div>
          <div>Accuracy <span style="color: {summary.accuracy >= 90 ? '#22c55e' : '#eab308'}; font-weight: bold;">{summary.accuracy?.toFixed(1)}%</span></div>
          <div>Status <span style="color: #22c55e;">ACCEPTED</span></div>
          <div>Time <span style="color: #9ca3af;">{summary.duration?.toFixed(1)}s</span></div>
          <div>Cost <span style="color: #eab308;">${summary.cost?.toFixed(3)}</span></div>
          <div>Model <span style="color: #a78bfa;">gemini-flash-lite</span></div>
        </div>
      </div>
    {/if}

    <div style="height: 1px;"></div>
  </div>
</div>
