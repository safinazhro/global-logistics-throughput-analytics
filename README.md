# Global Logistics Throughput & Labor Analytics

**Identifying and quantifying a hidden operational bottleneck in warehouse cargo handling — from raw data to an interactive business intelligence dashboard.**

An end-to-end data analytics case study on warehouse throughput, landside logistics, and labor allocation in a cargo handling facility. Built as a portfolio project for a **Business Data Analyst** role in the global logistics industry.

---

## Headline Result

Across six months of simulated operations, an estimated **USD ~7,000 in demurrage penalties** was traced back to a single, correctable root cause: labor allocation on the second shift did not scale with the shift's actual workload, particularly for cargo types that require more intensive handling.

---

## 1. Business Problem

A warehouse logistics facility runs three work shifts across three zones, handling three categories of cargo with very different handling requirements:

| Cargo Type | Handling Complexity | Why |
|---|---|---|
| Standard Dry | Low | Standard load/unload procedure |
| Refrigerated | High | Requires power hookup, temperature checks, time-sensitive due to spoilage risk |
| Hazardous | High | Mandatory safety inspection and additional documentation |

Trucks that stay at the facility longer than their contractual **free time allowance** trigger a **demurrage penalty**, billed per hour of excess dwell time. This project investigates whether penalty costs are randomly distributed, or whether they trace back to a systemic operational issue that can be fixed with a policy change rather than added infrastructure.

**Analytical questions addressed:**
1. Which shift and zone contribute the most to demurrage costs?
2. Is current labor allocation proportional to the workload each shift actually receives?
3. Which cargo types carry the highest financial risk?
4. What is the estimated cost impact of correcting labor allocation?

---

## 2. Key Findings

- **Shift 2 (14:00–22:00)** receives the highest truck volume of the three shifts, yet is allocated the lowest headcount relative to its workload — a labor scheduling mismatch, not a volume problem per se.
- This mismatch is statistically significant, not random variation: a Welch's t-test on dwell time (Shift 2 vs. all other shifts) returns **p < 0.000001**, with a **Cohen's d of 0.90** (a large effect size).
- **Shift congestion index** (labor demand relative to labor supply) correlates strongly with dwell time (**Pearson r ≈ 0.50, p < 0.000001**), confirming that delays scale predictably with the labor gap rather than occurring at random.
- **Refrigerated and Hazardous cargo** account for a disproportionate share of total demurrage cost relative to their share of shipment volume, consistent with their higher handling complexity.
- A directional simulation shows that a **20% labor increase on Shift 2** could reduce that shift's demurrage cost substantially, because most affected shipments sit only marginally above the free time threshold.

Full statistical validation and simulation logic are documented in [`eda_analysis.ipynb`](eda_analysis.ipynb).

---

## 3. Methodology

### Data generation
Since this is a portfolio project (not built on proprietary company data), a synthetic but operationally realistic dataset was engineered in [`generate_dataset.py`](generate_dataset.py). Rather than pure random values, the generator encodes real operational logic:

- Truck arrivals are distributed across shifts with a deliberately uneven volume-to-labor ratio.
- Processing time is a function of cargo type complexity and a **congestion index**, calculated per shift-day as labor demand versus labor supply.
- Dwell time and demurrage penalties are derived mechanically from gate-in/gate-out timestamps and cargo-specific contractual thresholds, the same way they would be calculated in a real terminal operating system.
- ~1–1.5% missing values are deliberately injected into non-critical fields to reflect real-world data quality issues.

This approach means the "bottleneck" in the data is not decorative — it is a reproducible, internally consistent pattern that a real analytical workflow can (and does) detect.

### Exploratory analysis
[`eda_analysis.ipynb`](eda_analysis.ipynb) walks through data quality checks, volume and labor analysis, demurrage breakdowns by shift/zone/cargo type, statistical significance testing, and a labor-rebalancing cost simulation.

### Interactive dashboard
[`app.py`](app.py) turns the EDA findings into a decision-support tool with live filtering, built in Streamlit.

---

## 4. Dashboard Overview

The dashboard is organized into four pages, navigable from the sidebar, with global filters for date range, shift, zone, and cargo type.

| Page | Purpose |
|---|---|
| **Overview** | Facility-wide KPIs: total trucks processed, total demurrage cost, average dwell time, share of shipments affected |
| **Shift and Labor Analysis** | Workload-to-labor ratio, congestion index by shift, dwell time distribution, congestion-vs-dwell-time relationship |
| **Cargo Risk Breakdown** | Demurrage cost and delay rate by cargo type, shift-by-cargo risk heatmap |
| **Financial Impact and Recommendation** | Revenue-at-risk projection, interactive labor-rebalancing simulator, summary recommendation |

### Running it locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

The app expects `warehouse_operations.csv` to be in the same directory. To regenerate the dataset from scratch:

```bash
python generate_dataset.py
```

---

## 5. Tech Stack

- **Python** — Pandas, NumPy for the data pipeline; SciPy for statistical testing
- **Jupyter Notebook** — exploratory analysis, hypothesis testing, and simulation
- **Streamlit** — interactive dashboard, themed via `.streamlit/config.toml` (no custom CSS/HTML)
- **Plotly** — interactive charting with a consistent, industry-appropriate color palette

---

## 6. Repository Structure

```
global-logistics-throughput-analytics/
├── .streamlit/
│   └── config.toml          # Dashboard visual theme
├── app.py                   # Streamlit dashboard (4 pages)
├── generate_dataset.py      # Synthetic data generator with embedded bottleneck logic
├── warehouse_operations.csv # Generated dataset (14k+ records, 22 columns)
├── eda_analysis.ipynb       # Exploratory analysis, statistical testing, simulation
├── requirements.txt
└── README.md
```

---

## 7. Recommendation

The primary recommendation is to **rebalance shift labor allocation**, prioritizing Shift 2 and cargo types with higher handling complexity (Refrigerated, Hazardous). Based on the simulation in the dashboard's final page, this is estimated to meaningfully reduce demurrage exposure without requiring additional warehouse capacity — a lower-cost intervention than physical expansion.

---

## 8. Limitations & Next Steps

- The dataset is synthetic; it is designed to be operationally realistic, not a substitute for real terminal operations data.
- The labor-rebalancing simulation is a directional estimate based on the same formula used to generate the data, not a model trained on independent historical outcomes.
- Natural next steps: replace the simulation with a queueing-theory or regression-based model trained on real operational data, and extend the analysis to landside trucking scheduling and multi-facility comparisons.

---

## Author

[Safina Zahra]
[www.linkedin.com/in/safina-zahra] · [safinaznah@gmail.com] 
