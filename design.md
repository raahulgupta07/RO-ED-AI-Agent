# CityBCPAgent Design System

Complete UI/UX reference extracted from the CityBCPAgent project. Every hex color, font size, border width, and component pattern documented for pixel-perfect recreation in any framework.

---

## 0. Tech Stack & Languages

### Frontend
| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| Framework | **SvelteKit** | 5 | SPA with file-based routing |
| Language | **TypeScript / Svelte 5** | — | Svelte 5 runes (`$state`, `$derived`, `$effect`, `$props`) |
| CSS | **TailwindCSS** | 4.2 | Utility-first styling |
| Charts | **ECharts** | 6 | Interactive data visualization |
| Adapter | `@sveltejs/adapter-static` | 3 | Static SPA build (fallback: index.html) |
| Build | **Vite** | 6 | Dev server + production bundler |
| Fonts | **Google Fonts** (Space Grotesk) | — | CDN-loaded, weights 300-700 |
| Icons | **Material Symbols Outlined** | — | CDN-loaded, variable font |

### Backend
| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| Framework | **FastAPI** | 0.115 | REST API + WebSocket |
| Language | **Python** | 3.12 | Backend logic, data processing |
| Server | **Uvicorn** | 0.30 | ASGI server |
| Database | **SQLite** | (bundled) | WAL mode, 22 tables, auto-migration |
| Auth | **python-jose** | 3.3 | JWT token generation/validation |
| Data | **pandas** | 2.2 | DataFrame processing |
| Excel | **openpyxl** | 3.1 | Excel read/write (read_only for validation) |
| ML | **scikit-learn** | 1.5 | Ridge, IsolationForest, GradientBoosting |
| AI | **Gemini 3.1 Flash Lite** | — | Via OpenRouter API |
| Export | **openpyxl** | 3.1 | Excel export with merged headers, colored text |

### Infrastructure
| Layer | Technology | Purpose |
|-------|-----------|---------|
| Container | **Docker** | Single container, port 8000 |
| Compose | **docker-compose** | Volume for DB persistence |
| Base Image | `python:3.12-slim` | Minimal Python + apt nodejs/npm for frontend build |
| Frontend Serving | FastAPI catch-all route | Serves SvelteKit static build at `/`, API at `/api/*` |

### Key Svelte 5 Patterns Used
```svelte
<!-- State -->
let count = $state(0);
let items: Item[] = $state([]);

<!-- Derived -->
const filtered = $derived(items.filter(i => i.active));
const total = $derived.by(() => { /* complex logic */ });

<!-- Effects -->
$effect(() => { /* runs on dependency change */ });

<!-- Props -->
let { data, title = 'Default' } = $props();

<!-- Template constants (must be inside {#if}, {#each}, NOT inside HTML elements) -->
{#each items as item}
  {@const pct = item.value / total * 100}
  <span>{pct}%</span>
{/each}

<!-- HTML entities required (Svelte parses < > as HTML) -->
{#if buffer &lt; 3} CRITICAL {/if}
```

---

## 1. Brand Identity

### Design Philosophy
**Brutalist / Industrial / Newspaper / Command Center**

The UI deliberately rejects modern soft design trends. It uses:
- **Zero border-radius** (`* { border-radius: 0px !important; }`) -- every element is sharp-cornered
- **Asymmetric ink borders** (thicker on bottom/right, thinner on top/left) mimicking letterpress printing
- **Stamp shadows** (hard-edged `4px 4px 0px` offsets, no blur) like rubber stamp impressions
- **All-caps labels** with wide letter-spacing, styled like military/industrial tags
- **Monochromatic dark-on-yellow** palette resembling aged newsprint or legal pads
- **Terminal/CLI aesthetics** in naming conventions: `AUTH_AGENT`, `DATA_INGESTION_MODULE`, `SYNC_STATUS`
- **No emojis in UI chrome** -- status uses colored dots and material icons instead

### Overall Aesthetic
A wartime command center / newspaper operations desk. Dense data tables, bold uppercase headings, visible grid lines, dark title bars, and a warm yellow background that evokes urgency without alarm.

---

## 2. Color Palette

### 2.1 CSS Custom Properties (`:root`)

| Variable | Hex | Usage |
|---|---|---|
| `--surface` | `#feffd6` | Page background (warm yellow) |
| `--surface-container-lowest` | `#ffffff` | Pure white (card backgrounds, inputs) |
| `--surface-container-low` | `#fcf9ef` | Alternating table row (even) |
| `--surface-container` | `#f6f4e9` | Form backgrounds, filter bar, message area |
| `--surface-container-high` | `#f1eee3` | (available, rarely used) |
| `--surface-container-highest` | `#ebe8dd` | Skeleton loading, scrollbar track, table headers, progress bar track |
| `--on-surface` | `#383832` | Primary text, borders, dark backgrounds |
| `--on-background` | `#383832` | Same as on-surface (used for ink-border) |
| `--primary` | `#007518` | Primary green (success, safe, active) |
| `--primary-container` | `#00fc40` | Bright green (CTA buttons, boot complete, active tab icon) |
| `--secondary` | `#006f7c` | Teal (secondary actions, tool labels, data types) |
| `--secondary-container` | `#26e6ff` | (available, rarely used directly) |
| `--tertiary` | `#9d4867` | Mauve/rose (tertiary, logout, LIVE_FEED badge) |
| `--tertiary-container` | `#fe97b9` | Pink (accent card bg for tertiary, clear button) |
| `--error` | `#be2d06` | Deep red (errors, critical alerts, danger zone) |
| `--error-container` | `#f95630` | Orange-red (REDUCE mode, grade D) |
| `--outline` | `#828179` | Placeholder text, muted icons |
| `--outline-variant` | `#bbb9b1` | (available, rarely used) |

### 2.2 Extended Colors (used inline, not as CSS vars)

| Hex | Name | Usage |
|---|---|---|
| `#ff9d00` | Amber/Orange | Warnings, MONITOR mode, thinking dot 2, fuel agent, suggestion icons |
| `#e85d04` | Burnt Orange | Fuel/burn column headers, fuel agent boot |
| `#65655e` | Warm Gray | Muted text, disabled states, NO DATA, sub-labels |
| `#9d9d91` | Light Gray | Timestamps, formula annotations |
| `#4a4a44` | Dark Gray | Boot sequence inactive text |
| `#1a1a1a` | Near Black | Data model terminal background |
| `#00ff41` | Terminal Green | ERD primary key color, computed field names |
| `#856404` | Warning Brown | Excel issues text on `#fff3cd` background |
| `#fff3cd` | Warning Yellow BG | Data quality warning banner |
| `#C6EFCE` | Validation Pass BG | Cell background when values match |
| `#FFC7CE` | Validation Fail BG | Cell background when values mismatch |
| `#FFF3CD` | Blackout Issue BG | Cell background for blackout discrepancies |

### 2.3 Semantic Color Mapping

| Semantic | Hex | CSS Var |
|---|---|---|
| Success / Safe / Good | `#007518` | `--primary` |
| Success Bright / CTA | `#00fc40` | `--primary-container` |
| Warning / Monitor | `#ff9d00` | (inline) |
| Error / Critical / Danger | `#be2d06` | `--error` |
| Error Bright / Reduce | `#f95630` | `--error-container` |
| Info / Secondary | `#006f7c` | `--secondary` |
| Muted / Disabled | `#65655e` | (inline) |

### 2.4 Status/Severity Color Map

```
CRITICAL  = #be2d06 (deep red)
WARNING   = #ff9d00 (amber)
WATCH     = #ff9d00 (amber, same as WARNING)
INFO      = #65655e (warm gray)
NORMAL    = #9d9d91 (light gray dot)
```

### 2.5 Operating Mode Colors

```
FULL      = #007518 (green)
MONITOR   = #ff9d00 (amber)
REDUCE    = #f95630 (orange-red)
CLOSE     = #be2d06 (deep red)
```

### 2.6 Urgency Colors

```
HIGH      = #be2d06
MEDIUM    = #ff9d00
MED       = #ff9d00
LOW       = #007518
```

### 2.7 BCP Grade Colors

```
A = #007518 (green)
B = #006f7c (teal)
C = #ff9d00 (amber)
D = #f95630 (orange-red)
F = #be2d06 (deep red)
```

### 2.8 Buffer Days Thresholds

```
>= 7 days  = #007518 (SAFE)
>= 3 days  = #ff9d00 (WARNING)
<  3 days  = #be2d06 (CRITICAL)
```

### 2.9 Data Freshness Colors

```
<= 2 days ago  = #007518 (green)
<= 7 days ago  = #ff9d00 (amber)
>  7 days ago   = #be2d06 (red)
NEVER          = #65655e (gray)
```

### 2.10 Upload/Validation Status Colors

```
VALIDATING = #006f7c (teal)
VALIDATED  = #007518 (green)
INVALID    = #be2d06 (red)
WRONG_TAB  = #ff9d00 (amber)
UPLOADING  = #ff9d00 (amber)
IMPORTED   = #007518 (green)
REJECTED   = #be2d06 (red)
```

### 2.11 Trend Arrow Colors

```
Up (good)     = #007518
Down (bad)    = #be2d06
Neutral       = #65655e
```

### 2.12 KPI Card Color Variants

```
primary   -> accent: #007518, bg: white
secondary -> accent: #006f7c, bg: white
tertiary  -> accent: #9d4867, bg: #fe97b9 (when variant='accent')
error     -> accent: #be2d06, bg: white
```

---

## 3. Typography

### 3.1 Font Family

```css
font-family: 'Space Grotesk', sans-serif;
```

Google Fonts import:
```
https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&display=swap
```

### 3.2 Font Weights

| Weight | Tailwind Class | Usage |
|---|---|---|
| 300 | `font-light` | (available, rarely used) |
| 400 | `font-normal` | Body text, sub-labels |
| 500 | `font-medium` | Chat suggestions, descriptions |
| 600 | `font-semibold` | (available) |
| 700 | `font-bold` | Most labels, nav items, table cells |
| 900 | `font-black` | Headlines, KPI values, tags, table headers, buttons |

**Primary pattern:** `font-black uppercase` for headings and labels. `font-bold` for secondary text. `font-medium` for body.

### 3.3 Font Sizes

| Size | Tailwind | Context |
|---|---|---|
| `text-8xl` | 6rem | Login decoration ("CITY HOLDINGS MYANMAR") |
| `text-7xl` | 4.5rem | Buffer hero number |
| `text-5xl` | 3rem | Login title "ACCESS_PORTAL", KPI hero values |
| `text-4xl` | 2.25rem | KPI card values, page titles "DATA_ENTRY" |
| `text-3xl` | 1.875rem | (responsive: becomes 1.5rem on mobile) |
| `text-2xl` | 1.5rem | Header brand "BCP COMMAND CENTER", section totals |
| `text-xl` | 1.25rem | Chat empty state heading |
| `text-lg` | 1.125rem | Section sub-headers, AI panel icon |
| `text-sm` | 0.875rem | Nav items, form inputs, chat messages, most body text |
| `text-xs` | 0.75rem | Table cells, descriptions, smaller labels |
| `text-[11px]` | 0.6875rem | Footer bar, AI panel title, table text |
| `text-[10px]` | 0.625rem | Tag labels, sub-info, tracking text, timestamps |
| `text-[9px]` | 0.5625rem | Severity badges, status text, footnotes |
| `text-[8px]` | 0.5rem | Step numbers, key hints, freshness badges |
| `text-[7px]` | 0.4375rem | Tab sub-descriptions |

### 3.4 Letter Spacing / Tracking

| Tailwind Class | Usage |
|---|---|
| `tracking-tighter` | Headlines, brand name, KPI values |
| `tracking-tight` | Tab labels |
| `tracking-wider` | Buttons ("INITIATE_AUTHENTICATION"), footer status |
| `tracking-widest` | Login decorative labels, boot sequence names |

### 3.5 Text Transform

```
uppercase  -- Used on virtually ALL labels, headings, tags, badges, buttons, nav items
```

Everything visible is uppercase. Body/paragraph text and chat messages are the only exceptions.

### 3.6 Font Mono

`font-mono` is used for:
- Data values in raw data tables
- File types in upload queue
- Terminal-style elements (data model ERD)
- Timestamps and progress counters

---

## 4. Layout & Spacing

### 4.1 Page Structure

```
<header>  — fixed top, z-50, full width
<main>    — pt-16 (header clearance), pb-16 (footer clearance), px-6
<footer>  — fixed bottom, z-50, h-10, full width
```

### 4.2 Max Widths

| Context | Value |
|---|---|
| Page container | `max-w-[1920px] mx-auto` |
| Upload page | `max-w-6xl mx-auto` (1152px) |
| Login form | `max-w-md` (448px) |
| Login full layout | `max-w-7xl` (1280px) |
| Chat input | `max-w-4xl mx-auto` |
| Chat suggestions grid | `max-w-3xl mx-auto` |

### 4.3 Spacing Tokens (Tailwind classes used)

| Pattern | Values Used |
|---|---|
| Page padding | `px-6`, `px-6 md:px-24` (login) |
| Section gap | `space-y-6`, `space-y-4`, `gap-4` |
| Card padding | `p-4`, `p-3`, `p-6`, `p-8` |
| Table cell padding | `px-4 py-2.5`, `px-3 py-2`, `px-2 py-1.5`, `px-2 py-1` |
| Header padding | `px-6 py-3` |
| Filter bar padding | `p-4` |
| Form input padding | `px-4 py-3` |
| Button padding | `px-8 py-3` (primary), `px-4 py-3` (medium), `px-3 py-1.5` (small), `px-2 py-1` (tiny) |
| Tag padding | `px-2 py-0.5` (standard tag), `px-1.5 py-0.5` (severity badge) |
| Grid gaps | `gap-3`, `gap-4`, `gap-6`, `gap-8` |
| Login form internal | `space-y-5` |
| Between label and input | `mb-1` |

### 4.4 Grid Patterns

```css
/* KPI cards */
grid-cols-2 md:grid-cols-3 lg:grid-cols-4

/* Sync status cards */
grid-cols-2 md:grid-cols-4 lg:grid-cols-7

/* Validation summary cards */
grid-cols-2 md:grid-cols-4

/* Data model ERD cards */
grid-cols-1 md:grid-cols-2 xl:grid-cols-3

/* Chat suggestions */
grid-cols-1 md:grid-cols-2 lg:grid-cols-3

/* Operating modes KPI */
grid-cols-4
```

### 4.5 Fixed Positioning

```
Header:  fixed top-0 w-full z-50
Footer:  fixed bottom-0 left-0 w-full z-50
Filter:  sticky top-16 z-30
Toast:   fixed top-20 right-6 z-50
```

### 4.6 Responsive Breakpoints

```css
/* Mobile */
@media (max-width: 640px) {
  .text-3xl { font-size: 1.5rem; }
  .text-2xl { font-size: 1.25rem; }
  /* Chart heights reduced */
}

/* Tailwind responsive */
md: 768px   (show nav, grid columns expand)
lg: 1024px  (login decoration visible, more grid columns)
xl: 1280px  (3-column ERD grid)
```

---

## 5. Components

### 5.1 Header / Navigation

**Structure:**
```
fixed top-0, full width, z-50
border-bottom: 3px solid #383832
background: #feffd6
```

**Brand Badge:**
```
text-2xl font-bold tracking-tighter uppercase
px-2 py-1
background: #383832
color: #feffd6
text: "BCP COMMAND CENTER"
```

**Nav Items:**
```
px-2 py-1
text-sm font-bold uppercase tracking-tighter
```

- **Default:** `color: #383832; background: transparent`
- **Active:** `background: #383832; color: #feffd6`
- **Hover:** `background: #007518; color: white`

**User Avatar:**
```
w-10 h-10
background: #9d4867
color: white
border: 2px solid #383832
font-bold text-sm
Content: first letter of username, uppercase
```

**Search Dropdown:**
```
background: white
border: 2px solid #383832
box-shadow: 4px 4px 0px 0px #383832
width: 280px
```

### 5.2 Buttons

#### Primary Button (CTA / Submit)
```css
background: #00fc40;
color: #383832;
border: 2px solid #383832;
box-shadow: 4px 4px 0px 0px #383832;  /* stamp shadow */
font-weight: 900;  /* font-black */
text-transform: uppercase;
letter-spacing: wider;
font-size: 0.875rem;
padding: 12px 32px;  /* py-3 px-8 */

/* Press effect */
active:translate-x-[2px] active:translate-y-[2px]
```

#### Secondary Button (Action)
```css
background: #007518;
color: white;
border: 2px solid #383832;
```

#### Danger Button (Reset / Purge)
```css
background: #be2d06;
color: #feffd6;
border: 2px solid #383832;
box-shadow: 4px 4px 0px 0px #383832;
```

#### Ghost Button (Clear / Delete)
```css
background: transparent;
color: #feffd6;
border: 1px solid #65655e;
font-size: 10px;
font-weight: 900;
text-transform: uppercase;
```

#### Dark Background Button (Retry)
```css
background: #383832;
color: #feffd6;
border: 2px solid #383832;
```

#### Tab Button
```css
/* Default */
background: transparent;
color: #65655e;
font-weight: 700;
text-transform: uppercase;
letter-spacing: tight;
font-size: 11px;
padding: 8px 12px;

/* Active */
background: #383832;
color: #feffd6;
```

#### Disabled State
```css
opacity: 0.5;
/* or */ opacity: 0.3;
cursor: not-allowed;
```

### 5.3 Cards / KPI Cards

#### Standard KPI Card (KpiCard.svelte)
```css
/* Container */
padding: 16px;
background: white;
border-color: #383832;

/* Asymmetric border (heavier bottom-right) */
border-top-width: 2px;
border-left-width: 2px;
border-bottom-width: 4px;
border-right-width: 4px;
border-style: solid;

/* Stamp shadow */
box-shadow: 4px 4px 0px 0px rgba(56, 56, 50, 1);
```

**Title Tag:**
```css
display: inline-block;
padding: 2px 8px;
font-size: 10px;
font-weight: 900;
text-transform: uppercase;
background: #383832;
color: #feffd6;
```

**Value:**
```css
font-size: 2.25rem;  /* text-4xl */
font-weight: 900;
letter-spacing: tighter;
color: #383832;
```

**Unit suffix:**
```css
font-size: 1.125rem;  /* text-lg */
```

**Progress Bar:**
```css
height: 8px;  /* h-2 */
background: #ebe8dd;
border: 1px solid #383832;
/* Fill color = accent color from colorMap */
```

**Subtitle:**
```css
font-size: 10px;
text-transform: uppercase;
opacity: 0.6;
font-weight: 700;
color: #383832;
```

#### Data Container Card (used for tables, sections)
```css
border: 2px solid #383832;
box-shadow: 4px 4px 0px 0px #383832;

/* Title bar */
padding: 8px 16px;
background: #383832;
color: #feffd6;
font-weight: 900;
text-transform: uppercase;
font-size: 0.875rem;
```

### 5.4 Tables

#### Table Container
```css
border: 2px solid #383832;
box-shadow: 4px 4px 0px 0px #383832;
background: white;
overflow-x: auto;
max-height: 500px;
overflow-y: auto;
```

#### Table Title Bar
```css
padding: 8px 16px;
background: #383832;
color: #feffd6;
font-weight: 900;
text-transform: uppercase;
letter-spacing: wider;
font-size: 0.875rem;
```

#### Table Header Row
```css
background: #ebe8dd;
position: sticky;
top: 0;
z-index: 1;
```

#### Table Header Cell
```css
padding: 6px 8px;       /* px-2 py-1.5 (small tables) */
/* or */ padding: 8px 16px;  /* px-4 py-2 (large tables) */
text-align: left;
font-weight: 900;
text-transform: uppercase;
font-size: 10px;        /* or 0.75rem for larger tables */
border-bottom: 2px solid #383832;
```

#### Grouped Header (merged columns)
```css
/* Group label row */
font-size: 9px;
font-weight: 900;
text-transform: uppercase;
color: {group.color};  /* e.g., #65655e, #007518, #e85d04, #006f7c, #9d4867, #be2d06 */
text-align: center;
border-bottom: 1px solid #383832;
```

#### Table Body Row
```css
border-bottom: 1px solid rgba(56, 56, 50, 0.15);

/* Alternating rows */
/* Even (0, 2, 4...): background: white (or transparent) */
/* Odd (1, 3, 5...):  background: #fcf9ef */
```

#### Table Body Cell
```css
padding: 6px 8px;    /* px-2 py-1 (compact) */
/* or */ padding: 10px 16px;  /* px-4 py-2.5 (roomy) */
font-size: 10px;     /* or 0.75rem */
color: #383832;
font-family: monospace;  /* for data tables */
```

#### Sticky Column
```css
position: sticky;
left: 0;
background: inherit;  /* match row bg */
border-right: 2px solid #383832;
```

#### Sort/Status in Table Header
Column group colors are set per metric type:
```
Blackout:    #65655e
Tank:        #007518
Burn/Fuel:   #e85d04
Sales:       #006f7c
Diesel Cost: #9d4867
Margin:      #007518
Diesel %:    #be2d06
```

### 5.5 Forms & Inputs

#### Input Field
```css
width: 100%;
padding: 12px 16px;    /* px-4 py-3 */
font-size: 0.875rem;   /* text-sm */
font-weight: 700;
font-family: 'Space Grotesk', sans-serif;
background: white;
border: 2px solid #383832;
color: #383832;
border-radius: 0;  /* forced by global rule */
```

#### Input Focus
No visible focus ring by default (Tailwind `focus:outline-none` used in chat). Relies on border color contrast.

#### Input Label (Tag Style)
```css
display: inline-block;
padding: 2px 8px;       /* px-2 py-0.5 */
font-size: 10px;        /* text-[10px] */
font-weight: 900;
text-transform: uppercase;
background: #383832;
color: #feffd6;
margin-bottom: 4px;     /* mb-1 */
```

#### Select/Dropdown
```css
width: 100%;
padding: 8px 12px;     /* px-3 py-2 */
font-size: 0.875rem;
font-weight: 700;
text-transform: uppercase;
background: white;
border: 2px solid #383832;
color: #383832;

/* Disabled state */
background: #ebe8dd;
color: #65655e;
cursor: not-allowed;
```

#### Chat Input (textarea)
```css
width: 100%;
padding: 12px 16px;
font-size: 0.875rem;
background: #f6f4e9;
border: 2px solid #383832;
color: #383832;
border-radius: 8px;  /* exception to global 0 rule -- overridden by !important */
min-height: 44px;
max-height: 120px;
resize: none;
```

### 5.6 Badges / Tags

#### Severity Badge
```css
display: inline-block;
padding: 2px 6px;        /* px-1.5 py-0.5 */
font-size: 9px;           /* text-[9px] */
font-weight: 900;
text-transform: uppercase;
color: white;

/* Backgrounds by severity */
CRITICAL: background: #be2d06;
WARNING:  background: #ff9d00;
WATCH:    background: #ff9d00;
INFO:     background: #65655e;
NORMAL:   background: #9d9d91;
```

#### Category Badge
```css
padding: 2px 8px;        /* px-2 py-0.5 */
font-size: 9px;
font-weight: 700;
text-transform: uppercase;
color: white;

DAILY:     background: #007518;
REFERENCE: background: #006f7c;
UNKNOWN:   background: #828179;
```

#### Grade Badge
```css
/* Used inline with grade letter */
color determined by gradeColors map:
A = #007518
B = #006f7c
C = #ff9d00
D = #f95630
F = #be2d06
font-weight: 900;
```

#### Operating Mode Badge
```css
padding: 2px 10px;
font-size: 0.75rem;
font-weight: 800;
letter-spacing: 0.05em;
text-transform: uppercase;
color: white;
background: {modeColors[mode]};
```

#### Status Badge (Upload Queue)
```css
display: inline-flex;
align-items: center;
gap: 4px;
padding: 2px 8px;
font-weight: 700;
text-transform: uppercase;
font-size: 10px;
color: white;
background: {statusColor[status]};
```

#### Freshness Badge
```css
padding: 2px 6px;        /* px-1.5 py-0.5 */
font-size: 8px;           /* text-[8px] */
font-weight: 900;
color: white;
background: {freshness.color};  /* #007518, #ff9d00, or #be2d06 */
```

#### Role Badge (boot sequence)
```css
padding: 2px 6px;
font-size: 8px;
font-weight: 700;
text-transform: uppercase;
background: #007518;
color: white;
```

#### LIVE_FEED Badge (footer)
```css
padding: 2px 8px;
font-size: 10px;
font-weight: 700;
background: #9d4867;
color: white;
border: 1px solid #383832;
animation: pulse (Tailwind animate-pulse);
```

### 5.7 Chapter Headings

The dashboard uses a "chapter" pattern for major sections:

```css
/* Full-width dark bar */
padding: 12px 16px;      /* px-4 py-3 */
background: #383832;
color: #feffd6;
margin-bottom: 12px;

/* Layout: icon + text */
display: flex;
align-items: center;
gap: 12px;

/* Icon */
font-size: 1.5rem;        /* text-2xl material-symbols-outlined */
color: #ff9d00;            /* amber accent for icons */

/* Title */
font-weight: 900;
text-transform: uppercase;
font-size: 0.875rem;
"CHAPTER 1: OPERATING MODES"

/* Subtitle */
font-size: 10px;
opacity: 0.75;
"Should each site stay OPEN, MONITOR, REDUCE hours, or CLOSE?"

/* Question prompt (below) */
font-family: monospace;
font-size: 0.75rem;
color: #00fc40;
padding-left: 32px;
"? Which sites should reduce generator hours?"
```

### 5.8 Progress Bars

#### Validation Progress (inline, small)
```css
width: 80px;          /* w-20 */
height: 6px;          /* h-1.5 */
background: #ebe8dd;
border: 1px solid #383832;

/* Fill */
background: #00fc40;
height: 100%;
transition: all;
```

#### Upload Progress (inline, small)
```css
/* Same structure as validation but amber fill */
background: #ff9d00;
```

#### Upload Overall Progress
```css
width: 100%;
height: 8px;          /* h-2 */
background: #ebe8dd;
border: 1px solid #383832;

/* Fill */
background: #007518;
height: 100%;
transition: all;
```

#### Buffer Hero Progress Bar
```css
height: 16px;        /* h-4 */
max-width: 240px;
background: #ebe8dd;
border: 2px solid #383832;

/* Fill */
background: {bufferColor};  /* #007518, #ff9d00, or #be2d06 */
```

#### Boot Sequence Progress
```css
height: 6px;          /* h-1.5 */
background: #4a4a44;

/* Fill */
background: #007518;        /* in progress */
background: #00fc40;        /* complete */
transition: all 300ms;
```

### 5.9 Chat Bubbles

#### User Message
```css
max-width: 70%;
padding: 10px 16px;    /* px-4 py-2.5 */
font-size: 0.875rem;
background: #383832;
color: #feffd6;
border-radius: 12px 12px 0 12px;  /* rounded top, flat bottom-right */
```

#### Assistant Message
```css
max-width: 80%;
padding: 12px 16px;    /* px-4 py-3 */
font-size: 0.875rem;
line-height: relaxed;   /* leading-relaxed */
background: white;
color: #383832;
border: 1px solid #ebe8dd;
border-radius: 0 12px 12px 12px;  /* flat top-left, rounded elsewhere */
```

#### Assistant Avatar
```css
width: 28px;
height: 28px;
background: #007518;
border-radius: 50%;
display: flex;
align-items: center;
justify-content: center;

/* Icon inside */
material-symbols-outlined: "psychology"
font-size: 0.875rem;
color: white;
```

#### Thinking Animation
Three bouncing dots:
```css
/* Dot container */
display: flex;
gap: 4px;

/* Each dot */
width: 8px;
height: 8px;
border-radius: 50%;      /* exception: dots are round */

/* Dot 1 */ background: #007518; animation-delay: 0ms;
/* Dot 2 */ background: #ff9d00; animation-delay: 150ms;
/* Dot 3 */ background: #be2d06; animation-delay: 300ms;

@keyframes bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-6px); }
}
animation: bounce 0.6s ease-in-out infinite;
```

#### Tool Call Expander
```css
/* Button */
font-size: 9px;
font-weight: 700;
text-transform: uppercase;
color: #006f7c;
padding: 2px 8px;
border-radius: 4px;

/* Expanded container */
background: #ebe8dd;
padding: 12px;
border-radius: 8px;

/* Tool entry */
font-size: 10px;
icon color: #006f7c;
tool name: font-bold, color: #006f7c;
preview: font-mono, opacity: 0.5, color: #383832;
```

### 5.10 AI Insight Panel

#### Container
```css
border: 2px solid #383832;
box-shadow: 4px 4px 0px 0px #383832;
background: white;
margin-top: 1rem;
```

#### Title Bar
```css
padding: 8px 16px;     /* px-4 py-2 */
background: #383832;
color: #feffd6;
display: flex;
justify-content: space-between;
align-items: center;

/* Icon */
material-symbols-outlined: "psychology"
color: #00fc40;
font-size: 1.125rem;

/* Title text */
font-size: 11px;
font-weight: 900;
text-transform: uppercase;
```

#### Action Buttons (in title bar)
```css
/* Copy button */
padding: 4px 8px;
font-size: 9px;
font-weight: 900;
text-transform: uppercase;
border: 1px solid #feffd6;
background: transparent;       /* default */
color: #feffd6;
/* Copied state: */
background: #007518;
color: white;

/* ASK AI button */
padding: 6px 12px;
font-size: 10px;
font-weight: 900;
text-transform: uppercase;
background: #00fc40;
color: #383832;
```

#### Loading State
```css
padding: 24px 16px;
text-align: center;

/* Spinner */
width: 20px; height: 20px;
border: 2px solid #383832;
border-top-color: transparent;
border-radius: 50%;
animation: spin;

/* Text */
font-size: 0.875rem;
font-weight: 700;
text-transform: uppercase;
color: #383832;
```

#### Content Area
```css
padding: 16px;
font-size: 0.75rem;
line-height: relaxed;
color: #383832;
```

#### Footer Bar
```css
padding: 6px 16px;
background: #f6f4e9;
border-top: 1px solid #ebe8dd;
font-size: 9px;
color: #9d9d91;
```

### 5.11 Modals / Tooltips

#### Overlay Backdrop
```css
position: fixed;
inset: 0;
z-index: 40;
/* Used as click-to-close layer (transparent) */
```

#### Dropdown Panel
```css
position: absolute;
top: 100%;
left: 0;
z-index: 50;
margin-top: 4px;
background: white;
border: 2px solid #383832;
box-shadow: 4px 4px 0px 0px #383832;
max-height: 300px;
overflow-y: auto;
```

#### Toast Notification
```css
position: fixed;
top: 80px;     /* top-20 */
right: 24px;   /* right-6 */
z-index: 50;
padding: 12px 16px;
font-size: 0.875rem;
font-weight: 700;
text-transform: uppercase;
letter-spacing: wider;
border: 2px solid #383832;
box-shadow: 4px 4px 0px 0px #383832;

/* Success */ background: #007518; color: white;
/* Error */   background: #be2d06; color: white;

animation: slide-in 0.3s ease-out;
```

### 5.12 Footer Bar

```css
position: fixed;
bottom: 0;
left: 0;
width: 100%;
height: 40px;    /* h-10 */
z-index: 50;
display: flex;
flex-direction: row;
align-items: stretch;
overflow: hidden;
background: #feffd6;
border-top: 3px solid #383832;
```

**Status Segments:**
```css
/* Each segment */
display: flex;
align-items: center;
padding: 0 16px;
height: 100%;
border-right: 2px solid #383832;

/* Text */
font-family: monospace;
font-size: 11px;
font-weight: 700;
letter-spacing: widest;
text-transform: uppercase;

/* First segment (green) */
background: #007518;
color: white;

/* Other segments */
color: #383832;
```

---

## 6. Animations

### 6.1 Boot Sequence
```css
/* Each agent row transitions opacity and border-left color */
transition: all 300ms;
opacity: 1 (active/past) or 0.15 (future);

/* Left border: 3px solid */
Past:    border-color: #007518
Current: border-color: {agent.color}
Future:  border-color: #65655e

/* Background */
Past:    rgba(0,117,24,0.1)
Current: rgba(254,255,214,0.05)
Future:  transparent

/* Spinner for current agent */
width: 16px; height: 16px;
border: 2px solid {agent.color};
border-top-color: transparent;
border-radius: 50%;
animation: spin;

/* Status text */
Past:    "DONE" color: #007518
Current: "RUNNING" color: {agent.color}, animate-pulse
```

Timing: 350ms per agent, 400ms pause before "ALL SYSTEMS OPERATIONAL", 300ms before revealing dashboard.

### 6.2 Thinking Dots (Chat)
```css
@keyframes bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-6px); }
}
animation: bounce 0.6s ease-in-out infinite;
```

### 6.3 Section Stagger (section-animate)
```css
@keyframes sectionFadeIn {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

.section-animate > * {
  opacity: 0;
  animation: sectionFadeIn 0.4s ease-out forwards;
}

/* Stagger delays: */
child 1:  0.05s
child 2:  0.15s
child 3:  0.25s
child 4:  0.35s
child 5:  0.45s
child 6:  0.55s
child 7:  0.65s
child 8:  0.75s
child 9:  0.85s
child 10: 0.95s
child 11+: 1.0s
```

### 6.4 Toast Slide-In
```css
@keyframes slide-in {
  from { transform: translateX(100%); opacity: 0; }
  to { transform: translateX(0); opacity: 1; }
}
animation: slide-in 0.3s ease-out;
```

### 6.5 Skeleton Loading
```css
@keyframes skeleton-pulse {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 0.7; }
}
.skeleton {
  background: #ebe8dd;
  animation: skeleton-pulse 1.5s ease-in-out infinite;
}
```

### 6.6 Button Press Effect
```css
active:translate-x-[2px] active:translate-y-[2px]
```
Simulates a rubber stamp being pressed down, reducing the shadow offset.

### 6.7 Hover Effects
```css
/* Chat suggestions */
hover:translate-y-[-1px]

/* Nav items */
hover: background: #007518; color: white;

/* General */
transition-colors
hover:opacity-80
```

---

## 7. Icons

### 7.1 Icon Library

**Google Material Symbols Outlined**

```css
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap');

.material-symbols-outlined {
  font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24;
  vertical-align: middle;
}
```

### 7.2 Common Icon Mappings

| Icon Name | Usage |
|---|---|
| `psychology` | AI assistant avatar, AI insight panel |
| `dashboard` | Dashboard nav/tab |
| `search` | Search, site dive |
| `local_gas_station` | Fuel-related items |
| `bolt` | Loading state, blackout agent |
| `warning` | Risk/danger |
| `check_circle` | Completed/success |
| `error` | Error state |
| `send` | Chat send button |
| `delete` | Clear chat |
| `build` | Tools used |
| `terminal` | Tool call entry |
| `content_copy` | Copy button |
| `refresh` | Refresh/retry |
| `download` | Export/download |
| `cloud_upload` | File upload drop zone |
| `tune` | Filter toggle |
| `restart_alt` | Reset filters |
| `lan` | Connectivity status |
| `speed` | DB sync status |
| `timer` | Session timer |
| `check_circle` | Operational status |
| `security` | Auth agent |
| `storage` | Data agent |
| `analytics` | Analytics agent |
| `show_chart` | Chart agent |
| `precision_manufacturing` | Operations tab |
| `query_stats` | Predictions tab |
| `map` | Sectors tab |
| `history` | Trends tab |
| `toggle_on` | Operating modes |
| `storefront` | CMHL (retail) |
| `apartment` | CP (property) |
| `bakery_dining` | CFC (F&B) |
| `local_shipping` | PG (distribution) |
| `point_of_sale` | Sales data |
| `database` | Reference data |
| `delete_forever` | Nuclear purge |
| `pending` | Running tool |
| `radio_button_unchecked` | Not started |

### 7.3 Icon Sizes

| Tailwind | Context |
|---|---|
| `text-5xl` | Empty state decorative |
| `text-4xl` | Loading spinner, drop zone |
| `text-2xl` | Chapter heading icons, danger zone |
| `text-xl` | Chat header, error icon |
| `text-lg` | AI panel icon, sync card |
| `text-base` | Tab icons |
| `text-sm` | Nav, table icons, boot sequence |
| `text-xs` | Inline tool icons, action buttons |

---

## 8. CSS Utility Classes

### 8.1 Custom Classes (app.css)

| Class | Effect |
|---|---|
| `.ink-border` | Asymmetric border: top/left 2px, bottom/right 3px, solid, color: var(--on-background) |
| `.stamp-shadow` | `box-shadow: 4px 4px 0px 0px var(--on-background)` |
| `.tab-active` | `background: var(--on-background); color: var(--surface)` |
| `.custom-scrollbar` | 8px wide, track: var(--surface-container), thumb: var(--on-background) |
| `.font-headline` | `font-family: 'Space Grotesk', sans-serif` |
| `.skeleton` | Loading placeholder with pulse animation |
| `.section-animate` | Staggered fade-in for children |
| `.animate-slide-in` | Toast notification slide from right |

### 8.2 Global Overrides

```css
* { border-radius: 0px !important; }  /* No rounded corners anywhere */
::selection { background: #007518; color: white; }  /* Green text selection */
```

### 8.3 Tailwind Patterns Used

```
/* Layout */
flex, grid, items-center, justify-between, gap-{n}
sticky, fixed, absolute, relative, z-{n}

/* Spacing */
p-{n}, px-{n}, py-{n}, m-{n}, mx-auto, space-y-{n}

/* Sizing */
w-full, h-full, max-w-{size}, min-w-[{px}]

/* Typography */
text-{size}, font-{weight}, uppercase, tracking-{style}
truncate, whitespace-nowrap, leading-relaxed

/* Display */
hidden, md:flex, lg:flex, inline-block, inline-flex

/* Effects */
transition-all, transition-colors
active:translate-x-[2px] active:translate-y-[2px]
hover:opacity-80, hover:translate-y-[-1px]
animate-pulse, animate-spin, animate-bounce

/* Overflow */
overflow-x-auto, overflow-y-auto, overflow-hidden
```

---

## 9. Dark Patterns (sidebar, header, dark sections)

### 9.1 Dark Title Bars
```css
background: #383832;
color: #feffd6;
```
Used for: table headers, chapter headings, AI insight panel header, boot sequence, filter bar tags.

### 9.2 Boot Sequence Full Dark
```css
background: #383832;           /* full page */
text color: #feffd6 (primary), #65655e (muted), #9d9d91 (timestamp)
accent: #00fc40 (complete), #007518 (success)
```

### 9.3 Chat Header Bar
```css
background: #383832;
border-bottom: 2px solid #383832;
Title: color: #feffd6;
Status badge: background: #007518 (online) or #be2d06 (offline);
Icon: color: #00fc40;
```

### 9.4 Data Model Terminal
```css
background: #1a1a1a;
color: #00ff41 (green terminal text);
color: #ccc (normal text);
color: #888 (comments);
color: #555 (muted);
color: #ff9d00 (foreign keys);
```

### 9.5 Section Header (upload)
```css
padding: 16px;
color: white;
border: 2px solid #383832;
box-shadow: 4px 4px 0px 0px #383832;
background: #007518 (daily) or #006f7c (reference);
```

---

## 10. Code Snippets

### 10.1 KPI Card

```html
<div style="
  padding: 16px;
  background: white;
  border-top: 2px solid #383832;
  border-left: 2px solid #383832;
  border-bottom: 4px solid #383832;
  border-right: 4px solid #383832;
  box-shadow: 4px 4px 0px 0px rgba(56, 56, 50, 1);
">
  <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
    <span style="display: inline-block; padding: 2px 8px; font-size: 10px; font-weight: 900; text-transform: uppercase; background: #383832; color: #feffd6;">FUEL USED</span>
    <span class="material-symbols-outlined" style="color: #007518;">local_gas_station</span>
  </div>
  <div style="font-size: 2.25rem; font-weight: 900; letter-spacing: -0.05em; color: #383832;">
    12,450<span style="font-size: 1.125rem;">L</span>
  </div>
  <div style="margin-top: 12px; height: 8px; background: #ebe8dd; border: 1px solid #383832;">
    <div style="height: 100%; width: 65%; background: #007518;"></div>
  </div>
  <div style="margin-top: 8px; font-size: 10px; text-transform: uppercase; opacity: 0.6; font-weight: 700; color: #383832;">207.5 L per site</div>
</div>
```

### 10.2 Data Table with Header

```html
<div style="border: 2px solid #383832; box-shadow: 4px 4px 0px 0px #383832;">
  <!-- Title bar -->
  <div style="padding: 8px 16px; background: #383832; color: #feffd6; display: flex; justify-content: space-between; align-items: center;">
    <span style="font-weight: 900; text-transform: uppercase; font-size: 0.875rem;">OPERATING_MODES</span>
    <span style="font-size: 10px; font-weight: 700; padding: 2px 8px; background: #feffd6; color: #383832;">60 SITES</span>
  </div>
  <div style="background: white; overflow-x: auto;">
    <table style="width: 100%; border-collapse: collapse; font-size: 0.75rem;">
      <thead style="background: #ebe8dd;">
        <tr>
          <th style="padding: 8px 16px; text-align: left; font-weight: 900; text-transform: uppercase; font-size: 10px; border-bottom: 2px solid #383832;">SITE</th>
          <th style="padding: 8px 16px; text-align: left; font-weight: 900; text-transform: uppercase; font-size: 10px; border-bottom: 2px solid #383832;">MODE</th>
          <th style="padding: 8px 16px; text-align: left; font-weight: 900; text-transform: uppercase; font-size: 10px; border-bottom: 2px solid #383832;">BUFFER</th>
        </tr>
      </thead>
      <tbody>
        <tr style="border-bottom: 1px solid rgba(56,56,50,0.15);">
          <td style="padding: 10px 16px; font-weight: 700; color: #383832;">CMHL-MKT01</td>
          <td style="padding: 10px 16px;"><span style="background: #007518; color: white; padding: 2px 10px; font-size: 0.75rem; font-weight: 800; text-transform: uppercase;">FULL</span></td>
          <td style="padding: 10px 16px; color: #007518; font-weight: 700;">12.5d</td>
        </tr>
        <tr style="border-bottom: 1px solid rgba(56,56,50,0.15); background: #fcf9ef;">
          <td style="padding: 10px 16px; font-weight: 700; color: #383832;">CFC-SBFTY</td>
          <td style="padding: 10px 16px;"><span style="background: #be2d06; color: white; padding: 2px 10px; font-size: 0.75rem; font-weight: 800; text-transform: uppercase;">CLOSE</span></td>
          <td style="padding: 10px 16px; color: #be2d06; font-weight: 700;">0.8d</td>
        </tr>
      </tbody>
    </table>
  </div>
</div>
```

### 10.3 Chapter Heading

```html
<div style="padding: 12px 16px; background: #383832; color: #feffd6; margin-bottom: 12px;">
  <div style="display: flex; align-items: center; gap: 12px;">
    <span class="material-symbols-outlined" style="font-size: 1.5rem; color: #ff9d00;">toggle_on</span>
    <div>
      <div style="font-weight: 900; text-transform: uppercase; font-size: 0.875rem;">CHAPTER 1: OPERATING MODES</div>
      <div style="font-size: 10px; opacity: 0.75;">Should each site stay OPEN, MONITOR, REDUCE hours, or CLOSE?</div>
    </div>
  </div>
  <div style="margin-top: 8px; font-size: 0.75rem; font-family: monospace; padding-left: 32px; color: #00fc40;">? Which sites should reduce generator hours? Who should close?</div>
</div>
```

### 10.4 Badge

```html
<!-- Severity badge -->
<span style="display: inline-block; padding: 2px 6px; font-size: 9px; font-weight: 900; text-transform: uppercase; background: #be2d06; color: white;">CRITICAL</span>

<!-- Warning badge -->
<span style="display: inline-block; padding: 2px 6px; font-size: 9px; font-weight: 900; text-transform: uppercase; background: #ff9d00; color: white;">WARNING</span>

<!-- Info badge -->
<span style="display: inline-block; padding: 2px 6px; font-size: 9px; font-weight: 900; text-transform: uppercase; background: #65655e; color: white;">INFO</span>

<!-- Category badge -->
<span style="display: inline-block; padding: 2px 8px; font-size: 9px; font-weight: 700; text-transform: uppercase; background: #007518; color: white;">DAILY</span>

<!-- Grade badge -->
<span style="font-weight: 900; font-size: 1.5rem; color: #007518;">A</span>
```

### 10.5 Button (Primary + Stamp Shadow)

```html
<!-- Primary CTA -->
<button style="
  padding: 12px 32px;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-size: 0.875rem;
  font-family: 'Space Grotesk', sans-serif;
  background: #00fc40;
  color: #383832;
  border: 2px solid #383832;
  box-shadow: 4px 4px 0px 0px #383832;
  cursor: pointer;
">SUBMIT_UPLOAD</button>

<!-- Secondary -->
<button style="
  padding: 8px 16px;
  font-weight: 900;
  text-transform: uppercase;
  font-size: 0.75rem;
  background: #007518;
  color: white;
  border: 2px solid #383832;
  box-shadow: 4px 4px 0px 0px #383832;
  cursor: pointer;
">EXECUTE</button>

<!-- Danger -->
<button style="
  padding: 8px 24px;
  font-weight: 900;
  text-transform: uppercase;
  font-size: 0.75rem;
  background: #be2d06;
  color: #feffd6;
  border: 2px solid #383832;
  box-shadow: 4px 4px 0px 0px #383832;
  cursor: pointer;
">RESET</button>
```

### 10.6 Form Input with Label Tag

```html
<div>
  <div style="display: inline-block; padding: 2px 8px; font-size: 10px; font-weight: 900; text-transform: uppercase; background: #383832; color: #feffd6; margin-bottom: 4px;">OPERATOR_ID</div>
  <input type="text" placeholder="Enter credentials" style="
    width: 100%;
    padding: 12px 16px;
    font-size: 0.875rem;
    font-weight: 700;
    font-family: 'Space Grotesk', sans-serif;
    background: white;
    border: 2px solid #383832;
    color: #383832;
    border-radius: 0;
  " />
</div>
```

### 10.7 Status Indicator

```html
<!-- Dot indicator (used in login, sync cards) -->
<div style="display: flex; align-items: center; gap: 8px; font-size: 10px; text-transform: uppercase; letter-spacing: 0.1em; font-weight: 700; color: #383832; opacity: 0.4;">
  <span style="width: 8px; height: 8px; background: #007518; display: inline-block;"></span>
  NODE_ACTIVE
</div>

<!-- Online/Offline badge -->
<span style="font-size: 9px; padding: 2px 8px; font-weight: 700; text-transform: uppercase; background: #007518; color: white;">ONLINE</span>
<span style="font-size: 9px; padding: 2px 8px; font-weight: 700; text-transform: uppercase; background: #be2d06; color: white;">OFFLINE</span>

<!-- Freshness indicator -->
<span style="padding: 2px 6px; font-size: 8px; font-weight: 900; background: #007518; color: white;">1d ago</span>
<span style="padding: 2px 6px; font-size: 8px; font-weight: 900; background: #ff9d00; color: white;">5d ago</span>
<span style="padding: 2px 6px; font-size: 8px; font-weight: 900; background: #be2d06; color: white;">14d ago</span>
```

### 10.8 Login Form Container

```html
<form style="
  padding: 32px;
  background: #f6f4e9;
  border-top: 2px solid #383832;
  border-left: 2px solid #383832;
  border-bottom: 3px solid #383832;
  border-right: 3px solid #383832;
  box-shadow: 4px 4px 0px 0px #383832;
">
  <!-- Error message -->
  <div style="padding: 12px; margin-bottom: 24px; font-weight: 700; font-size: 0.875rem; text-transform: uppercase; background: #be2d06; color: white; border: 2px solid #383832;">
    AUTHENTICATION_FAILED
  </div>

  <!-- Field -->
  <div style="margin-bottom: 20px;">
    <div style="display: inline-block; padding: 2px 8px; font-size: 10px; font-weight: 900; text-transform: uppercase; background: #383832; color: #feffd6; margin-bottom: 4px;">OPERATOR_ID</div>
    <input type="text" placeholder="Enter credentials" style="width: 100%; padding: 12px 16px; font-size: 0.875rem; font-weight: 700; font-family: 'Space Grotesk', sans-serif; background: white; border: 2px solid #383832; color: #383832;" />
  </div>

  <!-- Submit -->
  <button type="submit" style="width: 100%; padding: 16px; font-weight: 900; text-transform: uppercase; letter-spacing: 0.05em; font-size: 0.875rem; background: #00fc40; color: #383832; border: 2px solid #383832; cursor: pointer;">
    INITIATE_AUTHENTICATION
  </button>
</form>
```

### 10.9 Tab Bar

```html
<div style="display: flex; gap: 0; background: #ebe8dd; border: 2px solid #383832;">
  <!-- Active tab -->
  <button style="padding: 10px 12px; font-weight: 700; text-transform: uppercase; letter-spacing: -0.025em; font-size: 11px; white-space: nowrap; background: #383832; color: #feffd6;">DAILY_DATA</button>
  <!-- Inactive tab -->
  <button style="padding: 10px 12px; font-weight: 700; text-transform: uppercase; letter-spacing: -0.025em; font-size: 11px; white-space: nowrap; background: transparent; color: #65655e;">REFERENCE_DATA</button>
  <button style="padding: 10px 12px; font-weight: 700; text-transform: uppercase; letter-spacing: -0.025em; font-size: 11px; white-space: nowrap; background: transparent; color: #65655e;">DATA_QUALITY</button>
</div>
```

### 10.10 Drop Zone

```html
<div style="
  padding: 40px;
  text-align: center;
  cursor: pointer;
  background: white;
  border: 3px dashed #383832;
  transition: all;
">
  <span class="material-symbols-outlined" style="font-size: 2.25rem; color: #007518;">cloud_upload</span>
  <p style="font-size: 0.875rem; font-weight: 900; text-transform: uppercase; margin-top: 8px; color: #383832;">DROP_DAILY_FILES_HERE</p>
  <p style="font-size: 10px; font-weight: 700; text-transform: uppercase; margin-top: 4px; color: #65655e;">Blackout, fuel price, recent sales</p>
</div>

<!-- Drag-over state: -->
<!-- background: #ebe8dd; border-color: #007518; -->
```

### 10.11 Sync Status Card

```html
<button style="
  padding: 12px;
  text-align: left;
  border: 2px solid #383832;
  background: #f6f4e9;
  box-shadow: 3px 3px 0px 0px #383832;
">
  <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
    <span class="material-symbols-outlined" style="font-size: 0.875rem; color: #007518;">storefront</span>
    <span style="width: 8px; height: 8px; background: #007518;"></span>
  </div>
  <div style="font-size: 10px; font-weight: 900; text-transform: uppercase; color: #383832;">CMHL</div>
  <div style="font-size: 9px; font-weight: 700; margin-top: 4px; color: #007518;">1,250 ROWS</div>
  <div style="font-size: 8px; font-weight: 700; color: #65655e;">2026-04-07 14:30</div>
  <div style="margin-top: 4px; padding: 2px 6px; font-size: 8px; font-weight: 900; text-align: center; background: #007518; color: white;">1d ago</div>
</button>
```

### 10.12 AI Insight Panel

```html
<div style="border: 2px solid #383832; box-shadow: 4px 4px 0px 0px #383832; background: white; margin-top: 1rem;">
  <!-- Header -->
  <div style="padding: 8px 16px; background: #383832; color: #feffd6; display: flex; justify-content: space-between; align-items: center;">
    <div style="display: flex; align-items: center; gap: 8px;">
      <span class="material-symbols-outlined" style="font-size: 1.125rem; color: #00fc40;">psychology</span>
      <span style="font-size: 11px; font-weight: 900; text-transform: uppercase;">AI EXECUTIVE BRIEFING</span>
    </div>
    <button style="padding: 6px 12px; font-size: 10px; font-weight: 900; text-transform: uppercase; background: #00fc40; color: #383832;">
      <span class="material-symbols-outlined" style="font-size: 0.875rem;">psychology</span> ASK AI
    </button>
  </div>
  <!-- Empty state -->
  <div style="padding: 16px; text-align: center;">
    <span class="material-symbols-outlined" style="font-size: 1.5rem; color: #ebe8dd;">psychology</span>
    <p style="font-size: 10px; margin-top: 4px; color: #9d9d91;">Click ASK AI to generate analysis</p>
  </div>
</div>
```

---

## Appendix: Complete Hex Color Reference

All hex colors used across the frontend, sorted by usage frequency:

| Hex | Count | Role |
|---|---|---|
| `#383832` | ~200+ | Primary dark (text, borders, backgrounds, shadows) |
| `#feffd6` | ~50+ | Surface yellow (page bg, dark-on-light text) |
| `#007518` | ~40+ | Primary green (success, safe, active) |
| `#be2d06` | ~30+ | Error red (critical, danger, failure) |
| `#ff9d00` | ~25+ | Amber (warning, monitor, uploading) |
| `#65655e` | ~25+ | Warm gray (muted text, disabled, subtitles) |
| `#ebe8dd` | ~20+ | Light warm gray (table headers, skeleton, tracks) |
| `#f6f4e9` | ~15+ | Container bg (forms, filter bar, chat area) |
| `#006f7c` | ~15+ | Teal (secondary, tool names, data types) |
| `#00fc40` | ~12+ | Bright green (CTA buttons, terminal prompt) |
| `#9d4867` | ~8+ | Mauve (tertiary, avatar, LIVE badge) |
| `#fcf9ef` | ~8+ | Alternating row bg |
| `#f95630` | ~5+ | Orange-red (REDUCE mode, grade D) |
| `#fe97b9` | ~3+ | Pink (tertiary accent bg, clear link) |
| `#828179` | ~3+ | Outline gray (placeholder, muted icon) |
| `#e85d04` | ~3+ | Burnt orange (fuel column header, fuel agent) |
| `#9d9d91` | ~3+ | Light gray (timestamps, annotations) |
| `#4a4a44` | ~2+ | Dark gray (boot bg track, inactive text) |
| `#1a1a1a` | ~2+ | Near-black (terminal bg) |
| `#00ff41` | ~2+ | Terminal green (ERD primary keys) |
| `#26e6ff` | ~1 | Bright cyan (secondary container, unused) |
| `#bbb9b1` | ~1 | Outline variant (defined, rarely used) |
| `#fff3cd` | ~2+ | Warning yellow bg |
| `#C6EFCE` | ~4+ | Validation pass cell bg |
| `#FFC7CE` | ~4+ | Validation fail cell bg |
| `#856404` | ~2+ | Warning brown text |
