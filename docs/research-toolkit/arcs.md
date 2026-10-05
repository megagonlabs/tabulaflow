<div class="arcs-page" data-arcs-page>
  <header class="arcs-hero">
    <div class="arcs-hero__title">
      <div>
        <h1>ARCS</h1>
        <p>Towards Precise Text-to-SQL via Structured Disambiguation</p>
      </div>
    </div>
    <div class="arcs-hero__resources" aria-label="ARCS resources">
      <span class="arcs-resource" aria-disabled="true">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line></svg>
        Paper
      </span>
      <span class="arcs-resource" aria-disabled="true">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22"></path></svg>
        Code
      </span>
      <span class="arcs-resource" aria-disabled="true">
        <svg viewBox="0 0 24 24" aria-hidden="true"><ellipse cx="12" cy="5" rx="9" ry="3"></ellipse><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"></path><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"></path></svg>
        Dataset
      </span>
    </div>
  </header>
</div>

<div class="arcs-introduction" markdown="1">

## Introduction

As text-to-SQL systems move beyond demonstrations toward real-world deployment,
ambiguity in user questions becomes a primary source of errors. These ambiguities
are often subtle, domain- or data-specific, and can silently cause system outputs
to deviate from the user's true intent. **Structured disambiguation** resolves
ambiguity through explicit, constrained interactions rather than free-form
dialogue.

ARCS (**A**mbiguity **R**esolution **C**orpus for **S**QL) is a text-to-SQL
benchmark featuring naturally occurring, unconstrained ambiguities over
real-world databases, with complete annotations of valid ambiguity points,
interpretations, and SQL queries.

</div>

<div class="arcs-tabs" role="tablist" aria-label="Explore ARCS">
    <button id="arcs-tab-database" class="arcs-tab" type="button" role="tab" aria-controls="arcs-database" aria-selected="true"><svg viewBox="0 0 24 24" aria-hidden="true"><ellipse cx="12" cy="5" rx="9" ry="3"></ellipse><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"></path><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"></path></svg>Database</button>
    <button id="arcs-tab-sample-tasks" class="arcs-tab" type="button" role="tab" aria-controls="arcs-sample-tasks" aria-selected="false" tabindex="-1"><svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="2"></rect><line x1="3" y1="9" x2="21" y2="9"></line><line x1="9" y1="21" x2="9" y2="9"></line></svg>Sample Tasks</button>
    <button id="arcs-tab-leaderboard" class="arcs-tab" type="button" role="tab" aria-controls="arcs-leaderboard" aria-selected="false" tabindex="-1"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"></path><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"></path><path d="M4 22h16"></path><path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22"></path><path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22"></path><path d="M18 2H6v7a6 6 0 0 0 12 0V2Z"></path></svg>Leaderboard</button>
    <button id="arcs-tab-taxonomy" class="arcs-tab" type="button" role="tab" aria-controls="arcs-taxonomy" aria-selected="false" tabindex="-1"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>Taxonomy</button>
</div>

<div id="arcs-database" class="arcs-panel arcs-panel--flush" role="tabpanel" aria-labelledby="arcs-tab-database">
<div class="arcs-databases" data-arcs-databases data-source="../../assets/arcs/databases.json">
<div class="arcs-databases__status" data-database-status>Loading databases…</div>
<div class="arcs-databases__browser" data-database-browser hidden>
<div class="arcs-question-row">
<button class="arcs-task-nav" type="button" data-database-previous aria-label="Previous database">
<svg viewBox="0 0 24 24" aria-hidden="true"><polyline points="15 18 9 12 15 6"></polyline></svg>
</button>
<div class="arcs-database-card">
<svg class="arcs-database-card__icon" viewBox="0 0 24 24" aria-hidden="true"><ellipse cx="12" cy="5" rx="9" ry="3"></ellipse><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"></path><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"></path></svg>
<code data-database-name></code>
<span data-database-position></span>
</div>
<button class="arcs-task-nav" type="button" data-database-next aria-label="Next database">
<svg viewBox="0 0 24 24" aria-hidden="true"><polyline points="9 18 15 12 9 6"></polyline></svg>
</button>
</div>
<div class="arcs-schema-grid" data-database-schema></div>
</div>
</div>
</div>

<div id="arcs-sample-tasks" class="arcs-panel arcs-panel--flush" role="tabpanel" aria-labelledby="arcs-tab-sample-tasks" hidden>
<div class="arcs-samples" data-arcs-samples data-source="../../assets/arcs/sample-tasks.compact.json">
<div class="arcs-samples__status" data-sample-status>Loading sample tasks…</div>
<div class="arcs-samples__browser" data-sample-browser hidden>
<div class="arcs-question-row">
<button class="arcs-task-nav" type="button" data-task-previous aria-label="Previous sample task">
<svg viewBox="0 0 24 24" aria-hidden="true"><polyline points="15 18 9 12 15 6"></polyline></svg>
</button>
<div class="arcs-question-card">
<svg class="arcs-question-card__icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>
<p class="arcs-question" data-task-question></p>
<div class="arcs-task-meta">
<span data-task-position></span>
<span data-task-database></span>
</div>
</div>
<button class="arcs-task-nav" type="button" data-task-next aria-label="Next sample task">
<svg viewBox="0 0 24 24" aria-hidden="true"><polyline points="9 18 15 12 9 6"></polyline></svg>
</button>
</div>
<div class="arcs-ambiguity-controls" data-ambiguity-controls></div>
<div class="arcs-sample-output">
<section class="arcs-query-panel" aria-labelledby="arcs-sample-sql-heading">
<div class="arcs-sample-panel__header">
<h3 id="arcs-sample-sql-heading"><svg viewBox="0 0 24 24" aria-hidden="true"><polyline points="4 17 10 11 4 5"></polyline><line x1="12" y1="19" x2="20" y2="19"></line></svg>SQL</h3>
</div>
<pre class="arcs-sql"><code data-task-sql></code></pre>
</section>
<section class="arcs-results-panel" aria-labelledby="arcs-sample-results-heading">
<div class="arcs-sample-panel__header">
<h3 id="arcs-sample-results-heading"><svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="2"></rect><line x1="3" y1="9" x2="21" y2="9"></line><line x1="9" y1="21" x2="9" y2="9"></line></svg>Results</h3>
<span data-results-count></span>
</div>
<div class="arcs-results" data-task-results></div>
</section>
</div>
</div>
</div>

</div>

<div id="arcs-leaderboard" class="arcs-panel arcs-panel--flush" role="tabpanel" aria-labelledby="arcs-tab-leaderboard" hidden>
<section class="arcs-leaderboard" data-arcs-leaderboard>
<div class="arcs-leaderboard__scroller">
<table aria-describedby="arcs-leaderboard-note" class="arcs-leaderboard__table" data-arcs-leaderboard-table>
                        <caption>ARCS model performance leaderboard</caption>
                        <thead>
                            <tr>
                                <th class="arcs-leaderboard__rank-col">#</th>
                                <th class="arcs-leaderboard__method-col">Method</th>
                                <th class="arcs-leaderboard__score-col">Full Recall</th>
                                <th class="arcs-leaderboard__score-col">Perfect</th>
                                <th class="arcs-leaderboard__score-col">EX<sub>disamb</sub></th>
                                <th class="arcs-leaderboard__score-col">EX<sub>e2e</sub></th>
                                <th class="arcs-leaderboard__score-col">ΔEX</th>
                                <th class="arcs-leaderboard__score-col">Cost ($)</th>
                            </tr>
                            <tr class="arcs-leaderboard__groups">
                                <th></th>
                                <th></th>
                                <th colspan="2">Disambiguation Only</th>
                                <th>SQL Only</th>
                                <th colspan="3">End-to-end</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td class="arcs-leaderboard__rank"></td>
                                <td class="arcs-leaderboard__model"><code>gptoss-20b</code></td>
                                <td class="arcs-leaderboard__score">4.18</td>
                                <td class="arcs-leaderboard__score">0.96</td>
                                <td class="arcs-leaderboard__score">27.97</td>
                                <td class="arcs-leaderboard__score">7.40</td>
                                <td class="arcs-leaderboard__score arcs-leaderboard__negative">-20.57</td>
                                <td class="arcs-leaderboard__score arcs-leaderboard__cost">0.0003</td>
                            </tr>
                            <tr>
                                <td class="arcs-leaderboard__rank"></td>
                                <td class="arcs-leaderboard__model"><code>gptoss-120b</code></td>
                                <td class="arcs-leaderboard__score">16.72</td>
                                <td class="arcs-leaderboard__score">1.61</td>
                                <td class="arcs-leaderboard__score">52.09</td>
                                <td class="arcs-leaderboard__score">26.05</td>
                                <td class="arcs-leaderboard__score arcs-leaderboard__negative">-26.04</td>
                                <td class="arcs-leaderboard__score arcs-leaderboard__cost">0.003</td>
                            </tr>
                            <tr>
                                <td class="arcs-leaderboard__rank"></td>
                                <td class="arcs-leaderboard__model"><code>qwen3-8b</code></td>
                                <td class="arcs-leaderboard__score">6.11</td>
                                <td class="arcs-leaderboard__score">0.00</td>
                                <td class="arcs-leaderboard__score">11.25</td>
                                <td class="arcs-leaderboard__score">5.79</td>
                                <td class="arcs-leaderboard__score arcs-leaderboard__negative">-5.46</td>
                                <td class="arcs-leaderboard__score arcs-leaderboard__cost">0.009</td>
                            </tr>
                            <tr>
                                <td class="arcs-leaderboard__rank"></td>
                                <td class="arcs-leaderboard__model"><code>qwen3-235b-a22b-instruct-2507</code></td>
                                <td class="arcs-leaderboard__score">6.43</td>
                                <td class="arcs-leaderboard__score">2.57</td>
                                <td class="arcs-leaderboard__score">37.30</td>
                                <td class="arcs-leaderboard__score">20.26</td>
                                <td class="arcs-leaderboard__score arcs-leaderboard__negative">-17.04</td>
                                <td class="arcs-leaderboard__score arcs-leaderboard__cost">0.02</td>
                            </tr>
                            <tr>
                                <td class="arcs-leaderboard__rank"></td>
                                <td class="arcs-leaderboard__model"><code>qwen3-coder-480b</code></td>
                                <td class="arcs-leaderboard__score">6.11</td>
                                <td class="arcs-leaderboard__score">2.57</td>
                                <td class="arcs-leaderboard__score">26.69</td>
                                <td class="arcs-leaderboard__score">15.76</td>
                                <td class="arcs-leaderboard__score arcs-leaderboard__negative">-10.93</td>
                                <td class="arcs-leaderboard__score arcs-leaderboard__cost">0.03</td>
                            </tr>
                            <tr>
                                <td class="arcs-leaderboard__rank"></td>
                                <td class="arcs-leaderboard__model"><code>deepseek-v3.1</code></td>
                                <td class="arcs-leaderboard__score">14.47</td>
                                <td class="arcs-leaderboard__score">1.93</td>
                                <td class="arcs-leaderboard__score">49.52</td>
                                <td class="arcs-leaderboard__score">23.47</td>
                                <td class="arcs-leaderboard__score arcs-leaderboard__negative">-26.05</td>
                                <td class="arcs-leaderboard__score arcs-leaderboard__cost">0.01</td>
                            </tr>
                            <tr>
                                <td class="arcs-leaderboard__rank"></td>
                                <td class="arcs-leaderboard__model"><code>deepseek-r1-0528</code></td>
                                <td class="arcs-leaderboard__score">10.93</td>
                                <td class="arcs-leaderboard__score">3.22</td>
                                <td class="arcs-leaderboard__score">38.26</td>
                                <td class="arcs-leaderboard__score">23.15</td>
                                <td class="arcs-leaderboard__score arcs-leaderboard__negative">-15.11</td>
                                <td class="arcs-leaderboard__score arcs-leaderboard__cost">0.04</td>
                            </tr>
                            <tr>
                                <td class="arcs-leaderboard__rank"></td>
                                <td class="arcs-leaderboard__model"><code>kimi-k2-thinking</code></td>
                                <td class="arcs-leaderboard__score">9.97</td>
                                <td class="arcs-leaderboard__score">0.96</td>
                                <td class="arcs-leaderboard__score">43.41</td>
                                <td class="arcs-leaderboard__score">19.29</td>
                                <td class="arcs-leaderboard__score arcs-leaderboard__negative">-24.12</td>
                                <td class="arcs-leaderboard__score arcs-leaderboard__cost">0.03</td>
                            </tr>
                            <tr>
                                <td class="arcs-leaderboard__rank"></td>
                                <td class="arcs-leaderboard__model"><code>gemini-2.5-flash</code></td>
                                <td class="arcs-leaderboard__score">17.04</td>
                                <td class="arcs-leaderboard__score arcs-leaderboard__second-best">10.61</td>
                                <td class="arcs-leaderboard__score">42.44</td>
                                <td class="arcs-leaderboard__score">27.65</td>
                                <td class="arcs-leaderboard__score arcs-leaderboard__negative">-14.79</td>
                                <td class="arcs-leaderboard__score arcs-leaderboard__cost">0.01</td>
                            </tr>
                            <tr>
                                <td class="arcs-leaderboard__rank"></td>
                                <td class="arcs-leaderboard__model"><code>gemini-2.5-pro</code></td>
                                <td class="arcs-leaderboard__score">20.90</td>
                                <td class="arcs-leaderboard__score">9.65</td>
                                <td class="arcs-leaderboard__score">50.80</td>
                                <td class="arcs-leaderboard__score">30.87</td>
                                <td class="arcs-leaderboard__score arcs-leaderboard__negative">-19.93</td>
                                <td class="arcs-leaderboard__score arcs-leaderboard__cost">0.06</td>
                            </tr>
                            <tr>
                                <td class="arcs-leaderboard__rank"></td>
                                <td class="arcs-leaderboard__model"><code>gemini-3-pro</code> <span class="arcs-leaderboard__config">(high*)</span></td>
                                <td class="arcs-leaderboard__score">26.37</td>
                                <td class="arcs-leaderboard__score arcs-leaderboard__best">13.83</td>
                                <td class="arcs-leaderboard__score">65.27</td>
                                <td class="arcs-leaderboard__score">44.05</td>
                                <td class="arcs-leaderboard__score arcs-leaderboard__negative">-21.22</td>
                                <td class="arcs-leaderboard__score arcs-leaderboard__cost">0.14</td>
                            </tr>
                            <tr>
                                <td class="arcs-leaderboard__rank"></td>
                                <td class="arcs-leaderboard__model"><code>claude-haiku-4.5</code> <span class="arcs-leaderboard__config">(high*)</span></td>
                                <td class="arcs-leaderboard__score">17.68</td>
                                <td class="arcs-leaderboard__score">8.04</td>
                                <td class="arcs-leaderboard__score">49.84</td>
                                <td class="arcs-leaderboard__score">28.62</td>
                                <td class="arcs-leaderboard__score arcs-leaderboard__negative">-21.22</td>
                                <td class="arcs-leaderboard__score arcs-leaderboard__cost">0.03</td>
                            </tr>
                            <tr>
                                <td class="arcs-leaderboard__rank"></td>
                                <td class="arcs-leaderboard__model"><code>claude-sonnet-4.5</code> <span class="arcs-leaderboard__config">(high*)</span></td>
                                <td class="arcs-leaderboard__score">23.47</td>
                                <td class="arcs-leaderboard__score">7.40</td>
                                <td class="arcs-leaderboard__score">57.88</td>
                                <td class="arcs-leaderboard__score">43.73</td>
                                <td class="arcs-leaderboard__score arcs-leaderboard__negative">-14.15</td>
                                <td class="arcs-leaderboard__score arcs-leaderboard__cost">0.09</td>
                            </tr>
                            <tr>
                                <td class="arcs-leaderboard__rank"></td>
                                <td class="arcs-leaderboard__model"><code>claude-opus-4.5</code> <span class="arcs-leaderboard__config">(high*)</span></td>
                                <td class="arcs-leaderboard__score">22.51</td>
                                <td class="arcs-leaderboard__score">8.04</td>
                                <td class="arcs-leaderboard__score arcs-leaderboard__second-best">67.85</td>
                                <td class="arcs-leaderboard__score">38.59</td>
                                <td class="arcs-leaderboard__score arcs-leaderboard__negative">-29.26</td>
                                <td class="arcs-leaderboard__score arcs-leaderboard__cost">0.15</td>
                            </tr>
                            <tr>
                                <td class="arcs-leaderboard__rank"></td>
                                <td class="arcs-leaderboard__model"><code>gpt-4.1-nano</code></td>
                                <td class="arcs-leaderboard__score">2.25</td>
                                <td class="arcs-leaderboard__score">0.64</td>
                                <td class="arcs-leaderboard__score">10.29</td>
                                <td class="arcs-leaderboard__score">7.07</td>
                                <td class="arcs-leaderboard__score arcs-leaderboard__negative">-3.22</td>
                                <td class="arcs-leaderboard__score arcs-leaderboard__cost">0.006</td>
                            </tr>
                            <tr>
                                <td class="arcs-leaderboard__rank"></td>
                                <td class="arcs-leaderboard__model"><code>gpt-4.1-mini</code></td>
                                <td class="arcs-leaderboard__score">10.61</td>
                                <td class="arcs-leaderboard__score">4.18</td>
                                <td class="arcs-leaderboard__score">45.34</td>
                                <td class="arcs-leaderboard__score">21.86</td>
                                <td class="arcs-leaderboard__score arcs-leaderboard__negative">-23.48</td>
                                <td class="arcs-leaderboard__score arcs-leaderboard__cost">0.007</td>
                            </tr>
                            <tr>
                                <td class="arcs-leaderboard__rank"></td>
                                <td class="arcs-leaderboard__model"><code>gpt-4.1</code></td>
                                <td class="arcs-leaderboard__score">14.47</td>
                                <td class="arcs-leaderboard__score">7.40</td>
                                <td class="arcs-leaderboard__score">56.27</td>
                                <td class="arcs-leaderboard__score">29.90</td>
                                <td class="arcs-leaderboard__score arcs-leaderboard__negative">-26.37</td>
                                <td class="arcs-leaderboard__score arcs-leaderboard__cost">0.03</td>
                            </tr>
                            <tr>
                                <td class="arcs-leaderboard__rank"></td>
                                <td class="arcs-leaderboard__model"><code>o4-mini</code> <span class="arcs-leaderboard__config">(low)</span></td>
                                <td class="arcs-leaderboard__score">22.83</td>
                                <td class="arcs-leaderboard__score">8.36</td>
                                <td class="arcs-leaderboard__score">56.27</td>
                                <td class="arcs-leaderboard__score">36.01</td>
                                <td class="arcs-leaderboard__score arcs-leaderboard__negative">-20.26</td>
                                <td class="arcs-leaderboard__score arcs-leaderboard__cost">0.02</td>
                            </tr>
                            <tr>
                                <td class="arcs-leaderboard__rank"></td>
                                <td class="arcs-leaderboard__model"><code>o4-mini</code> <span class="arcs-leaderboard__config">(medium*)</span></td>
                                <td class="arcs-leaderboard__score">30.55</td>
                                <td class="arcs-leaderboard__score">6.43</td>
                                <td class="arcs-leaderboard__score">62.06</td>
                                <td class="arcs-leaderboard__score">42.44</td>
                                <td class="arcs-leaderboard__score arcs-leaderboard__negative">-19.62</td>
                                <td class="arcs-leaderboard__score arcs-leaderboard__cost">0.03</td>
                            </tr>
                            <tr>
                                <td class="arcs-leaderboard__rank"></td>
                                <td class="arcs-leaderboard__model"><code>o4-mini</code> <span class="arcs-leaderboard__config">(high)</span></td>
                                <td class="arcs-leaderboard__score">27.97</td>
                                <td class="arcs-leaderboard__score">6.43</td>
                                <td class="arcs-leaderboard__score">64.95</td>
                                <td class="arcs-leaderboard__score">44.05</td>
                                <td class="arcs-leaderboard__score arcs-leaderboard__negative">-20.90</td>
                                <td class="arcs-leaderboard__score arcs-leaderboard__cost">0.06</td>
                            </tr>
                            <tr>
                                <td class="arcs-leaderboard__rank"></td>
                                <td class="arcs-leaderboard__model"><code>gpt-5-nano</code> <span class="arcs-leaderboard__config">(medium*)</span></td>
                                <td class="arcs-leaderboard__score">16.08</td>
                                <td class="arcs-leaderboard__score">4.82</td>
                                <td class="arcs-leaderboard__score">50.16</td>
                                <td class="arcs-leaderboard__score">29.26</td>
                                <td class="arcs-leaderboard__score arcs-leaderboard__negative">-20.90</td>
                                <td class="arcs-leaderboard__score arcs-leaderboard__cost">0.005</td>
                            </tr>
                            <tr>
                                <td class="arcs-leaderboard__rank"></td>
                                <td class="arcs-leaderboard__model"><code>gpt-5-mini</code> <span class="arcs-leaderboard__config">(medium*)</span></td>
                                <td class="arcs-leaderboard__score">42.12</td>
                                <td class="arcs-leaderboard__score">0.00</td>
                                <td class="arcs-leaderboard__score">63.02</td>
                                <td class="arcs-leaderboard__score">44.37</td>
                                <td class="arcs-leaderboard__score arcs-leaderboard__negative">-18.65</td>
                                <td class="arcs-leaderboard__score arcs-leaderboard__cost">0.01</td>
                            </tr>
                            <tr>
                                <td class="arcs-leaderboard__rank"></td>
                                <td class="arcs-leaderboard__model"><code>gpt-5</code> <span class="arcs-leaderboard__config">(minimal)</span></td>
                                <td class="arcs-leaderboard__score">30.23</td>
                                <td class="arcs-leaderboard__score">0.32</td>
                                <td class="arcs-leaderboard__score">56.27</td>
                                <td class="arcs-leaderboard__score">37.62</td>
                                <td class="arcs-leaderboard__score arcs-leaderboard__negative">-18.65</td>
                                <td class="arcs-leaderboard__score arcs-leaderboard__cost">0.02</td>
                            </tr>
                            <tr>
                                <td class="arcs-leaderboard__rank"></td>
                                <td class="arcs-leaderboard__model"><code>gpt-5</code> <span class="arcs-leaderboard__config">(low)</span></td>
                                <td class="arcs-leaderboard__score">52.41</td>
                                <td class="arcs-leaderboard__score">0.96</td>
                                <td class="arcs-leaderboard__score">65.59</td>
                                <td class="arcs-leaderboard__score">48.55</td>
                                <td class="arcs-leaderboard__score arcs-leaderboard__negative">-17.04</td>
                                <td class="arcs-leaderboard__score arcs-leaderboard__cost">0.04</td>
                            </tr>
                            <tr>
                                <td class="arcs-leaderboard__rank"></td>
                                <td class="arcs-leaderboard__model"><code>gpt-5</code> <span class="arcs-leaderboard__config">(medium*)</span></td>
                                <td class="arcs-leaderboard__score arcs-leaderboard__second-best">59.16</td>
                                <td class="arcs-leaderboard__score">0.00</td>
                                <td class="arcs-leaderboard__score">67.52</td>
                                <td class="arcs-leaderboard__score arcs-leaderboard__best">57.88</td>
                                <td class="arcs-leaderboard__score arcs-leaderboard__negative">-9.64</td>
                                <td class="arcs-leaderboard__score arcs-leaderboard__cost">0.09</td>
                            </tr>
                            <tr>
                                <td class="arcs-leaderboard__rank"></td>
                                <td class="arcs-leaderboard__model"><code>gpt-5</code> <span class="arcs-leaderboard__config">(high)</span></td>
                                <td class="arcs-leaderboard__score arcs-leaderboard__best">61.09</td>
                                <td class="arcs-leaderboard__score">0.00</td>
                                <td class="arcs-leaderboard__score arcs-leaderboard__best">68.81</td>
                                <td class="arcs-leaderboard__score arcs-leaderboard__second-best">57.56</td>
                                <td class="arcs-leaderboard__score arcs-leaderboard__negative">-11.25</td>
                                <td class="arcs-leaderboard__score arcs-leaderboard__cost">0.16</td>
                            </tr>
                        </tbody>
                    </table>
</div>
<p id="arcs-leaderboard-note" class="arcs-leaderboard__footnote">* indicates the default reasoning effort</p>
</section>
</div>

<div id="arcs-taxonomy" class="arcs-panel arcs-panel--flush" role="tabpanel" aria-labelledby="arcs-tab-taxonomy" hidden>
<section class="arcs-taxonomy">
<div class="arcs-taxonomy__description">
<h2>Ambiguity in Text-to-SQL</h2>
<p>A key challenge in characterizing ambiguity in text-to-SQL is that it is inherently intersectional: it arises from the friction between natural language and a specific database schema. We address this intersectional nature with two orthogonal dimensions: a <strong><em>linguistic dimension</em></strong>, which captures the linguistic source of the ambiguity, and a <strong><em>database dimension</em></strong>, which captures how the ambiguity maps to database elements.</p>
</div>
<figure class="arcs-taxonomy__figure">
<a href="../../assets/arcs/taxonomy.png" target="_blank" rel="noopener" aria-label="Open the ARCS taxonomy diagram at full size">
<img src="../../assets/arcs/taxonomy.png" width="3747" height="1831" loading="lazy" alt="ARCS taxonomy diagram organizing text-to-SQL ambiguity by linguistic source and database element mapping">
</a>
</figure>
</section>
</div>
