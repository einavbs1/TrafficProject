FlowGrid policy backup — 20260530_132749
Label: pre_balanced_policy_20k
Map: plan_2_opposite_thru_right

Contents:
  dqn_policy.pth          — main checkpoint (restore to map folder)
  dqn_policy_objectives.txt
  config/dqn_policy_config.yaml — snapshot at backup time
  logs/dqn_training_log.jsonl — training history copy

Restore main checkpoint:
  copy dqn_policy.pth -> data/maps/plan_2_opposite_thru_right/dqn_policy.pth

Fresh start (archive old + new log):
  python scripts/run_train.py --map plan_2_opposite_thru_right --fresh --episodes 500

Files copied: 4