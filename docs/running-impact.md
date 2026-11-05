# Running impact

The running impact page uses the per-session TRIMP equation from [Emig and Peltonen (2020)](https://pmc.ncbi.nlm.nih.gov/articles/PMC7538888/), a study of approximately 14,000 marathon runners. TRIMP = moving minutes × κ₁ × (average speed / crossover speed) × exp(κ₂ × average speed / crossover speed). The paper reports coefficient pairs 0.64, 1.92 for men and 0.86, 1.67 for women; the user selects the pair without storing personal data.

Crossover speed comes from the existing running predictions model, fitted to recent benchmark-distance activities. The existing 180-day window and query include running activities of at least 3 km with positive moving time. Runs with speed greater than three times crossover speed are excluded to avoid calculating nonsensical or overflowing results from corrupt records. The resulting sum is not directly comparable with the paper's full training season, which uses its own season definition. It is training load, not an estimate of the fitness gained from an individual workout. Benchmark effort, terrain, missing runs, moving time and other sports affect interpretation.

The authenticated API contract is documented in the FastAPI OpenAPI interface at
`/docs`, under `GET /activities/running/impact`. The response model describes
individual run inputs and TRIMP points, the fitted model, and the selected
coefficients. An empty response example illustrates the no-benchmark case;
`RunningImpactActivity` includes an example calculated with a 3.33 m/s
crossover speed and the male coefficient set. See the FastAPI guidance on
[response models](https://fastapi.tiangolo.com/tutorial/response-model/) and
[JSON Schema examples](https://fastapi.tiangolo.com/tutorial/schema-extra-example/).
