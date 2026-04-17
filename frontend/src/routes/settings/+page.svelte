<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api';
  import { auth } from '$lib/stores/auth.svelte';
  import ChapterHeading from '$lib/components/ChapterHeading.svelte';
  import DataTable from '$lib/components/DataTable.svelte';
  import FormInput from '$lib/components/FormInput.svelte';
  import Button from '$lib/components/Button.svelte';

  let users = $state<any[]>([]);
  let logs = $state<any[]>([]);
  let groups = $state<any[]>([]);
  let activeTab = $state<'users' | 'logs' | 'auth' | 'groups'>('users');
  let loading = $state(true);

  // Create user form
  let newUsername = $state('');
  let newPassword = $state('');
  let newDisplayName = $state('');
  let newRole = $state('user');
  let createError = $state('');
  let createSuccess = $state('');

  // Keycloak settings
  let kcRealmUrl = $state('');
  let kcClientId = $state('');
  let kcClientSecret = $state('');
  let kcAdminRole = $state('admin');
  let kcEnabled = $state(false);
  let kcSaving = $state(false);
  let kcTesting = $state(false);
  let kcMessage = $state('');
  let kcMessageType = $state<'success' | 'error' | ''>('');
  let kcTestResult = $state('');
  let kcTestType = $state<'success' | 'error' | ''>('');

  // Group editor
  let editingGroup = $state<any>(null);
  let groupName = $state('');
  let groupDesc = $state('');
  let groupPages = $state({ agent: true, history: true, items: true, declarations: true, costs: true, settings: false });
  let groupActions = $state({ run_pipeline: true, upload_pdf: true, download_excel: true, delete_jobs: false, export_data: true });
  let groupScope = $state('own');
  let groupMembers = $state<number[]>([]);
  let groupSaving = $state(false);
  let groupMessage = $state('');

  const userColumns = [
    { key: 'username', label: 'Username' },
    { key: 'role', label: 'Role' },
    { key: 'group_name', label: 'Group' },
    { key: 'auth_type', label: 'Auth' },
    { key: 'email', label: 'Email' },
    { key: 'created_at', label: 'Created' },
    { key: 'last_login', label: 'Login' },
  ];

  const logColumns = [
    { key: 'created_at', label: 'Timestamp' },
    { key: 'username', label: 'User' },
    { key: 'action', label: 'Action' },
    { key: 'detail', label: 'Details' },
  ];

  const userRows = $derived(users.map(u => ({
    ...u,
    auth_type: u.keycloak_id ? 'KEYCLOAK' : 'LOCAL',
    group_name: u.group_name || '—',
    email: u.email || '—',
    is_active: u.is_active ? 'ACTIVE' : 'DISABLED',
    created_at: (u.created_at || '').split('T')[0] || (u.created_at || '').split(' ')[0] || '',
    last_login: u.last_login ? ((u.last_login || '').split('T')[0] || (u.last_login || '').split(' ')[0]) : 'Never',
  })));

  const logRows = $derived(logs.map(l => ({
    ...l,
    created_at: l.created_at?.replace('T', ' ').slice(0, 19) ?? '',
  })));

  async function loadData() {
    loading = true;
    try { users = await api.listUsers(); } catch { users = []; }
    try { logs = await api.activityLogs(); } catch { logs = []; }
    try { groups = await api.listGroups(); } catch { groups = []; }
    loading = false;
  }

  async function loadKeycloakSettings() {
    try {
      const s = await api.getKeycloakSettings();
      kcRealmUrl = s.realm_url || '';
      kcClientId = s.client_id || '';
      kcClientSecret = s.client_secret || '';
      kcAdminRole = s.admin_role || 'admin';
      kcEnabled = s.enabled || false;
    } catch {}
  }

  async function createUser() {
    createError = '';
    createSuccess = '';
    try {
      await api.createUser({ username: newUsername, password: newPassword, display_name: newDisplayName, role: newRole });
      createSuccess = `User '${newUsername}' created`;
      newUsername = ''; newPassword = ''; newDisplayName = ''; newRole = 'user';
      await loadData();
    } catch (e: any) { createError = e.message; }
  }

  async function saveKeycloakSettings() {
    kcSaving = true; kcMessage = '';
    try {
      await api.saveKeycloakSettings({ realm_url: kcRealmUrl, client_id: kcClientId, client_secret: kcClientSecret, admin_role: kcAdminRole, enabled: kcEnabled });
      if (kcEnabled && (!kcRealmUrl.trim() || !kcClientId.trim())) {
        kcMessage = 'SAVED — will not activate until REALM_URL and CLIENT_ID are configured';
        kcMessageType = 'error';
      } else if (kcEnabled) {
        kcMessage = 'KEYCLOAK ENABLED — All users must authenticate via SSO';
        kcMessageType = 'success';
      } else {
        kcMessage = 'SETTINGS SAVED — Using local auth';
        kcMessageType = 'success';
      }
      await auth.fetchAuthConfig();
    } catch (e: any) { kcMessage = e.message || 'SAVE_FAILED'; kcMessageType = 'error'; }
    kcSaving = false;
  }

  async function testKeycloakConnection() {
    kcTesting = true; kcTestResult = '';
    try {
      const r = await api.testKeycloakConnection({ realm_url: kcRealmUrl, client_id: kcClientId, client_secret: kcClientSecret, admin_role: kcAdminRole, enabled: kcEnabled });
      kcTestResult = r.message; kcTestType = r.success ? 'success' : 'error';
    } catch (e: any) { kcTestResult = e.message || 'FAILED'; kcTestType = 'error'; }
    kcTesting = false;
  }

  // Group editor functions
  function startNewGroup() {
    editingGroup = { id: null };
    groupName = ''; groupDesc = '';
    groupPages = { agent: true, history: true, items: true, declarations: true, costs: true, settings: false };
    groupActions = { run_pipeline: true, upload_pdf: true, download_excel: true, delete_jobs: false, export_data: true };
    groupScope = 'own'; groupMembers = []; groupMessage = '';
  }

  async function editGroup(g: any) {
    editingGroup = g;
    groupName = g.name; groupDesc = g.description || '';
    groupPages = { agent: !!g.page_agent, history: !!g.page_history, items: !!g.page_items, declarations: !!g.page_declarations, costs: !!g.page_costs, settings: !!g.page_settings };
    groupActions = { run_pipeline: !!g.action_run_pipeline, upload_pdf: !!g.action_upload_pdf, download_excel: !!g.action_download_excel, delete_jobs: !!g.action_delete_jobs, export_data: !!g.action_export_data };
    groupScope = g.data_scope || 'own'; groupMessage = '';
    // Fetch members
    try {
      const full = await api.getGroup(g.id);
      groupMembers = (full.members || []).map((m: any) => m.id);
    } catch { groupMembers = []; }
  }

  async function saveGroup() {
    groupSaving = true; groupMessage = '';
    const data = {
      name: groupName, description: groupDesc,
      page_agent: groupPages.agent, page_history: groupPages.history, page_items: groupPages.items,
      page_declarations: groupPages.declarations, page_costs: groupPages.costs, page_settings: groupPages.settings,
      action_run_pipeline: groupActions.run_pipeline, action_upload_pdf: groupActions.upload_pdf,
      action_download_excel: groupActions.download_excel, action_delete_jobs: groupActions.delete_jobs,
      action_export_data: groupActions.export_data,
      data_scope: groupScope, member_ids: groupMembers,
    };
    try {
      if (editingGroup?.id) {
        await api.updateGroup(editingGroup.id, data);
        groupMessage = 'GROUP UPDATED';
      } else {
        await api.createGroup(data);
        groupMessage = 'GROUP CREATED';
      }
      await loadData();
    } catch (e: any) { groupMessage = e.message; }
    groupSaving = false;
  }

  async function deleteGroup() {
    if (!editingGroup?.id) return;
    try {
      await api.deleteGroup(editingGroup.id);
      editingGroup = null;
      await loadData();
    } catch (e: any) { groupMessage = e.message; }
  }

  function toggleMember(uid: number) {
    if (groupMembers.includes(uid)) groupMembers = groupMembers.filter(id => id !== uid);
    else groupMembers = [...groupMembers, uid];
  }



  onMount(() => { loadData(); loadKeycloakSettings(); });

  // Load data when switching to profiles/learning tabs
</script>

<ChapterHeading icon="settings" title="ADMIN_PANEL" subtitle="System settings, user management, and authentication" question="Configure the system" />

{#if !auth.isAdmin}
  <div class="p-8 text-center font-bold uppercase" style="color: var(--error);">ADMIN ACCESS REQUIRED</div>
{:else}
  <!-- Tab bar -->
  <div class="flex gap-0 mb-4 border-2" style="border-color: var(--on-surface); background: var(--surface-container-highest);">
    {#each [['users','USERS'],['logs','ACTIVITY_LOG'],['auth','AUTHENTICATION'],['groups','GROUPS']] as [key, label]}
      <button class="px-3 py-2 text-[11px] font-bold uppercase tracking-tight cursor-pointer"
        style="{activeTab === key ? 'background: var(--on-surface); color: var(--surface);' : 'color: var(--outline);'}"
        onclick={() => activeTab = key as any}
      >{label}</button>
    {/each}
  </div>

  {#if loading && !['auth','groups'].includes(activeTab)}
    <div class="skeleton h-64 w-full"></div>

  {:else if activeTab === 'users'}
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <div class="lg:col-span-2">
        <DataTable title="REGISTERED_USERS" count={users.length} columns={userColumns} rows={userRows} />
      </div>
      {#if !auth.isKeycloak}
        <div class="border-2 stamp-shadow" style="border-color: var(--on-surface);">
          <div class="dark-bar">CREATE_USER</div>
          <div class="bg-white p-3 space-y-3">
            {#if createError}<div class="p-2 text-xs font-bold uppercase text-white" style="background: var(--error);">{createError}</div>{/if}
            {#if createSuccess}<div class="p-2 text-xs font-bold uppercase text-white" style="background: var(--primary);">{createSuccess}</div>{/if}
            <FormInput label="USERNAME" bind:value={newUsername} placeholder="username" />
            <FormInput label="PASSWORD" type="password" bind:value={newPassword} placeholder="password" />
            <FormInput label="DISPLAY_NAME" bind:value={newDisplayName} placeholder="Display Name" />
            <div>
              <div class="tag-label mb-0.5">ROLE</div>
              <select bind:value={newRole} class="w-full px-2 py-1.5 text-sm font-bold uppercase border-2" style="border-color: var(--on-surface);">
                <option value="user">USER</option>
                <option value="admin">ADMIN</option>
              </select>
            </div>
            <Button variant="secondary" size="md" onclick={createUser}>CREATE_OPERATOR</Button>
          </div>
        </div>
      {:else}
        <div class="border-2 stamp-shadow" style="border-color: var(--on-surface);">
          <div class="dark-bar">AUTH_PROVIDER</div>
          <div class="bg-white p-3">
            <div class="flex items-center gap-2 mb-2">
              <span class="inline-block w-2 h-2" style="background: var(--primary);"></span>
              <span class="text-xs font-bold uppercase" style="color: var(--primary);">KEYCLOAK_ACTIVE</span>
            </div>
            <p class="text-[10px] font-bold uppercase" style="color: var(--outline);">Users auto-provisioned on first login via Keycloak.</p>
          </div>
        </div>
      {/if}
    </div>

  {:else if activeTab === 'logs'}
    <DataTable title="ACTIVITY_LOG" count={logs.length} columns={logColumns} rows={logRows} />

  {:else if activeTab === 'auth'}
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <!-- LEFT: Keycloak config form (2 cols wide) -->
      <div class="lg:col-span-2 border-2 stamp-shadow" style="border-color: var(--on-surface);">
        <div class="dark-bar flex items-center justify-between">
          <span>KEYCLOAK_CONFIGURATION</span>
          <button class="px-3 py-1 text-[10px] font-black uppercase cursor-pointer border-2"
            style="border-color: {kcEnabled ? 'white' : 'rgba(255,255,255,0.4)'}; background: {kcEnabled ? 'var(--primary)' : 'transparent'}; color: white;"
            onclick={() => kcEnabled = !kcEnabled}>{kcEnabled ? 'ENABLED' : 'DISABLED'}</button>
        </div>
        <div class="bg-white p-4">
          {#if kcMessage}<div class="mb-3 p-2 text-xs font-bold uppercase text-white border-2" style="background: {kcMessageType === 'success' ? 'var(--primary)' : 'var(--error)'}; border-color: var(--on-surface);">{kcMessage}</div>{/if}
          {#if kcTestResult}<div class="mb-3 p-2 text-xs font-bold uppercase border-2" style="background: {kcTestType === 'success' ? '#C6EFCE' : '#FFC7CE'}; border-color: var(--on-surface);">{kcTestResult}</div>{/if}
          <div class="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-3">
            <div>
              <div class="tag-label mb-0.5" style="font-size: 9px;">REALM_URL</div>
              <input bind:value={kcRealmUrl} placeholder="https://keycloak.example.com/realms/myapp" class="w-full font-bold text-sm focus:outline-none" style="padding: 8px 10px; font-family: 'Space Grotesk', sans-serif; background: white; border: 2px solid var(--on-surface);" />
            </div>
            <div>
              <div class="tag-label mb-0.5" style="font-size: 9px;">CLIENT_ID</div>
              <input bind:value={kcClientId} placeholder="ro-ed-frontend" class="w-full font-bold text-sm focus:outline-none" style="padding: 8px 10px; font-family: 'Space Grotesk', sans-serif; background: white; border: 2px solid var(--on-surface);" />
            </div>
            <div>
              <div class="tag-label mb-0.5" style="font-size: 9px;">CLIENT_SECRET <span style="color: var(--outline); font-weight: 500;">(optional)</span></div>
              <input bind:value={kcClientSecret} placeholder="Leave empty for public client (PKCE)" class="w-full font-bold text-sm focus:outline-none" style="padding: 8px 10px; font-family: 'Space Grotesk', sans-serif; background: white; border: 2px solid var(--on-surface);" />
            </div>
            <div>
              <div class="tag-label mb-0.5" style="font-size: 9px;">ADMIN_ROLE_NAME</div>
              <input bind:value={kcAdminRole} placeholder="admin" class="w-full font-bold text-sm focus:outline-none" style="padding: 8px 10px; font-family: 'Space Grotesk', sans-serif; background: white; border: 2px solid var(--on-surface);" />
            </div>
          </div>
          <div class="flex gap-3 mt-4">
            <button onclick={testKeycloakConnection} disabled={kcTesting || !kcRealmUrl} class="px-4 py-2.5 text-xs font-black uppercase cursor-pointer border-2" class:opacity-50={kcTesting || !kcRealmUrl} style="border-color: var(--on-surface); background: var(--surface-container-highest);">{kcTesting ? 'TESTING...' : 'TEST_CONNECTION'}</button>
            <button onclick={saveKeycloakSettings} disabled={kcSaving} class="flex-1 px-4 py-2.5 text-xs font-black uppercase cursor-pointer border-2 press-effect" class:opacity-50={kcSaving} style="border-color: var(--on-surface); background: var(--primary-container); box-shadow: 3px 3px 0px 0px var(--on-surface);">{kcSaving ? 'SAVING...' : 'SAVE_CONFIGURATION'}</button>
          </div>
        </div>
      </div>

      <!-- RIGHT: Keycloak setup guide -->
      <div class="border-2" style="border-color: var(--on-surface);">
        <div class="dark-bar">KEYCLOAK_SETUP_GUIDE</div>
        <div class="bg-white p-3 space-y-3 text-[10px] font-bold uppercase" style="color: var(--on-surface);">
          <div>
            <div style="color: var(--secondary);">1. CLIENT_TYPE</div>
            <div style="color: var(--outline);">Public (PKCE) or Confidential (with secret)</div>
          </div>
          <div>
            <div style="color: var(--secondary);">2. VALID_REDIRECT_URIS</div>
            <div class="px-2 py-1 mt-0.5 font-mono text-[9px]" style="background: var(--surface-container); color: var(--on-surface); word-break: break-all;">{typeof window !== 'undefined' ? window.location.origin : 'https://your-app'}/*</div>
          </div>
          <div>
            <div style="color: var(--secondary);">3. POST_LOGOUT_REDIRECT_URIS</div>
            <div class="px-2 py-1 mt-0.5 font-mono text-[9px]" style="background: var(--surface-container); word-break: break-all;">{typeof window !== 'undefined' ? window.location.origin : 'https://your-app'}/*</div>
          </div>
          <div>
            <div style="color: var(--secondary);">4. WEB_ORIGINS</div>
            <div class="px-2 py-1 mt-0.5 font-mono text-[9px]" style="background: var(--surface-container); word-break: break-all;">{typeof window !== 'undefined' ? window.location.origin : 'https://your-app'}</div>
          </div>
          <div>
            <div style="color: var(--secondary);">5. REALM_ROLES_NEEDED</div>
            <div class="flex gap-1 mt-0.5">
              <span class="px-1.5 py-0.5 text-[9px]" style="background: var(--on-surface); color: var(--surface);">{kcAdminRole || 'admin'}</span>
              <span class="px-1.5 py-0.5 text-[9px]" style="background: var(--outline); color: white;">user</span>
            </div>
            <div class="mt-0.5" style="color: var(--outline);">Users without "{kcAdminRole || 'admin'}" role get "user" role</div>
          </div>
          <div class="pt-1" style="border-top: 1px solid var(--surface-container-highest);">
            <div style="color: var(--secondary);">IMPLEMENTATION</div>
            <div class="space-y-1 mt-1" style="color: var(--outline);">
              <div>OIDC Auth Code + PKCE (no keycloak-js needed)</div>
              <div>Session init on app start via auth.init()</div>
              <div>Routes protected by layout guard</div>
              <div>Bearer token in all API requests</div>
              <div>Logout terminates Keycloak session</div>
              <div>Token auto-refresh 60s before expiry</div>
            </div>
          </div>
        </div>
      </div>
    </div>

  {:else if activeTab === 'groups'}
    <!-- GROUPS MANAGEMENT -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <!-- Group list -->
      <div class="border-2 stamp-shadow" style="border-color: var(--on-surface);">
        <div class="dark-bar flex items-center justify-between">
          <span>GROUPS</span>
          <button class="px-2 py-0.5 text-[10px] font-black uppercase cursor-pointer" style="color: var(--primary-container);" onclick={startNewGroup}>+ NEW</button>
        </div>
        <div class="bg-white">
          {#if groups.length === 0}
            <div class="p-4 text-xs font-bold uppercase text-center" style="color: var(--outline);">No groups created yet</div>
          {:else}
            {#each groups as g}
              <button class="w-full text-left px-4 py-3 flex items-center justify-between cursor-pointer"
                style="border-bottom: 1px solid var(--surface-container-highest); {editingGroup?.id === g.id ? 'background: var(--surface-container);' : ''}"
                onclick={() => editGroup(g)}>
                <div>
                  <div class="text-sm font-bold uppercase" style="color: var(--on-surface);">{g.name}</div>
                  <div class="text-[10px] font-bold uppercase" style="color: var(--outline);">{g.member_count} member{g.member_count !== 1 ? 's' : ''}</div>
                </div>
                <span class="text-[10px] font-bold uppercase" style="color: var(--secondary);">EDIT</span>
              </button>
            {/each}
          {/if}
        </div>
      </div>

      <!-- Group editor -->
      {#if editingGroup}
        <div class="border-2 stamp-shadow" style="border-color: var(--on-surface);">
          <div class="dark-bar">{editingGroup.id ? 'EDIT_GROUP' : 'CREATE_GROUP'}</div>
          <div class="bg-white p-4 space-y-3">
            {#if groupMessage}<div class="p-2 text-xs font-bold uppercase" style="color: var(--primary);">{groupMessage}</div>{/if}

            <div>
              <div class="tag-label mb-0.5" style="font-size: 9px;">GROUP_NAME</div>
              <input bind:value={groupName} placeholder="e.g. Operators" class="w-full font-bold text-sm focus:outline-none" style="padding: 6px 10px; font-family: 'Space Grotesk', sans-serif; background: white; border: 2px solid var(--on-surface);" />
            </div>

            <!-- Pages -->
            <div>
              <div class="tag-label mb-1" style="font-size: 9px;">PAGES</div>
              <div class="flex flex-wrap gap-2">
                {#each Object.entries(groupPages) as [key, val]}
                  <button class="px-2 py-1 text-[10px] font-black uppercase cursor-pointer border"
                    style="border-color: var(--on-surface); background: {val ? 'var(--primary)' : 'white'}; color: {val ? 'white' : 'var(--outline)'};"
                    onclick={() => groupPages = {...groupPages, [key]: !val}}>{key}</button>
                {/each}
              </div>
            </div>

            <!-- Actions -->
            <div>
              <div class="tag-label mb-1" style="font-size: 9px;">ACTIONS</div>
              <div class="flex flex-wrap gap-2">
                {#each Object.entries(groupActions) as [key, val]}
                  <button class="px-2 py-1 text-[10px] font-black uppercase cursor-pointer border"
                    style="border-color: var(--on-surface); background: {val ? 'var(--secondary)' : 'white'}; color: {val ? 'white' : 'var(--outline)'};"
                    onclick={() => groupActions = {...groupActions, [key]: !val}}>{key.replace(/_/g, ' ')}</button>
                {/each}
              </div>
            </div>

            <!-- Data scope -->
            <div>
              <div class="tag-label mb-1" style="font-size: 9px;">DATA_SCOPE</div>
              <div class="flex gap-2">
                {#each [['own', 'OWN DATA'], ['all_readonly', 'ALL (READ)'], ['all_full', 'ALL (FULL)']] as [val, label]}
                  <button class="px-2 py-1 text-[10px] font-black uppercase cursor-pointer border"
                    style="border-color: var(--on-surface); background: {groupScope === val ? 'var(--on-surface)' : 'white'}; color: {groupScope === val ? 'var(--surface)' : 'var(--outline)'};"
                    onclick={() => groupScope = val}>{label}</button>
                {/each}
              </div>
            </div>

            <!-- Members -->
            <div>
              <div class="tag-label mb-1" style="font-size: 9px;">MEMBERS</div>
              <div class="flex flex-wrap gap-2 max-h-24 overflow-y-auto">
                {#each users.filter(u => u.role !== 'admin') as u}
                  <button class="px-2 py-1 text-[10px] font-bold uppercase cursor-pointer border"
                    style="border-color: var(--on-surface); background: {groupMembers.includes(u.id) ? 'var(--tertiary)' : 'white'}; color: {groupMembers.includes(u.id) ? 'white' : 'var(--outline)'};"
                    onclick={() => toggleMember(u.id)}>{u.username}</button>
                {/each}
                {#if users.filter(u => u.role !== 'admin').length === 0}
                  <span class="text-[10px] font-bold uppercase" style="color: var(--outline);">No non-admin users yet</span>
                {/if}
              </div>
            </div>

            <!-- Buttons -->
            <div class="flex gap-2 pt-1">
              {#if editingGroup.id}
                <button onclick={deleteGroup} class="px-3 py-2 text-[10px] font-black uppercase cursor-pointer border-2" style="border-color: var(--error); color: var(--error);">DELETE</button>
              {/if}
              <button onclick={saveGroup} disabled={groupSaving || !groupName.trim()}
                class="flex-1 px-3 py-2 text-[10px] font-black uppercase cursor-pointer border-2 press-effect"
                class:opacity-50={groupSaving || !groupName.trim()}
                style="border-color: var(--on-surface); background: var(--primary-container); box-shadow: 2px 2px 0px 0px var(--on-surface);">
                {groupSaving ? 'SAVING...' : 'SAVE_GROUP'}
              </button>
              <button onclick={() => editingGroup = null} class="px-3 py-2 text-[10px] font-black uppercase cursor-pointer border-2" style="border-color: var(--on-surface); color: var(--outline);">CANCEL</button>
            </div>
          </div>
        </div>
      {:else}
        <div class="border-2 flex items-center justify-center p-8" style="border-color: var(--surface-container-highest); border-style: dashed;">
          <div class="text-center">
            <div class="text-xs font-bold uppercase" style="color: var(--outline);">Select a group to edit or</div>
            <button class="mt-2 px-4 py-2 text-xs font-black uppercase cursor-pointer border-2 press-effect"
              style="border-color: var(--on-surface); background: var(--primary-container); box-shadow: 2px 2px 0px 0px var(--on-surface);"
              onclick={startNewGroup}>CREATE_NEW_GROUP</button>
          </div>
        </div>
      {/if}
    </div>

  {/if}
{/if}
