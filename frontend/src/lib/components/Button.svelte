<script lang="ts">
  import type { Snippet } from 'svelte';

  let {
    variant = 'primary' as 'primary' | 'secondary' | 'danger' | 'ghost' | 'dark',
    size = 'md' as 'sm' | 'md' | 'lg',
    disabled = false,
    onclick = undefined as (() => void) | undefined,
    children,
  }: {
    variant?: 'primary' | 'secondary' | 'danger' | 'ghost' | 'dark';
    size?: 'sm' | 'md' | 'lg';
    disabled?: boolean;
    onclick?: (() => void) | undefined;
    children: Snippet;
  } = $props();

  const styles = $derived({
    primary: 'background: #00fc40; color: #383832; border: 2px solid #383832; box-shadow: 4px 4px 0px 0px #383832;',
    secondary: 'background: #007518; color: white; border: 2px solid #383832; box-shadow: 4px 4px 0px 0px #383832;',
    danger: 'background: #be2d06; color: #feffd6; border: 2px solid #383832; box-shadow: 4px 4px 0px 0px #383832;',
    ghost: 'background: transparent; color: #feffd6; border: 1px solid #65655e;',
    dark: 'background: #383832; color: #feffd6; border: 2px solid #383832; box-shadow: 4px 4px 0px 0px #383832;',
  }[variant]);

  const padding = $derived({
    sm: 'padding: 6px 12px; font-size: 10px;',
    md: 'padding: 8px 16px; font-size: 0.75rem;',
    lg: 'padding: 12px 32px; font-size: 0.875rem;',
  }[size]);
</script>

<button
  class="press-effect font-black uppercase tracking-wider cursor-pointer transition-colors"
  class:opacity-50={disabled}
  class:cursor-not-allowed={disabled}
  style="{styles} {padding}"
  {disabled}
  onclick={onclick}
>
  {@render children()}
</button>
