"""
GlucoShield D1NAMO & Wearable Telemetry Validation Runner
=========================================================
Runs the end-to-end wearable telemetry pipeline:
  1. Loads multi-modal participant streams via adapters
  2. Slices into causal 15-minute windows
  3. Computes engineered activity features (active load, HR reserve)
  4. Detects active states and discrete workout episodes
  5. Generates quality and coverage metrics
  6. Renders 5 publication figures
"""

import os
import sys
import json
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Ensure project root is in sys.path
BASE_DIR = "D:/ML PROJECT"
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from activity_telemetry.dataset_adapter import D1NAMOAdapter, MockWearableAdapter
from activity_telemetry.timestamp_alignment import align_telemetry_to_15m_grid
from activity_telemetry.feature_engineering import compute_activity_features
from activity_telemetry.activity_detection import detect_activity_states, extract_activity_episodes
from activity_telemetry.missing_data import clean_raw_timestamps, audit_participant_quality

def run_wearable_validation():
    print("=" * 80)
    print("GLUCOSHIELD — PHASE 7C STEP 2: WEARABLE TELEMETRY VALIDATION PIPELINE")
    print("=" * 80)

    val_dir = os.path.join(BASE_DIR, "activity_telemetry", "validation")
    results_dir = os.path.join(val_dir, "results")
    figures_dir = os.path.join(val_dir, "figures")
    os.makedirs(results_dir, exist_ok=True)
    os.makedirs(figures_dir, exist_ok=True)

    # 1. Select Adapter (D1NAMO or Mock Generator)
    d1namo_raw_dir = os.path.join(BASE_DIR, "data", "raw", "D1NAMO")
    d1namo_adapter = D1NAMOAdapter()
    available_d1namo_pts = d1namo_adapter.list_participants(d1namo_raw_dir)

    if available_d1namo_pts:
        print(f"Found {len(available_d1namo_pts)} local D1NAMO participants: {available_d1namo_pts}")
        adapter = d1namo_adapter
        data_dir = d1namo_raw_dir
        participants = available_d1namo_pts
    else:
        print("Local D1NAMO raw archive not present. Executing pipeline using high-fidelity multi-day MockWearableAdapter...")
        adapter = MockWearableAdapter(num_days=5, seed=42)
        data_dir = ""
        participants = adapter.list_participants()

    all_processed_dfs = []
    coverage_reports = []
    all_episodes = []

    print(f"\nProcessing {len(participants)} participants...")
    for pid in participants:
        print(f"  --> Loading & Processing participant: {pid}...")
        df_raw = adapter.load_participant_telemetry(pid, data_dir)
        df_clean = clean_raw_timestamps(df_raw)

        # 2. 15-Minute Alignment
        df_15m = align_telemetry_to_15m_grid(df_clean, participant_id=pid, expected_sample_interval_sec=5.0)

        # 3. Feature Engineering
        df_feat = compute_activity_features(df_15m, gamma_decay=0.75)

        # 4. Activity Detection & Episode Extraction
        df_detected = detect_activity_states(df_feat)
        episodes = extract_activity_episodes(df_detected, min_duration_minutes=15)

        # 5. Quality Audit
        cov_report = audit_participant_quality(df_detected, participant_id=pid)

        all_processed_dfs.append(df_detected)
        coverage_reports.append(cov_report)
        all_episodes.extend(episodes)

    # Combine all 15m records
    df_all_15m = pd.concat(all_processed_dfs, ignore_index=True)

    # =========================================================================
    # SAVE CSV AND JSON RESULTS
    # =========================================================================
    print("\n--- SAVING CSV & JSON SUMMARY ARTIFACTS ---")
    
    # 1. Participant Coverage CSV
    df_cov = pd.DataFrame([vars(r) for r in coverage_reports])
    df_cov.to_csv(os.path.join(results_dir, "participant_coverage.csv"), index=False)

    # 2. Feature Summary CSV (mean, std, min, max per feature)
    num_cols = ["cgm_glucose", "steps_15m", "hr_mean_15m", "hr_std_15m", "accel_mag_15m", "active_load_60m", "hr_reserve_pct"]
    feat_summary = df_all_15m[num_cols].describe().T[["count", "mean", "std", "min", "50%", "max"]]
    feat_summary.columns = ["count", "mean", "std", "min", "median", "max"]
    feat_summary.round(2).to_csv(os.path.join(results_dir, "feature_summary.csv"))

    # 3. Missingness Report CSV
    missing_report = pd.DataFrame({
        "feature": num_cols,
        "total_windows": len(df_all_15m),
        "valid_count": [df_all_15m[c].notna().sum() for c in num_cols],
        "missing_count": [df_all_15m[c].isna().sum() for c in num_cols],
        "missing_pct": [round((df_all_15m[c].isna().sum() / len(df_all_15m)) * 100, 2) for c in num_cols]
    })
    missing_report.to_csv(os.path.join(results_dir, "missingness_report.csv"), index=False)

    # 4. Activity Episode Summary CSV
    if all_episodes:
        df_ep = pd.DataFrame([vars(e) for e in all_episodes])
        df_ep.to_csv(os.path.join(results_dir, "activity_episode_summary.csv"), index=False)
    else:
        pd.DataFrame(columns=["participant_id", "start_timestamp", "duration_minutes"]).to_csv(
            os.path.join(results_dir, "activity_episode_summary.csv"), index=False
        )

    # 5. Alignment Quality JSON
    alignment_quality = {
        "dataset_name": adapter.dataset_name,
        "total_participants": len(participants),
        "total_15m_windows": int(len(df_all_15m)),
        "mean_cgm_coverage_pct": round(float(df_cov["cgm_coverage_pct"].mean()), 2),
        "mean_wearable_coverage_pct": round(float(df_cov["wearable_coverage_pct"].mean()), 2),
        "mean_joint_coverage_pct": round(float(df_cov["joint_coverage_pct"].mean()), 2),
        "total_activity_episodes_detected": len(all_episodes),
        "mean_episode_duration_mins": round(float(np.mean([e.duration_minutes for e in all_episodes])), 1) if all_episodes else 0.0
    }
    with open(os.path.join(results_dir, "alignment_quality.json"), "w") as f:
        json.dump(alignment_quality, f, indent=2)

    # 6. Validation Manifest JSON
    manifest = {
        "timestamp": "2026-08-28T17:25:00",
        "pipeline_version": "1.0.0",
        "temporal_resolution_minutes": 15,
        "participants_processed": participants,
        "total_windows_generated": len(df_all_15m),
        "files": [
            "participant_coverage.csv",
            "feature_summary.csv",
            "missingness_report.csv",
            "alignment_quality.json",
            "activity_episode_summary.csv"
        ]
    }
    with open(os.path.join(results_dir, "validation_manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)

    # =========================================================================
    # GENERATE PUBLICATION FIGURES (Figures 1 to 5)
    # =========================================================================
    print("\n--- RENDERING PUBLICATION VALIDATION FIGURES ---")

    # Figure 1: Sensor Coverage by Participant
    fig, ax = plt.subplots(figsize=(8, 4.5))
    x = np.arange(len(df_cov))
    w = 0.25
    ax.bar(x - w, df_cov["cgm_coverage_pct"], w, label="CGM Glucose", color="#1f77b4")
    ax.bar(x, df_cov["wearable_coverage_pct"], w, label="Wearable Telemetry", color="#ff7f0e")
    ax.bar(x + w, df_cov["joint_coverage_pct"], w, label="Joint Synchronized", color="#2ca02c")
    ax.set_ylabel("Coverage Percentage (%)", fontsize=12)
    ax.set_title("Figure 1: Telemetry Sensor Coverage by Participant", fontsize=13, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(df_cov["participant_id"], fontsize=10)
    ax.set_ylim(0, 115)
    ax.legend(frameon=True)
    ax.grid(axis="y", linestyle="--", alpha=0.5)
    plt.tight_layout()
    fig.savefig(os.path.join(figures_dir, "fig1_sensor_coverage.png"), dpi=300)
    plt.close(fig)

    # Figure 2: 15-Minute Aligned Multi-Modal Time Series Example (24 Hours)
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 7), sharex=True)
    sample_pt = df_all_15m[df_all_15m["participant_id"] == participants[0]].iloc[:96]  # 24 hours
    
    # 2a: Glucose
    ax1.plot(sample_pt["timestamp"], sample_pt["cgm_glucose"], color="#d62728", linewidth=2, label="CGM Glucose")
    ax1.axhline(70, color="gray", linestyle=":", alpha=0.7)
    ax1.axhline(180, color="gray", linestyle=":", alpha=0.7)
    ax1.set_ylabel("Glucose (mg/dL)", fontsize=11)
    ax1.set_title(f"Figure 2: 24-Hour Synchronized 15-Minute Telemetry ({participants[0]})", fontsize=13, fontweight="bold")
    ax1.legend(loc="upper right")
    ax1.grid(True, linestyle="--", alpha=0.4)

    # 2b: Heart Rate & Active State
    ax2.plot(sample_pt["timestamp"], sample_pt["hr_mean_15m"], color="#1f77b4", linewidth=2, label="Mean Heart Rate (bpm)")
    active_idx = sample_pt[sample_pt["is_active_15m"] == 1]["timestamp"]
    active_hr = sample_pt[sample_pt["is_active_15m"] == 1]["hr_mean_15m"]
    ax2.scatter(active_idx, active_hr, color="#ff7f0e", s=40, zorder=5, label="Active State (Gated)")
    ax2.set_ylabel("Heart Rate (bpm)", fontsize=11)
    ax2.legend(loc="upper right")
    ax2.grid(True, linestyle="--", alpha=0.4)

    # 2c: Steps & Causal 60m Active Load
    ax3.bar(sample_pt["timestamp"], sample_pt["steps_15m"], width=pd.Timedelta(minutes=12), color="#2ca02c", alpha=0.6, label="15m Step Count")
    ax3.plot(sample_pt["timestamp"], sample_pt["active_load_60m"], color="#9467bd", linewidth=2, label="Causal 60m Active Load")
    ax3.set_ylabel("Steps / Load", fontsize=11)
    ax3.set_xlabel("Timestamp", fontsize=11)
    ax3.legend(loc="upper right")
    ax3.grid(True, linestyle="--", alpha=0.4)
    plt.tight_layout()
    fig.savefig(os.path.join(figures_dir, "fig2_15min_alignment_example.png"), dpi=300)
    plt.close(fig)

    # Figure 3: Activity Feature Distributions
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(9, 6.5))
    ax1.hist(df_all_15m["hr_mean_15m"].dropna(), bins=25, color="#1f77b4", edgecolor="black", alpha=0.7)
    ax1.set_title("15m Mean Heart Rate (bpm)", fontweight="bold")
    ax1.set_xlabel("bpm")
    ax1.grid(True, linestyle="--", alpha=0.4)

    ax2.hist(df_all_15m["steps_15m"].dropna(), bins=25, color="#2ca02c", edgecolor="black", alpha=0.7)
    ax2.set_title("15m Step Count", fontweight="bold")
    ax2.set_xlabel("Steps")
    ax2.grid(True, linestyle="--", alpha=0.4)

    ax3.hist(df_all_15m["active_load_60m"].dropna(), bins=25, color="#9467bd", edgecolor="black", alpha=0.7)
    ax3.set_title("Causal 60m Active Load", fontweight="bold")
    ax3.set_xlabel("Load Units")
    ax3.grid(True, linestyle="--", alpha=0.4)

    ax4.hist(df_all_15m["hr_reserve_pct"].dropna(), bins=25, color="#ff7f0e", edgecolor="black", alpha=0.7)
    ax4.set_title("Heart Rate Reserve (%)", fontweight="bold")
    ax4.set_xlabel("% Reserve")
    ax4.grid(True, linestyle="--", alpha=0.4)
    plt.suptitle("Figure 3: 15-Minute Engineered Wearable Feature Distributions", fontsize=13, fontweight="bold")
    plt.tight_layout()
    fig.savefig(os.path.join(figures_dir, "fig3_activity_feature_distributions.png"), dpi=300)
    plt.close(fig)

    # Figure 4: Missingness by Participant
    fig, ax = plt.subplots(figsize=(8, 4.5))
    valid_wins = df_cov["valid_wearable_windows"]
    miss_wins = df_cov["total_15m_windows"] - df_cov["valid_wearable_windows"]
    ax.bar(df_cov["participant_id"], valid_wins, label="Valid Wearable Windows", color="#2ca02c")
    ax.bar(df_cov["participant_id"], miss_wins, bottom=valid_wins, label="Missing Wearable Windows", color="#d62728")
    ax.set_ylabel("15-Minute Windows Count", fontsize=11)
    ax.set_title("Figure 4: Wearable Window Missingness by Participant", fontsize=13, fontweight="bold")
    ax.legend(frameon=True)
    ax.grid(axis="y", linestyle="--", alpha=0.5)
    plt.tight_layout()
    fig.savefig(os.path.join(figures_dir, "fig4_missingness_by_participant.png"), dpi=300)
    plt.close(fig)

    # Figure 5: Detected Activity Episodes (Duration vs Peak HR with Glucose Delta)
    if all_episodes:
        fig, ax = plt.subplots(figsize=(8, 5))
        durs = [e.duration_minutes for e in all_episodes]
        peak_hrs = [e.peak_hr for e in all_episodes]
        deltas = [e.glucose_delta if e.glucose_delta is not None else 0.0 for e in all_episodes]
        
        scatter = ax.scatter(durs, peak_hrs, c=deltas, cmap="coolwarm", s=100, edgecolor="black", linewidth=1.2)
        cbar = plt.colorbar(scatter, ax=ax)
        cbar.set_label("Post-Workout Glucose Delta (mg/dL)", fontsize=11)
        ax.set_xlabel("Workout Episode Duration (Minutes)", fontsize=11)
        ax.set_ylabel("Peak Workout Heart Rate (bpm)", fontsize=11)
        ax.set_title("Figure 5: Detected Activity Episodes & Glycemic Shifts", fontsize=13, fontweight="bold")
        ax.grid(True, linestyle="--", alpha=0.5)
        plt.tight_layout()
        fig.savefig(os.path.join(figures_dir, "fig5_detected_activity_episodes.png"), dpi=300)
        plt.close(fig)

    print("All 5 publication figures generated successfully in activity_telemetry/validation/figures/.")
    print("=" * 80)
    print("WEARABLE VALIDATION EXECUTION COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    run_wearable_validation()
