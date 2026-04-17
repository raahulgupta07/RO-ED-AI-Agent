<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api';
  import { auth } from '$lib/stores/auth.svelte';
  import ChapterHeading from '$lib/components/ChapterHeading.svelte';
  import DataTable from '$lib/components/DataTable.svelte';
  import Button from '$lib/components/Button.svelte';

  let declarations = $state<any[]>([]);
  let loading = $state(true);
  let searchQuery = $state('');
  let dateFrom = $state('');
  let dateTo = $state('');

  const columns = [
    { key: 'job_id', label: 'Job' },
    { key: 'declaration_no', label: 'Declaration No' },
    { key: 'declaration_date', label: 'Date' },
    { key: 'importer_name', label: 'Importer' },
    { key: 'consignor_name', label: 'Consignor' },
    { key: 'currency', label: 'Currency' },
    { key: 'total_customs_value', label: 'Customs Value', align: 'right' as const },
    { key: 'import_export_customs_duty', label: 'Duty', align: 'right' as const },
    { key: 'commercial_tax_ct', label: 'Tax', align: 'right' as const },
    { key: 'advance_income_tax_at', label: 'Income Tax', align: 'right' as const },
    { key: 'security_fee_sf', label: 'Security', align: 'right' as const },
    { key: 'maccs_service_fee_mf', label: 'MACCS', align: 'right' as const },
    { key: 'created_at', label: 'Processed' },
  ];

  const filteredDeclarations = $derived(() => {
    let result = declarations.map(d => ({
      ...d,
      total_customs_value: d.total_customs_value != null ? d.total_customs_value.toLocaleString() : '—',
      import_export_customs_duty: d.import_export_customs_duty != null ? d.import_export_customs_duty.toLocaleString() : '—',
      commercial_tax_ct: d.commercial_tax_ct != null ? d.commercial_tax_ct.toLocaleString() : '—',
      advance_income_tax_at: d.advance_income_tax_at != null ? d.advance_income_tax_at.toLocaleString() : '—',
      security_fee_sf: d.security_fee_sf != null ? d.security_fee_sf.toLocaleString() : '—',
      maccs_service_fee_mf: d.maccs_service_fee_mf != null ? d.maccs_service_fee_mf.toLocaleString() : '—',
    }));
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      result = result.filter(d =>
        d.declaration_no?.toLowerCase().includes(q) ||
        d.importer_name?.toLowerCase().includes(q) ||
        d.consignor_name?.toLowerCase().includes(q) ||
        d.job_id?.toLowerCase().includes(q)
      );
    }
    if (dateFrom) {
      result = result.filter(d => (d.declaration_date || d.created_at || '').split(' ')[0] >= dateFrom);
    }
    if (dateTo) {
      result = result.filter(d => (d.declaration_date || d.created_at || '').split(' ')[0] <= dateTo);
    }
    return result;
  });

  async function downloadExcel() {
    try {
      const res = await fetch('/api/data/declarations/download', {
        headers: { 'Authorization': `Bearer ${auth.token}` },
      });
      if (!res.ok) return;
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'all_declarations.xlsx';
      a.click();
      URL.revokeObjectURL(url);
    } catch {}
  }

  function clearFilters() {
    searchQuery = '';
    dateFrom = '';
    dateTo = '';
  }

  onMount(async () => {
    try { declarations = await api.listDeclarations(); } catch {}
    loading = false;
  });
</script>

<ChapterHeading
  icon="receipt_long"
  title="DECLARATION_DATA"
  subtitle="Consolidated customs declarations across all jobs"
  question="What are the customs values and duties?"
/>

<!-- Filters -->
<div class="flex flex-wrap gap-3 items-end mb-4">
  <div class="flex-1 min-w-[200px]">
    <input type="text" placeholder="Search declaration no, importer, consignor..."
           bind:value={searchQuery}
           class="w-full text-xs font-bold uppercase px-3 py-2 focus:outline-none"
           style="border: 2px solid var(--on-surface); background: white; color: var(--on-surface);" />
  </div>
  <div>
    <div class="tag-label mb-1 text-[8px]">FROM</div>
    <input type="date" bind:value={dateFrom}
           class="text-[10px] font-mono px-2 py-1.5 focus:outline-none"
           style="border: 2px solid var(--on-surface); background: white; color: var(--on-surface);" />
  </div>
  <div>
    <div class="tag-label mb-1 text-[8px]">TO</div>
    <input type="date" bind:value={dateTo}
           class="text-[10px] font-mono px-2 py-1.5 focus:outline-none"
           style="border: 2px solid var(--on-surface); background: white; color: var(--on-surface);" />
  </div>
  {#if searchQuery || dateFrom || dateTo}
    <button class="text-[8px] font-black uppercase px-2 py-1.5 cursor-pointer"
            style="border: 1px solid var(--outline); color: var(--outline); background: transparent;"
            onclick={clearFilters}>CLEAR</button>
  {/if}
  <Button variant="secondary" size="sm" onclick={downloadExcel}>
    <span class="flex items-center gap-1">
      <span class="material-symbols-outlined text-xs">download</span> DOWNLOAD_XLSX
    </span>
  </Button>
</div>

{#if loading}
  <div class="skeleton h-64 w-full"></div>
{:else}
  <DataTable title="CUSTOMS_DECLARATIONS" count={filteredDeclarations().length} {columns} rows={filteredDeclarations()} />
{/if}
