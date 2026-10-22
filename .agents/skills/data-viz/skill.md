  ---
  name: data-visualization
  description: Create effective, responsive, accessible, production-ready data visualizations with Chart.js (JavaScript/TypeScript). Use when choosing chart types, building or improving dashboards, styling Chart.js charts, optimizing performance, or implementing interactive charts.
  user-invocable: false
  ---

  # Data Visualization Skill — Chart.js

  Build effective charts using \*\*Chart.js 4.x\*\* and the official documentation as the source of truth: https://www.chartjs.org/docs/latest/ . Prefer Chart.js for visual output; do not generate matplotlib, seaborn, or Plotly implementations unless the user specifically requests them.

  ## Core workflow

  1. Determine the question the chart must answer, input shape, units, and audience.
  2. Select the simplest chart that accurately represents the relationship. Check whether it is supported natively by Chart.js.
  3. Inspect the project's existing Chart.js version, framework, chart wrappers, plugins, design tokens, and conventions. Reuse them; never introduce a second chart library without justification.
  4. Prepare the data: validate numeric values, sort intentionally, handle nulls, label units, and avoid misleading truncation or interpolation.
  5. Produce a responsive, accessible chart with descriptive labels, clear tooltips, appropriate tick formatting, and a useful empty state.
  6. Test small/large datasets, missing values, mobile widths, dark mode, and framework component teardown.
  7. When uncertain about API details, verify against https://www.chartjs.org/docs/latest/ rather than guessing.

  ## Chart selection guide

  | Relationship | Recommended visualization | Chart.js implementation / caveat |
  |---|---|---|
  | Trend over time | Line | \`type: 'line'\`; use \`time\` scale + date adapter for real timestamps |
  | Category comparison | Bar | \`type: 'bar'\` |
  | Ranking / long names | Horizontal bar | \`type: 'bar'\`, \`indexAxis: 'y'\`; sort explicitly |
  | Part-to-whole | Stacked bars | \`scales.x.stacked\` and \`scales.y.stacked\` |
  | Composition over time | Stacked area | Filled, stacked line datasets; confirm that semantics suit data |
  | Distribution | Histogram | Bin data first; display counts using \`type: 'bar'\` |
  | Correlation | Scatter | \`type: 'scatter'\`, \`{x, y}\` points |
  | Three numeric dimensions | Bubble | \`type: 'bubble'\`, \`{x, y, r}\` points; document radius meaning |
  | Small number of proportions | Doughnut or pie | \`type: 'doughnut'\` / \`pie\`; often prefer bars |
  | Metrics with different units | Separate panels | Dual axes only if essential, with explicit axis labels |
  | Many series / segments | Small multiples | Multiple Chart instances with consistent domain and styling |
  | Performance vs. target | Bar + target annotation | Annotation needs a separately installed plugin or a custom plugin |
  | Correlation matrix | Heatmap | Not built in; use a suitable plugin/custom visualization, or another tool by agreement |
  | Geographic / Sankey / network | Specialized visualization | Not built into core Chart.js; do not pretend they are supported |

  ### Avoid misleading visualization choices

  - Avoid 3D charts, unnecessary pie/doughnut charts, and excessive decoration.
  - For bar charts, ordinarily start the quantitative axis at zero.
  - Do not smooth lines in ways that introduce false patterns; default \`tension: 0\`.
  - Do not imply chronological spacing with a category axis if intervals are unequal; use a true time scale.
  - Avoid too many colors, unlabelled units, stacked charts with many series, and dual-axis comparisons without a compelling reason.
  - Use colorblind-conscious palettes and reinforce color differences with labels, line dashes, or point styles.

  ## Setup and reusable defaults

  Install with the project's package manager (example: \`npm install chart.js\`). For a bundled application, \`chart.js/auto\` registers the built-in components automatically. Use named imports and \`Chart.register(...)\` when bundle-size optimization matters.

  \`\`\`js
  import Chart from 'chart.js/auto';

  const COLORS = {
    primary: '#2563EB',
    teal: '#0D9488',
    orange: '#EA580C',
    purple: '#7C3AED',
    text: '#334155',
    grid: 'rgba(100,116,139,0.18)',
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: 'index', intersect: false },
    plugins: {
      legend: { position: 'top', labels: { usePointStyle: true } },
      tooltip: { enabled: true },
    },
    scales: {
      x: { grid: { display: false }, ticks: { color: COLORS.text, maxRotation: 0 } },
      y: { grid: { color: COLORS.grid }, ticks: { color: COLORS.text } },
    },
  };
  \`\`\`

  Make each canvas's \*\*dedicated parent element\*\* relatively positioned with an explicit height; do not attempt to size responsive charts through percentage \`canvas\` width/height attributes.

  \`\`\`html
  &lt;div style="position:relative;width:100%;height:320px"&gt;
    &lt;canvas id="myChart" role="img" aria-label="Revenue by month, January to June"&gt;&lt;/canvas&gt;
  &lt;/div&gt;
  \`\`\`

  The provided examples assume \`Chart\`, \`COLORS\`, and \`chartOptions\` are available. Use separate canvas elements/IDs for separate charts. In component frameworks, create a chart after the canvas mounts and call \`chart.destroy()\` when it unmounts. To update existing instances, change \`chart.data\` or \`chart.options\` and call \`chart.update()\` rather than creating duplicate instances.

  ## Chart.js code patterns

  ### Line chart — time series

  For equally spaced categorical months, labels are sufficient:

  \`\`\`js
  const chart = new Chart(document.getElementById('myChart'), {
    type: 'line',
    data: {
      labels: \['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'\],
      datasets: \[{
        label: 'Sessions',
        data: \[120, 148, 139, 165, 183, 201\],
        borderColor: COLORS.primary,
        backgroundColor: COLORS.primary,
        borderWidth: 2,
        pointRadius: 2,
        pointHoverRadius: 5,
        tension: 0,
        spanGaps: false,
      }\],
    },
    options: {
      ...chartOptions,
      scales: {
        ...chartOptions.scales,
        y: { ...chartOptions.scales.y, beginAtZero: true, title: { display: true, text: 'Sessions' } },
      },
    },
  });
  \`\`\`

  For \*\*real timestamps and unequal time intervals\*\*, install and import a compatible date adapter (e.g. \`chartjs-adapter-date-fns\` with \`date-fns\`), then provide \`{x: timestamp, y: value}\` data and \`scales.x.type: 'time'\`. A Chart.js time axis \*\*requires an adapter\*\*; it is not bundled automatically.

  ### Ranked horizontal bar chart

  \`\`\`js
  const items = \[
    { name: 'North', value: 74 },
    { name: 'South', value: 56 },
    { name: 'West', value: 92 },
  \].sort((a, b) =&gt; b.value - a.value);

  new Chart(document.getElementById('myChart'), {
    type: 'bar',
    data: {
      labels: items.map(d =&gt; d.name),
      datasets: \[{ label: 'Score', data: items.map(d =&gt; d.value), backgroundColor: COLORS.teal, borderRadius: 5 }\],
    },
    options: {
      ...chartOptions,
      indexAxis: 'y',
      plugins: { ...chartOptions.plugins, legend: { display: false } },
      scales: {
        x: { ...chartOptions.scales.x, beginAtZero: true, title: { display: true, text: 'Score' } },
        y: { ...chartOptions.scales.y, grid: { display: false } },
      },
    },
  });
  \`\`\`

  ### Histogram — pre-bin raw observations

  Core Chart.js does not have a separate histogram controller. Compute consistent bin boundaries and counts before rendering with a bar chart.

  \`\`\`js
  const values = \[12, 15, 16, 21, 22, 23, 26, 29, 31, 33\];
  const binWidth = 10;
  const lower = Math.floor(Math.min(...values) / binWidth) \* binWidth;
  const upper = (Math.floor(Math.max(...values) / binWidth) + 1) \* binWidth;
  const edges = Array.from({ length: (upper - lower) / binWidth + 1 }, (\_, i) =&gt; lower + i \* binWidth);
  const counts = edges.slice(0, -1).map((edge, i) =&gt;
    values.filter(v =&gt; v &gt;= edge &amp;&amp; (i === edges.length - 2 ? v &lt;= edges\[i + 1\] : v &lt; edges\[i + 1\])).length
  );

  new Chart(document.getElementById('myChart'), {
    type: 'bar',
    data: {
      labels: edges.slice(0, -1).map((edge, i) =&gt; \`${edge}–${edges\[i + 1\]}\`),
      datasets: \[{ label: 'Frequency', data: counts, backgroundColor: COLORS.primary, barPercentage: 1, categoryPercentage: 1 }\],
    },
    options: {
      ...chartOptions,
      plugins: { ...chartOptions.plugins, legend: { display: false } },
      scales: { ...chartOptions.scales, y: { ...chartOptions.scales.y, beginAtZero: true, ticks: { precision: 0 } } },
    },
  });
  \`\`\`

  For large arrays, use a linear-time binning algorithm instead of filtering for each bin. Explain if the final interval is inclusive.

  ### Scatter chart — numeric relationship

  \`\`\`js
  new Chart(document.getElementById('myChart'), {
    type: 'scatter',
    data: {
      datasets: \[{
        label: 'Temperature vs. pace',
        data: \[{ x: 18, y: 270 }, { x: 22, y: 282 }, { x: 28, y: 305 }\],
        backgroundColor: COLORS.purple,
        pointRadius: 5,
      }\],
    },
    options: {
      ...chartOptions,
      interaction: { mode: 'nearest', intersect: true },
      scales: {
        x: { ...chartOptions.scales.x, type: 'linear', title: { display: true, text: 'Temperature (°C)' } },
        y: { ...chartOptions.scales.y, title: { display: true, text: 'Pace (seconds/km)' } },
      },
    },
  });
  \`\`\`

  ### Stacked bar chart — composition

  \`\`\`js
  new Chart(document.getElementById('myChart'), {
    type: 'bar',
    data: {
      labels: \['Q1', 'Q2', 'Q3'\],
      datasets: \[
        { label: 'Organic', data: \[35, 42, 50\], backgroundColor: COLORS.primary },
        { label: 'Paid', data: \[22, 27, 30\], backgroundColor: COLORS.orange },
      \],
    },
    options: {
      ...chartOptions,
      scales: {
        x: { ...chartOptions.scales.x, stacked: true },
        y: { ...chartOptions.scales.y, stacked: true, beginAtZero: true },
      },
    },
  });
  \`\`\`

  For a 100% stacked chart, normalize each period to percentages \*\*before\*\* charting and label the axis as percent.

  ### Small multiples — coordinated panels

  Create one chart per category in its own canvas, use one shared min/max domain, and keep axes and colors consistent. Avoid repeating legends that do not add meaning.

  \`\`\`js
  const panels = \[
    { canvas: 'chartA', title: 'Group A', values: \[3, 5, 4\] },
    { canvas: 'chartB', title: 'Group B', values: \[2, 6, 7\] },
  \];
  const max = Math.max(...panels.flatMap(p =&gt; p.values));
  const charts = panels.map(p =&gt; new Chart(document.getElementById(p.canvas), {
    type: 'line',
    data: { labels: \['Jan', 'Feb', 'Mar'\], datasets: \[{ label: p.title, data: p.values, borderColor: COLORS.primary }\] },
    options: {
      ...chartOptions,
      plugins: { ...chartOptions.plugins, legend: { display: false }, title: { display: true, text: p.title } },
      scales: { ...chartOptions.scales, y: { ...chartOptions.scales.y, min: 0, max } },
    },
  }));
  // Call charts.forEach(chart =&gt; chart.destroy()) on teardown.
  \`\`\`

  ## Number and tooltip formatting

  Prefer \`Intl.NumberFormat\` instead of custom numeric suffix logic. Keep units and precision consistent across tooltips and axes.

  \`\`\`js
  const numberFormat = new Intl.NumberFormat('en-US', { maximumFractionDigits: 1 });
  const currencyFormat = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 });

  const formattingOptions = {
    scales: {
      y: { ticks: { callback: value =&gt; numberFormat.format(value) } },
    },
    plugins: {
      tooltip: {
        callbacks: {
          label: context =&gt; \`${context.dataset.label}: ${currencyFormat.format(context.parsed.y)}\`,
        },
      },
    },
  };
  \`\`\`

  Use \`context.parsed.x\` for a horizontal bar's numeric value; \`context.parsed.y\` is appropriate for the vertical series example above. Adapt formatting for percentages, distance, time, pace, and the project's locale.

  ## Interaction and data updates

  - Enable hover tooltips where they assist understanding, not as the sole source of essential information.
  - Use \`options.interaction.mode\` and \`intersect\` deliberately (\`index\` is useful for multi-series time trends; \`nearest\` for scatter).
  - Preserve keyboard-accessible controls outside the canvas when the user needs toggles, filters, or navigation.
  - Update \`chart.data.datasets\[0\].data\` and call \`chart.update()\`; call \`chart.destroy()\` before discarding its canvas.
  - For custom data labels, annotations, or zoom, install an appropriate plugin and check version compatibility. Do not use a nonexistent built-in option.

  ## Performance

  - Prefer fewer visible points and series when the task allows it.
  - For dense line datasets, investigate Chart.js's \*\*decimation\*\* plugin (\`min-max\` or \`lttb\`), after checking its prerequisites; do not assume it applies to every dataset or chart type.
  - For data already parsed into sorted \`{x, y}\` points in the scale's internal format, consider \`parsing: false\` and \`normalized: true\` when their preconditions are met.
  - Turn off animations (\`animation: false\`) for frequent real-time updates or very large datasets.
  - Use point radius \`0\` for dense line series; rely on hover interaction when appropriate.
  - Avoid recreating Chart objects on each state update in React/Vue/Svelte.
  - Consider tree-shaken named imports rather than \`chart.js/auto\` when minimizing bundle size.

  ## Accessibility and responsive design

  - Add \`role="img"\` and a meaningful \`aria-label\` or fallback text to each \`&lt;canvas&gt;\`. Canvas contents alone are not screen-reader accessible.
  - For important quantitative values, add adjacent HTML text or a data table.
  - Use a dedicated, \`position: relative\` parent container, with a set height and \`maintainAspectRatio: false\`.
  - Check legibility on mobile: fewer x-ticks, short labels, horizontal bars for longer category names, and readable tooltips.
  - Ensure good contrast in both dark and light themes; don't rely only on red vs. green.
  - For dashboards with multiple charts, ensure shared scale ranges when comparisons depend on them.
  - Use text labels and meaningful ordering, not just colors, to communicate meaning.

  ## Code review checklist

  - Does the chart answer a clear analytical question and use the right chart type?
  - Are units, time intervals, sorting, missing values, and baselines correct?
  - Is the API compatible with the installed Chart.js version?
  - If \`time\` is used, is a compatible date adapter installed and imported?
  - Are plugins explicitly installed and registered where required?
  - Is the chart responsive and the canvas accessible?
  - Are tooltips, legends, and labels genuinely useful?
  - Does the chart work with zero rows, one row, nulls, large numbers, and dense datasets?
  - Are charts updated/destroyed correctly to avoid memory leaks?
  - Has misleading smoothing, clipping, 3D, and gratuitous dual axes been avoided?


  ## Design Principles
  ## Accessibility Considerations

  ### Color Blindness

  - Never rely on color alone to distinguish data series
  - Add pattern fills, different line styles (solid, dashed, dotted), or direct labels
  - Test with a colorblind simulator (e.g., Coblis, Sim Daltonism)
  - Use the colorblind-friendly palette.

  ### Screen Readers

  - Include alt text describing the chart's key finding
  - Provide a data table alternative alongside the visualization
  - Use semantic titles and labels

  ### General Accessibility

  - Sufficient contrast between data elements and background
  - Text size minimum 10pt for labels, 12pt for titles
  - Avoid conveying information only through spatial position (add labels)
  - Consider printing: does the chart work in black and white?

  ### Accessibility Checklist

  Before sharing a visualization:
  - \[ \] Chart works without color (patterns, labels, or line styles differentiate series)
  - \[ \] Text is readable at standard zoom level
  - \[ \] Title describes the insight, not just the data
  - \[ \] Axes are labeled with units
  - \[ \] Legend is clear and positioned without obscuring data
  - \[ \] Data source and date range are noted

  ## Design Principles

  ## Accessibility Considerations

  ### Color Blindness

  - Never rely on color alone to distinguish data series

  - Add pattern fills, different line styles (solid, dashed, dotted), or direct labels

  - Test with a colorblind simulator (e.g., Coblis, Sim Daltonism)

  - Use the colorblind-friendly palette: `sns.color_palette("colorblind")`

  ### Screen Readers

  - Include alt text describing the chart's key finding

  - Provide a data table alternative alongside the visualization

  - Use semantic titles and labels

  ### General Accessibility

  - Sufficient contrast between data elements and background

  - Text size minimum 10pt for labels, 12pt for titles

  - Avoid conveying information only through spatial position (add labels)

  - Consider printing: does the chart work in black and white?

  ### Accessibility Checklist

  Before sharing a visualization:

  - \[ \] Chart works without color (patterns, labels, or line styles differentiate series)

  - \[ \] Text is readable at standard zoom level

  - \[ \] Title describes the insight, not just the data

  - \[ \] Axes are labeled with units

  - \[ \] Legend is clear and positioned without obscuring data

  - \[ \] Data source and date range are noted

 ## Official Chart.js references

  - Main documentation: https://www.chartjs.org/docs/latest/
  - Integration/imports: https://www.chartjs.org/docs/latest/getting-started/integration.html
  - Chart types: https://www.chartjs.org/docs/latest/charts/line.html and https://www.chartjs.org/docs/latest/charts/bar.html
  - Time axis + required adapter: https://www.chartjs.org/docs/latest/axes/cartesian/time.html
  - Responsive configuration: https://www.chartjs.org/docs/latest/configuration/responsive.html
  - Accessibility: https://www.chartjs.org/docs/latest/general/accessibility.html
  - Decimation: https://www.chartjs.org/docs/latest/configuration/decimation.html
  - Performance: [https://www.chartjs.org/docs/latest/general/performance.html](https://www.chartjs.org/docs/latest/general/performance.html)