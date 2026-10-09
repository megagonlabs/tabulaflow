# What is TabulaFlow?

TabulaFlow is an open-source data agent built on a modular Python library.

Think of it as Claude Code for data: describe in natural language what you want
to analyze, visualize, or transform. It works with all kinds of data, including
SQL and graph databases, files, Hugging Face datasets, Wikidata, and web pages.

Unlike existing coding-agent harnesses, which are built around files and the
shell, TabulaFlow treats tables as first-class citizens, as its name suggests:

- **Agent ergonomics.** The agent writes only queries and
  visualization specifications. TabulaFlow handles data resolution and
  rendering, so the agent never wastes tokens handcrafting data values or HTML
  to create visual artifacts.
- **Human ergonomics.** Data provenance is automatically tracked: each
  visualization exposes its underlying data table, and each table exposes the
  query that produced it.
- **Shell-independent.** The core harness remains fully functional for data work
  even when shell and filesystem access are disabled (e.g., when building
  hosted applications).

Like a general-purpose coding agent, TabulaFlow can also write code, run shell
commands, and browse the web.

<div class="demo-gallery" id="demo-gallery">
  <span class="demo-gallery__anchor" id="demo-disambiguation" data-tab-id="demo-tab-disambiguation" aria-hidden="true"></span>
  <span class="demo-gallery__anchor" id="demo-research" data-tab-id="demo-tab-research" aria-hidden="true"></span>
  <span class="demo-gallery__anchor" id="demo-travel" data-tab-id="demo-tab-travel" aria-hidden="true"></span>
  <span class="demo-gallery__anchor" id="demo-database" data-tab-id="demo-tab-database" aria-hidden="true"></span>
  <span class="demo-gallery__anchor" id="demo-wikidata" data-tab-id="demo-tab-wikidata" aria-hidden="true"></span>
  <span class="demo-gallery__anchor" id="demo-hugging-face" data-tab-id="demo-tab-hugging-face" aria-hidden="true"></span>
  <div class="demo-gallery__tabs" role="tablist" aria-label="TabulaFlow demos">
    <button type="button" role="tab" id="demo-tab-disambiguation" aria-selected="true" data-anchor-id="demo-disambiguation"
      data-title="Get Precise Data via Interactive Disambiguation"
      data-description="Resolve an ambiguous question with an interactive, parameterized visualization."
      data-type="Structured disambiguation"
      data-video-src="assets/demos/structured-disambiguation.mp4">Get Precise Data via Interactive Disambiguation</button>
    <button type="button" role="tab" id="demo-tab-research" aria-selected="false" tabindex="-1" data-anchor-id="demo-research"
      data-title="Build a Research Paper Database"
      data-description="Build a comprehensive, structured database of conference papers on a research topic."
      data-type="Research workflow"
      data-video-src="assets/demos/find-research-papers.mp4">Build a Research Paper Database</button>
    <button type="button" role="tab" id="demo-tab-travel" aria-selected="false" tabindex="-1" data-anchor-id="demo-travel"
      data-title="Plan a trip on a map"
      data-description="Find museums, add neighborhood boundaries, and map a walking route."
      data-type="Mapping workflow"
      data-video-src="assets/demos/plan-a-trip-on-a-map.mp4">Plan a Trip on a Map</button>
    <button type="button" role="tab" id="demo-tab-database" aria-selected="false" tabindex="-1" data-anchor-id="demo-database"
      data-title="Chat to a Bioinformatics MySQL db"
      data-description="Connect a bioinformatics MySQL database and ask TabulaFlow to introduce and explore it."
      data-type="Database workflow"
      data-video-src="assets/demos/chat-to-a-database.mp4">Chat to a Bioinformatics MySQL db</button>
    <button type="button" role="tab" id="demo-tab-wikidata" aria-selected="false" tabindex="-1" data-anchor-id="demo-wikidata"
      data-title="Query and Visualize Graphs"
      data-description="Ask a knowledge-graph question, inspect the results, and explore their relationships."
      data-type="Knowledge graph workflow"
      data-video-src="assets/demos/query-wikidata.mp4">Query and Visualize Graphs</button>
    <button type="button" role="tab" id="demo-tab-hugging-face" aria-selected="false" tabindex="-1" data-anchor-id="demo-hugging-face"
      data-title="Explore a multimodal Hugging Face dataset"
      data-description="Connect a multimodal Hugging Face dataset and explore its schema, rows, and media."
      data-type="Data browsing workflow"
      data-video-src="assets/demos/explore-a-multimodal-hugging-face-dataset.mp4">Explore a Multimodal Hugging Face Dataset</button>
  </div>
  <div class="demo-gallery__stage" role="tabpanel" aria-labelledby="demo-tab-disambiguation">
    <video class="demo-gallery__video" controls preload="metadata"
      src="assets/demos/structured-disambiguation.mp4" aria-label="TabulaFlow interactive disambiguation and visualization demo"></video>
    <figure class="media-placeholder media-placeholder--video" aria-live="polite" hidden>
      <div class="media-placeholder__content">
        <span class="media-placeholder__type">Structured disambiguation</span>
        <strong>Get Precise Data via Interactive Disambiguation</strong>
        <span>Resolve an ambiguous question with an interactive, parameterized visualization.</span>
      </div>
      <figcaption>Production placeholder · Include captions and a text transcript.</figcaption>
    </figure>
  </div>
</div>

## Get started

Install TabulaFlow with [`uv`](https://docs.astral.sh/uv/), set a model provider
key, and launch it:

```bash
uv tool install tabulaflow
export OPENAI_API_KEY="your-api-key"
tabulaflow
```

See [Models and providers](models.md) for Anthropic, vLLM, and other providers.

We also recommend installing Chromium to enable agent-driven web browsing:

```bash
uv tool run --from playwright playwright install chromium
```

TabulaFlow opens with bundled sample data, so you can start exploring
immediately.

## What TabulaFlow can do

Consider TabulaFlow if you regularly analyze data in Jupyter notebooks, explore
databases with DBeaver or Neo4j Browser, work with Hugging Face datasets or
Wikidata, or conduct deep research with structured
datasets.

<ul>
<li><strong>Interactive visualization.</strong> Create charts, maps, and relationship graphs
  backed by queryable, parameterized data, including graphs from Neo4j.
  <div class="demo-links">
    <a class="demo-cta" href="#demo-disambiguation">Disambiguation demo</a>
    <a class="demo-cta" href="#demo-travel">Map demo</a>
    <a class="demo-cta" href="#demo-wikidata">Graph demo</a>
    <a class="demo-cta" href="#demo-research">Research papers demo</a>
    <a class="demo-cta" href="#demo-database">MySQL demo</a>
  </div>
</li>
<li><strong>Structured disambiguation for precise answer.</strong> Get precise data and answer when there is
  ambiguity via interactive structured disambiguation proposed in the
  <a href="research/arcs/">ARCS paper</a>.
  <div class="demo-links">
    <a class="demo-cta" href="#demo-disambiguation">Disambiguation demo</a>
  </div>
</li>
<li><strong>Multimodal data browsing.</strong> Browse databases or Hugging Face datasets
  directly (no LLM needed). View images, PDFs, and other media directly inside
  tables, or ask an agent to analyze them.
  <div class="demo-links">
    <a class="demo-cta" href="#demo-hugging-face">Hugging Face demo</a>
  </div>
</li>
<li><strong>Cross-source analysis.</strong> Combine files and databases in a local workspace
  without changing the original sources.</li>
<li><strong>Large-scale dataset construction.</strong> Combine multiple sources and turn
  unstructured web pages and documents into structured, normalized tables with
  thousands of rows for deep research.
  <div class="demo-links">
    <a class="demo-cta" href="#demo-research">Research paper database demo</a>
  </div>
</li>
<li><strong>Agentic data enrichment.</strong> Enrich each row with an agent that can browse
  the web, query connected databases, and return typed results. Process many
  rows concurrently.
  <div class="demo-links">
    <a class="demo-cta" href="#demo-research">Research paper database demo</a>
    <a class="demo-cta" href="#demo-travel">Map demo</a>
  </div>
</li>
<li><strong>Parallel browser use.</strong> TabulaFlow's browser harness lets agents interact
  with many web pages in parallel during complex deep research tasks, including
  pages that require clicks and forms.</li>
</ul>


## How does TabulaFlow work?

<div class="trajectory-comparison" markdown="1">

<div class="trajectory-question" markdown="1">

Show an interactive chart of NYC taxi-zone counts by borough, with an
all/Manhattan-only choice control and a minimum-zone-area slider.

</div>

<div class="trajectory-columns" markdown="1">

<div class="trajectory-card trajectory-card--tabulaflow" markdown="1">

<div class="trajectory-harness-label">TabulaFlow <span class="trajectory-token-count" title="Displayed code payloads, o200k_base tokenizer">189 tokens</span></div>

<div class="trajectory-call trajectory-call--source" markdown="1">

<div class="trajectory-call__header"><code>create_parameterized_source</code></div>

<pre class="trajectory-code no-copy"><code>parameters: <span class="p">[{</span><span class="nt">"kind"</span><span class="p">:</span><span class="s2">"choice"</span><span class="p">,</span><span class="nt">"id"</span><span class="p">:</span><span class="s2">"nyc_scope"</span><span class="p">,</span><span class="nt">"label"</span><span class="p">:</span><span class="s2">"Borough scope"</span><span class="p">,</span><span class="nt">"choices"</span><span class="p">:[{</span><span class="nt">"id"</span><span class="p">:</span><span class="s2">"all"</span><span class="p">,</span><span class="nt">"label"</span><span class="p">:</span><span class="s2">"All boroughs"</span><span class="p">},{</span><span class="nt">"id"</span><span class="p">:</span><span class="s2">"manhattan"</span><span class="p">,</span><span class="nt">"label"</span><span class="p">:</span><span class="s2">"Manhattan only"</span><span class="p">}]},{</span><span class="nt">"kind"</span><span class="p">:</span><span class="s2">"number"</span><span class="p">,</span><span class="nt">"id"</span><span class="p">:</span><span class="s2">"nyc_min_area"</span><span class="p">,</span><span class="nt">"label"</span><span class="p">:</span><span class="s2">"Minimum zone area (×10⁻⁶ source units)"</span><span class="p">,</span><span class="nt">"min"</span><span class="p">:</span><span class="mi">0</span><span class="p">,</span><span class="nt">"max"</span><span class="p">:</span><span class="mi">1000</span><span class="p">,</span><span class="nt">"step"</span><span class="p">:</span><span class="mi">25</span><span class="p">,</span><span class="nt">"default"</span><span class="p">:</span><span class="mi">0</span><span class="p">}]</span>
---
<span class="k">SELECT</span><span class="w"> </span><span class="n">borough</span>
<span class="k">FROM</span><span class="w"> </span><span class="n">nyc_taxi_zones</span>
<span class="k">WHERE</span><span class="w"> </span><span class="n">shape_area</span><span class="w"> </span><span class="o">*</span><span class="w"> </span><span class="mi">1000000</span><span class="w"> </span><span class="o">&gt;=</span><span class="w"> </span><span class="err">{{</span><span class="w"> </span><span class="n">nyc_min_area</span><span class="w"> </span><span class="err">}}</span>
<span class="err">{</span><span class="o">%</span><span class="w"> </span><span class="k">if</span><span class="w"> </span><span class="n">nyc_scope</span><span class="w"> </span><span class="o">==</span><span class="w"> </span><span class="s1">'manhattan'</span><span class="w"> </span><span class="o">%</span><span class="err">}</span>
<span class="w">  </span><span class="k">AND</span><span class="w"> </span><span class="n">borough</span><span class="w"> </span><span class="o">=</span><span class="w"> </span><span class="s1">'Manhattan'</span>
<span class="err">{</span><span class="o">%</span><span class="w"> </span><span class="n">endif</span><span class="w"> </span><span class="o">%</span><span class="err">}</span></code></pre>

</div>

<div class="trajectory-call" markdown="1">

<div class="trajectory-call__header"><code>render_chart</code><span class="trajectory-call__filename">source=S1</span></div>

<pre class="trajectory-code no-copy"><code><span class="p">{</span>
<span class="w">  </span><span class="nt">"mark"</span><span class="p">:</span><span class="w"> </span><span class="s2">"bar"</span><span class="p">,</span>
<span class="w">  </span><span class="nt">"encoding"</span><span class="p">:</span><span class="w"> </span><span class="p">{</span>
<span class="w">    </span><span class="nt">"x"</span><span class="p">:</span><span class="w"> </span><span class="p">{</span><span class="nt">"field"</span><span class="p">:</span><span class="w"> </span><span class="s2">"borough"</span><span class="p">,</span><span class="w"> </span><span class="nt">"type"</span><span class="p">:</span><span class="w"> </span><span class="s2">"nominal"</span><span class="p">},</span>
<span class="w">    </span><span class="nt">"y"</span><span class="p">:</span><span class="w"> </span><span class="p">{</span><span class="nt">"aggregate"</span><span class="p">:</span><span class="w"> </span><span class="s2">"count"</span><span class="p">,</span><span class="w"> </span><span class="nt">"type"</span><span class="p">:</span><span class="w"> </span><span class="s2">"quantitative"</span><span class="p">}</span>
<span class="w">  </span><span class="p">}</span>
<span class="p">}</span></code></pre>

</div>

</div>

<div class="trajectory-card trajectory-card--codex" markdown="1">

<div class="trajectory-harness-label">Codex <span class="trajectory-token-count" title="Displayed code payloads, o200k_base tokenizer">2,768 tokens</span></div>

<details class="trajectory-preparation" markdown="1">
<summary><span class="trajectory-preparation__show">Show 2 tool calls</span><span class="trajectory-preparation__hide">Hide 2 tool calls</span></summary>

<div class="trajectory-call" markdown="1">

<div class="trajectory-call__header"><code>exec_command</code></div>

<pre class="trajectory-code no-copy"><code><span class="kn">import</span><span class="w"> </span><span class="nn">sqlite3</span><span class="o">,</span><span class="w"> </span><span class="nn">json</span>
<span class="n">c</span> <span class="o">=</span> <span class="n">sqlite3</span><span class="o">.</span><span class="n">connect</span><span class="p">(</span><span class="s1">'upload/sample(1).sqlite'</span><span class="p">)</span>
<span class="n">rows</span> <span class="o">=</span> <span class="n">c</span><span class="o">.</span><span class="n">execute</span><span class="p">(</span><span class="s1">'SELECT borough, shape_area FROM nyc_taxi_zones WHERE borough IS NOT NULL AND shape_area IS NOT NULL'</span><span class="p">)</span><span class="o">.</span><span class="n">fetchall</span><span class="p">()</span>
<span class="nb">print</span><span class="p">(</span><span class="nb">len</span><span class="p">(</span><span class="n">rows</span><span class="p">))</span>
<span class="nb">print</span><span class="p">(</span><span class="n">json</span><span class="o">.</span><span class="n">dumps</span><span class="p">(</span><span class="n">rows</span><span class="p">))</span>
<span class="nb">print</span><span class="p">(</span><span class="n">c</span><span class="o">.</span><span class="n">execute</span><span class="p">(</span><span class="s1">'SELECT borough, COUNT(*), MIN(shape_area), MAX(shape_area) FROM nyc_taxi_zones GROUP BY borough'</span><span class="p">)</span><span class="o">.</span><span class="n">fetchall</span><span class="p">())</span></code></pre>

</div>

<div class="trajectory-call" markdown="1">

<div class="trajectory-call__header"><code>exec_command</code></div>

<pre class="trajectory-code no-copy"><code><span class="kn">import</span><span class="w"> </span><span class="nn">sqlite3</span><span class="o">,</span><span class="w"> </span><span class="nn">json</span>
<span class="n">c</span> <span class="o">=</span> <span class="n">sqlite3</span><span class="o">.</span><span class="n">connect</span><span class="p">(</span><span class="s1">'upload/sample(1).sqlite'</span><span class="p">)</span>
<span class="n">d</span> <span class="o">=</span> <span class="p">{</span><span class="n">b</span><span class="p">:</span> <span class="p">[</span><span class="nb">round</span><span class="p">(</span><span class="n">a</span> <span class="o">*</span> <span class="mi">1000000</span><span class="p">,</span> <span class="mi">1</span><span class="p">)</span> <span class="k">for</span> <span class="n">a</span><span class="p">,</span> <span class="ow">in</span> <span class="n">c</span><span class="o">.</span><span class="n">execute</span><span class="p">(</span><span class="s1">'SELECT shape_area FROM nyc_taxi_zones WHERE borough=? ORDER BY shape_area'</span><span class="p">,</span> <span class="p">(</span><span class="n">b</span><span class="p">,))]</span> <span class="k">for</span> <span class="n">b</span> <span class="ow">in</span> <span class="p">[</span><span class="s1">'Bronx'</span><span class="p">,</span> <span class="s1">'Brooklyn'</span><span class="p">,</span> <span class="s1">'EWR'</span><span class="p">,</span> <span class="s1">'Manhattan'</span><span class="p">,</span> <span class="s1">'Queens'</span><span class="p">,</span> <span class="s1">'Staten Island'</span><span class="p">]}</span>
<span class="nb">print</span><span class="p">(</span><span class="n">json</span><span class="o">.</span><span class="n">dumps</span><span class="p">(</span><span class="n">d</span><span class="p">,</span> <span class="n">separators</span><span class="o">=</span><span class="p">(</span><span class="s1">','</span><span class="p">,</span> <span class="s1">':'</span><span class="p">)))</span></code></pre>

</div>

</details>

<div class="trajectory-call trajectory-call--patch" markdown="1">

<div class="trajectory-call__header"><code>apply_patch</code><span class="trajectory-call__filename">taxi-zone-borough-counts.html</span></div>

<pre class="trajectory-code no-copy"><code>*** Begin Patch
*** Add File: taxi-zone-borough-counts.html
<span class="trajectory-added">+&lt;div id=&quot;taxi-zone-borough-counts&quot; aria-labelledby=&quot;taxi-chart-title&quot;&gt;</span>
<span class="trajectory-added">+  &lt;style&gt;</span>
<span class="trajectory-added">+    #taxi-zone-borough-counts { color: var(--foreground); font-family: inherit; }</span>
<span class="trajectory-added">+    #taxi-zone-borough-counts .chart-wrap { margin-top: 1rem; width: 100%; }</span>
<span class="trajectory-added">+    #taxi-zone-borough-counts svg { display: block; width: 100%; height: auto; }</span>
<span class="trajectory-added">+    #taxi-zone-borough-counts .grid, #taxi-zone-borough-counts .axis { stroke: var(--border); stroke-width: 1; }</span>
<span class="trajectory-added">+    #taxi-zone-borough-counts .axis { stroke: var(--foreground); }</span>
<span class="trajectory-added">+    #taxi-zone-borough-counts .bar { fill: var(--viz-series-1); transition: height 180ms ease, y 180ms ease, opacity 180ms ease; }</span>
<span class="trajectory-added">+    #taxi-zone-borough-counts .bar-label { fill: var(--foreground); font-size: 12px; font-weight: 500; }</span>
<span class="trajectory-added">+    #taxi-zone-borough-counts .tick, #taxi-zone-borough-counts .axis-title { fill: var(--muted-foreground); font-size: 12px; }</span>
<span class="trajectory-added">+    #taxi-zone-borough-counts .status { margin-top: .5rem; color: var(--muted-foreground); }</span>
<span class="trajectory-added">+    #taxi-zone-borough-counts .control-value { color: var(--foreground); font-weight: 500; }</span>
<span class="trajectory-added">+  &lt;/style&gt;</span>
<span class="trajectory-added">+  &lt;h2 id=&quot;taxi-chart-title&quot;&gt;NYC taxi zones by borough&lt;/h2&gt;</span>
<span class="trajectory-added">+  &lt;div class=&quot;viz-controls&quot; aria-label=&quot;Taxi zone filters&quot;&gt;</span>
<span class="trajectory-added">+    &lt;div&gt;</span>
<span class="trajectory-added">+      &lt;label class=&quot;form-label&quot; for=&quot;borough-scope&quot;&gt;Borough scope&lt;/label&gt;</span>
<span class="trajectory-added">+      &lt;select id=&quot;borough-scope&quot; class=&quot;form-select&quot;&gt;</span>
<span class="trajectory-added">+        &lt;option value=&quot;all&quot;&gt;All boroughs&lt;/option&gt;</span>
<span class="trajectory-added">+        &lt;option value=&quot;Manhattan&quot;&gt;Manhattan only&lt;/option&gt;</span>
<span class="trajectory-added">+      &lt;/select&gt;</span>
<span class="trajectory-added">+    &lt;/div&gt;</span>
<span class="trajectory-added">+    &lt;div&gt;</span>
<span class="trajectory-added">+      &lt;label class=&quot;form-label&quot; for=&quot;min-area&quot;&gt;Minimum zone area &lt;span id=&quot;area-value&quot; class=&quot;control-value&quot;&gt;0&lt;/span&gt;&lt;/label&gt;</span>
<span class="trajectory-added">+      &lt;input id=&quot;min-area&quot; class=&quot;form-range&quot; type=&quot;range&quot; min=&quot;0&quot; max=&quot;1000&quot; value=&quot;0&quot; step=&quot;25&quot; aria-describedby=&quot;area-value&quot;&gt;</span>
<span class="trajectory-added">+    &lt;/div&gt;</span>
<span class="trajectory-added">+  &lt;/div&gt;</span>
<span class="trajectory-added">+  &lt;div class=&quot;chart-wrap&quot;&gt;</span>
<span class="trajectory-added">+    &lt;svg id=&quot;taxi-zone-chart&quot; role=&quot;img&quot; aria-labelledby=&quot;taxi-chart-title taxi-chart-desc&quot; viewBox=&quot;0 0 740 390&quot;&gt;</span>
<span class="trajectory-added">+      &lt;desc id=&quot;taxi-chart-desc&quot;&gt;Bar chart showing the count of taxi zones by borough after applying a borough and minimum-area filter.&lt;/desc&gt;</span>
<span class="trajectory-added">+    &lt;/svg&gt;</span>
<span class="trajectory-added">+  &lt;/div&gt;</span>
<span class="trajectory-added">+  &lt;div id=&quot;taxi-status&quot; class=&quot;status tabular-nums&quot; aria-live=&quot;polite&quot;&gt;&lt;/div&gt;</span>
<span class="trajectory-added">+  &lt;script&gt;</span>
<span class="trajectory-added">+    (() =&gt; {</span>
<span class="trajectory-added">+      const root = document.getElementById(&#x27;taxi-zone-borough-counts&#x27;);</span>
<span class="trajectory-added">+      const scope = root.querySelector(&#x27;#borough-scope&#x27;);</span>
<span class="trajectory-added">+      const minArea = root.querySelector(&#x27;#min-area&#x27;);</span>
<span class="trajectory-added">+      const areaValue = root.querySelector(&#x27;#area-value&#x27;);</span>
<span class="trajectory-added">+      const svg = root.querySelector(&#x27;#taxi-zone-chart&#x27;);</span>
<span class="trajectory-added">+      const status = root.querySelector(&#x27;#taxi-status&#x27;);</span>
<span class="trajectory-added">+      const areas = {&quot;Bronx&quot;:[62.6,62.9,91.1,95.2,106.4,134.5,146,148.5,148.9,149.6,150.9,155.9,161.3,161.8,163.2,167.5,171.2,185.8,191.1,199.1,205,205.6,212.8,228.5,241,254.7,288.7,313,314.4,334,360,360.1,394.6,395.8,399.6,547.1,703.3,722.1,744.6,904.1,926.4,1988.8,2020.3],&quot;Brooklyn&quot;:[45.2,81.8,101.4,108.4,108.9,113.6,114.7,124.2,130.3,132.5,138.9,143.6,147.4,157.2,158.2,163.3,168.6,172.3,173.9,175.8,191.9,198.9,201.7,203.2,208.7,247.7,264.5,268.3,270.6,270.9,296.4,306.9,310.8,313,323,323.5,323.8,332.6,352.9,353.2,354,380.3,382.6,394.3,407.3,447.5,452.1,453.2,462.1,472.1,510.8,534,537.3,736.3,801.7,868.3,900.3,993.4,1266.6,1381.8,1789.7],&quot;EWR&quot;:[782.3],&quot;Manhattan&quot;:[6.3,11.9,32.5,34.3,37.1,37.5,38.9,39.7,40.9,41.5,47,47.5,47.9,55.3,55.6,56.1,57.3,58,60.7,65.8,67.2,69.7,71.9,72.2,73.1,74.3,74.6,75.7,76.4,76.7,91.4,93.1,94.3,94.7,96,98.5,102.9,106.2,107.9,111.1,111.9,114.2,116.2,116.5,122.3,128.8,143.1,146.6,149.4,151.1,163.2,166.9,173.2,184.8,185.6,204.7,207.4,216,240.6,255.3,260.4,263.9,273.5,281.3,295,359.7,368.6,379.7,438.4],&quot;Queens&quot;:[18,26.6,44.7,78.3,104.6,145.6,145.9,178.3,180.9,183.9,195.5,197.5,202.4,217.5,226.6,247.7,281.3,291.2,291.8,296.6,323.6,327.4,338.4,346.6,354.4,366.2,373.8,374.9,384.6,389.8,395.6,422.3,423.7,428.2,435.8,446.7,452.3,467.9,468.3,474,485.8,499.8,504.7,504.9,520.1,536.8,546.7,547.6,571.2,572.8,594.3,615.1,619.4,623.3,688.5,754.8,761.9,764.4,766.2,816.1,871.9,904.3,925.2,947.5,1025.3,1057.9,1340.9,2038.3,4866.3],&quot;Staten Island&quot;:[373.2,421.2,466.2,498,525.7,606.5,625.8,641.4,657.8,658.4,812,890.1,944.4,1052.1,1169.6,1210.2,1826.9,1944.7,2073.8,2195.6]};</span>
<span class="trajectory-added">+      const order = [&#x27;Bronx&#x27;,&#x27;Brooklyn&#x27;,&#x27;Manhattan&#x27;,&#x27;Queens&#x27;,&#x27;Staten Island&#x27;,&#x27;EWR&#x27;];</span>
<span class="trajectory-added">+      const ns = &#x27;http://www.w3.org/2000/svg&#x27;;</span>
<span class="trajectory-added">+      const el = (tag, attrs = {}, text = &#x27;&#x27;) =&gt; { const n = document.createElementNS(ns, tag); Object.entries(attrs).forEach(([k,v]) =&gt; n.setAttribute(k,v)); n.textContent = text; return n; };</span>
<span class="trajectory-added">+      function draw() {</span>
<span class="trajectory-added">+        const threshold = Number(minArea.value); areaValue.textContent = \`\${threshold} × 10⁻⁶ area units\`;</span>
<span class="trajectory-added">+        const rows = order.map(b =&gt; ({borough:b,count:(scope.value === &#x27;all&#x27; || scope.value === b) ? areas[b].filter(a =&gt; a &gt;= threshold).length : 0,visible:scope.value === &#x27;all&#x27; || scope.value === b}));</span>
<span class="trajectory-added">+        const max = Math.max(1, ...rows.map(x =&gt; x.count)); const W=740,H=390,L=64,R=24,T=40,B=76, pw=W-L-R, ph=H-T-B;</span>
<span class="trajectory-added">+        svg.replaceChildren();</span>
<span class="trajectory-added">+        [0,Math.ceil(max/2),max].filter((x,i,a)=&gt;a.indexOf(x)===i).forEach(t=&gt;{const y=T+ph-(t/max)*ph;svg.append(el(&#x27;line&#x27;,{class:&#x27;grid&#x27;,x1:L,x2:W-R,y1:y,y2:y}));svg.append(el(&#x27;text&#x27;,{class:&#x27;tick&#x27;,x:L-9,y:y+4,&#x27;text-anchor&#x27;:&#x27;end&#x27;},String(t)));});</span>
<span class="trajectory-added">+        svg.append(el(&#x27;line&#x27;,{class:&#x27;axis&#x27;,x1:L,x2:L,y1:T,y2:T+ph}));svg.append(el(&#x27;line&#x27;,{class:&#x27;axis&#x27;,x1:L,x2:W-R,y1:T+ph,y2:T+ph}));</span>
<span class="trajectory-added">+        svg.append(el(&#x27;text&#x27;,{class:&#x27;axis-title&#x27;,x:18,y:T+ph/2,transform:\`rotate(-90 18 \${T+ph/2})\`,&#x27;text-anchor&#x27;:&#x27;middle&#x27;},&#x27;Zone count&#x27;));</span>
<span class="trajectory-added">+        const slot=pw/rows.length,bw=Math.min(72,slot*.58);</span>
<span class="trajectory-added">+        rows.forEach((row,i)=&gt;{const x=L+i*slot+(slot-bw)/2,h=(row.count/max)*ph,y=T+ph-h;const bar=el(&#x27;rect&#x27;,{class:&#x27;bar&#x27;,x,y,width:bw,height:h,rx:2,tabindex:0,role:&#x27;img&#x27;,&#x27;aria-label&#x27;:\`\${row.borough}: \${row.count} zones\`,opacity:row.visible?1:.18});bar.setAttribute(&#x27;data-tooltip&#x27;,\`\${row.borough}: \${row.count} zones\`);svg.append(bar);if(row.visible)svg.append(el(&#x27;text&#x27;,{class:&#x27;bar-label&#x27;,x:x+bw/2,y:Math.max(T+14,y-8),&#x27;text-anchor&#x27;:&#x27;middle&#x27;},String(row.count)));svg.append(el(&#x27;text&#x27;,{class:&#x27;tick&#x27;,x:x+bw/2,y:T+ph+26,&#x27;text-anchor&#x27;:&#x27;middle&#x27;},row.borough));});</span>
<span class="trajectory-added">+        const total=rows.reduce((s,x)=&gt;s+x.count,0); status.textContent = \`\${total} matching taxi zone\${total===1?&#x27;&#x27;:&#x27;s&#x27;}.\`;</span>
<span class="trajectory-added">+      }</span>
<span class="trajectory-added">+      scope.addEventListener(&#x27;change&#x27;,draw); minArea.addEventListener(&#x27;input&#x27;,draw); draw();</span>
<span class="trajectory-added">+    })();</span>
<span class="trajectory-added">+  &lt;/script&gt;</span>
<span class="trajectory-added">+&lt;/div&gt;</span>
*** End Patch</code></pre>

</div>

</div>

</div>

</div>

Connected sources are read-only. When necessary, the agent can transform
tables in a local workspace and keep intermediate files in a temporary scratch
directory, so your source data and project directory remain unchanged by
default. You can ask the agent at any time to export results to local files in
any format you need for sharing or further use.

TabulaFlow also goes beyond existing AI database assistants (e.g., Chat2DB),
which typically focus on generating SQL for a single database. TabulaFlow
supports broader, general-purpose workflows across SQL and graph databases,
local files, public datasets, and the web.

## Build and research with TabulaFlow

### Build with the Python library

Create your own data agents and applications with an async-native library
written in pure Python. Reuse its connectors, tools, and structured outputs
to build workflows tailored to your needs.
[Explore the library](library/quick-start.md){ .inline-cta }

### Run research experiments

Run large-scale experiments on text-to-SQL and text-to-Cypher benchmarks such
as Spider 2.0, CypherBench, and ARCS with TabulaFlow's research toolkit.
[Explore the toolkit](research/quick-start.md){ .inline-cta }

!!! note "Public beta"
    TabulaFlow 0.4.1 is a public beta. Patch releases preserve documented
    public APIs; minor `0.x` releases may include documented breaking changes.
    We welcome your feedback.
