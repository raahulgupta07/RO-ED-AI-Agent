<script lang="ts">
  type StepStatus = 'pending' | 'running' | 'done' | 'error';

  type PipelineStep = {
    id: string;
    label: string;
    icon: string;
    status: StepStatus;
    detail: string;
    time: string;
  };

  let {
    steps = $bindable([] as PipelineStep[]),
    filename = '',
    complete = false,
    summary = null as { items: number; accuracy: number; cost: number; duration: number; corrections: number; aiTables: number; declFilled: number } | null,
  } = $props();

  let spinnerFrame = $state(0);
  const spinnerChars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'];

  $effect(() => {
    if (!complete && steps.some(s => s.status === 'running')) {
      const interval = setInterval(() => { spinnerFrame++; }, 80);
      return () => clearInterval(interval);
    }
  });

  const spinner = $derived(spinnerChars[spinnerFrame % spinnerChars.length]);

  function statusIcon(s: StepStatus): string {
    if (s === 'done') return '✓';
    if (s === 'running') return spinner;
    if (s === 'error') return '✗';
    return '·';
  }

  function statusColor(s: StepStatus): string {
    if (s === 'done') return '#22c55e';
    if (s === 'running') return '#38bdf8';
    if (s === 'error') return '#ef4444';
    return '#374151';
  }
</script>

<div style="border: 2px solid #383832; background: #0a0a0f; font-family: 'SF Mono', 'Cascadia Code', 'Fira Code', monospace; font-size: 11px; color: #6b7280;">

  <!-- Header -->
  <div style="padding: 8px 14px; border-bottom: 1px solid #1a1a2e; display: flex; justify-content: space-between; align-items: center;">
    <div style="display: flex; align-items: center; gap: 8px;">
      <span style="color: #22c55e; font-size: 8px;">●</span>
      <span style="color: #4b5563; font-size: 10px; font-weight: bold;">RO-ED AI PIPELINE</span>
      <span style="color: #eab308; font-size: 10px;">{filename}</span>
    </div>
    {#if !complete && steps.some(s => s.status === 'running')}
      <span style="color: #38bdf8; font-size: 9px;">{spinner} PROCESSING</span>
    {:else if complete}
      <span style="color: #22c55e; font-size: 9px;">● COMPLETE</span>
    {/if}
  </div>

  <!-- Flow Diagram -->
  <div style="padding: 12px 14px;">

    <!-- Step nodes as horizontal flow -->
    <div style="display: flex; flex-wrap: wrap; gap: 4px 2px; align-items: center;">
      {#each steps as step, i}
        <div style="display: flex; align-items: center; gap: 2px;">
          <!-- Step box -->
          <div style="
            border: 1px solid {statusColor(step.status)};
            padding: 4px 8px;
            min-width: 70px;
            {step.status === 'running' ? `box-shadow: 0 0 8px ${statusColor(step.status)}40;` : ''}
            {step.status === 'done' ? 'opacity: 0.85;' : ''}
          ">
            <div style="display: flex; align-items: center; gap: 4px;">
              <span style="color: {statusColor(step.status)}; font-size: 10px;">{statusIcon(step.status)}</span>
              <span style="color: {step.status === 'running' ? '#e5e7eb' : statusColor(step.status)}; font-size: 9px; font-weight: bold;">{step.icon} {step.label}</span>
            </div>
            {#if step.detail}
              <div style="color: #4b5563; font-size: 8px; margin-top: 2px;">{step.detail}</div>
            {/if}
            {#if step.time}
              <div style="color: #374151; font-size: 8px;">{step.time}</div>
            {/if}
          </div>
          <!-- Arrow -->
          {#if i < steps.length - 1}
            <span style="color: {step.status === 'done' ? '#22c55e' : '#1a1a2e'}; font-size: 10px;">→</span>
          {/if}
        </div>
      {/each}
    </div>

    <!-- Progress bar -->
    {#if steps.length > 0}
      {@const doneCount = steps.filter(s => s.status === 'done').length}
      {@const totalSteps = steps.length}
      <div style="margin-top: 8px; display: flex; align-items: center; gap: 6px;">
        <div style="flex: 1; height: 3px; background: #1a1a2e; border-radius: 2px;">
          <div style="width: {(doneCount / totalSteps) * 100}%; height: 100%; background: #22c55e; border-radius: 2px; transition: width 0.3s;"></div>
        </div>
        <span style="color: #374151; font-size: 9px;">{doneCount}/{totalSteps}</span>
      </div>
    {/if}

    <!-- Completion summary -->
    {#if complete && summary}
      <div style="margin-top: 10px; border: 1px solid #14532d; background: #052e16; padding: 8px 12px;">
        <div style="color: #22c55e; font-weight: bold; font-size: 11px;">✅ EXTRACTION COMPLETE</div>
        <div style="margin-top: 6px; display: grid; grid-template-columns: repeat(3, 1fr); gap: 2px 12px; font-size: 10px;">
          <div style="color: #4b5563;">Declaration <span style="color: #d1d5db; font-weight: bold;">{summary.declFilled}/16</span></div>
          <div style="color: #4b5563;">Items <span style="color: #d1d5db; font-weight: bold;">{summary.items}</span></div>
          <div style="color: #4b5563;">AI Tables <span style="color: #d1d5db; font-weight: bold;">{summary.aiTables}</span></div>
          <div style="color: #4b5563;">Accuracy <span style="color: #22c55e; font-weight: bold;">{summary.accuracy.toFixed(1)}%</span></div>
          <div style="color: #4b5563;">Cost <span style="color: #eab308;">${summary.cost.toFixed(3)}</span></div>
          <div style="color: #4b5563;">Time <span style="color: #9ca3af;">{summary.duration.toFixed(1)}s</span></div>
        </div>
        {#if summary.corrections > 0}
          <div style="margin-top: 4px; color: #eab308; font-size: 9px;">✦ Verifier fixed {summary.corrections} values</div>
        {/if}
      </div>
    {/if}
  </div>
</div>
