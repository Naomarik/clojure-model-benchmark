(ns bench.dependency-planner
  (:require [clojure.set :as set]))

(defn plan [jobs]
  (let [all-capabilities (reduce set/union #{} (map :provides jobs))]
    (loop [remaining (vec jobs) provided #{} order []]
      (if (empty? remaining)
        order
        (if-let [job (first (sort-by :id
                                     (filter #(set/subset? (:requires %) provided)
                                             remaining)))]
          (recur (filterv #(not= (:id %) (:id job)) remaining)
                 (set/union provided (:provides job))
                 (conj order (:id job)))
          (let [missing (for [job (sort-by :id remaining)
                              capability (sort (set/difference (:requires job)
                                                               all-capabilities))]
                          [(:id job) capability])]
            (if-let [[job capability] (first missing)]
              {:error :missing-capability :capability capability :job job}
              {:error :cycle :jobs (vec (sort (map :id remaining)))})))))))
