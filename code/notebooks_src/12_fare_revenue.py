# %% [markdown]
# # 12 · Fare revenue: what the Yellow Line and the headway cut meant for the fare box
# * Weekday fare revenue before (1-10 Aug) and after (11-18 Aug) the opening, by line, by fare slab.
# * Revenue from trips using the new stations.
# * Revenue from the 10 Sep headway cut: causal entry effect (+8.7%, notebook 03) x entries x average fare.
# Fare-box revenue only: not profit (costs are not public) and not passengers' time savings.

# %%
SETUP

# %%
from t15 import fares as FR
import matplotlib.pyplot as plt
r = FR.fare_revenue()
for k, v in r.items():
    PL.save_table(v, f"fare_{k}.csv")
r["summary"].round(1)

# %%
r["yellow"].round(1)

# %%
r["headway"].round(1)

# %%
r["by_line"].round(0)

# %%
fig, ax = plt.subplots(1, 2, figsize=(14, 4))
s = r["summary"].iloc[:2]
ax[0].bar(["before", "after"], [r["summary"].at[1, "before"] / 1e7, r["summary"].at[1, "after"] / 1e7], color=["#9aa6b5", "#1f6fb2"])
ax[0].set_title("Fare revenue per weekday (Rs crore)")
f = r["fares"]
ax[1].bar(f["fare"].astype(str), f["trips"], color="#1f6fb2"); ax[1].set_title("Trips per weekday by fare (Rs), after opening")
PL.save_fig(fig, "fig20_fare_revenue.png")
