#!/usr/bin/env python3
"""Validate newly added bundled graders against known-good solutions."""

import argparse
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_SUITE = ROOT / "suites/eval_clojure.py"

SOLUTIONS = {
    "hard_apply_user_patch": """(defn apply-user-patch [user patch]
  (reduce (fn [u k] (if (contains? patch k) (assoc u k (get patch k)) u))
          user [:user/name :user/bio :user/admin?]))""",
    "hard_reitit_path_by_name": """(defn path-by-name [routes target]
  (letfn [(visit [[segment data & children] prefix]
            (let [path (str prefix segment)]
              (if (= (:name data) target)
                path
                (some #(visit % path) children))))]
    (some #(visit % "") routes)))""",
    "hard_honeysql_boolean_tree": """(defn visible-designs-query [{:keys [tenant-id user-id] :as opts}]
  {:select [:*] :from [:designs]
   :where (cond-> [:and [:= :tenant-id tenant-id]
                   [:or [:= :public? true] [:= :owner-id user-id]]]
            (contains? opts :excluded-statuses)
            (conj [:not [:in :status (:excluded-statuses opts)]]))})""",
    "hard_malli_errors_to_tree": """(defn errors->tree [errors]
  (reduce (fn [tree {:keys [in message]}]
            (update-in tree in (fnil conj []) message))
          {} errors))""",
    "hard_deep_merge": """(defn deep-merge [left right]
  (merge-with (fn [a b] (if (and (map? a) (map? b)) (deep-merge a b) b))
              left right))""",
    "fix_lazy_notification_effects": """(defn notify-users! [notify! users]
  (run! notify! users)
  nil)""",
    "hard_normalize_project_pull": """(defn normalize-project [pulled]
  (assoc (select-keys pulled [:project/id :project/name])
         :project/tasks
         (->> (:task/_project pulled)
              (map #(select-keys % [:task/id :task/title :task/done?]))
              (sort-by :task/id)
              vec)))""",
    "fix_threading_pipeline": """(defn active-emails [users]
  (->> users (filter :active?) (map :email) sort vec))""",
    "hard_reduce_until_match": """(defn first-matching [pred coll]
  (reduce (fn [_ x] (if (pred x) (reduced x) nil)) nil coll))""",
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", type=Path, default=DEFAULT_SUITE)
    args = parser.parse_args()
    suite = args.suite.resolve()
    if not suite.is_file():
        raise SystemExit(f"suite not found: {suite}")
    spec = importlib.util.spec_from_file_location("canonical_eval", suite)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot import suite: {suite}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    tasks = {name: checker for name, _, checker in module.TASKS}
    assert len(module.TASKS) == 33, len(module.TASKS)
    for name, solution in SOLUTIONS.items():
        passed, detail = tasks[name](solution)
        if not passed:
            raise SystemExit(f"{name}: {detail}")
        print(f"PASS {name}")


if __name__ == "__main__":
    main()
