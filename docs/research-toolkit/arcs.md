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
    <button id="arcs-tab-taxonomy" class="arcs-tab" type="button" role="tab" aria-controls="arcs-taxonomy" aria-selected="false" tabindex="-1"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1 4-10 15.3 15.3 0 0 1 4-10z"></path></svg>Taxonomy</button>
</div>

<div id="arcs-database" class="arcs-panel" role="tabpanel" aria-labelledby="arcs-tab-database" markdown="1">

## Database

Explore the schemas of the real-world databases included in ARCS. The
interactive database browser will appear here.

</div>

<div id="arcs-sample-tasks" class="arcs-panel" role="tabpanel" aria-labelledby="arcs-tab-sample-tasks" hidden markdown="1">

## Sample Tasks

Explore ambiguous questions, choose interpretations, and inspect the resulting
SQL and execution results. The interactive task browser will appear here.

</div>

<div id="arcs-leaderboard" class="arcs-panel" role="tabpanel" aria-labelledby="arcs-tab-leaderboard" hidden markdown="1">

## Leaderboard

Compare ambiguity resolution and end-to-end execution performance. The ARCS
leaderboard will appear here.

</div>

<div id="arcs-taxonomy" class="arcs-panel" role="tabpanel" aria-labelledby="arcs-tab-taxonomy" hidden markdown="1">

## Taxonomy

Explore the ambiguity types represented in ARCS. The taxonomy browser will
appear here.

</div>
