(ns bench.dependency-planner
  (:require [clojure.set :as set]))

(defn plan [jobs]
  (loop [remaining jobs completed #{} order []]
    (if (empty? remaining)
      order
      (if-let [job (first (sort-by :id
                                   (filter #(set/subset? (:requires %) completed)
                                           remaining)))]
        (recur (remove #(= (:id %) (:id job)) remaining)
               (conj completed (:id job))
               (conj order (:id job)))
        {:error :cycle :jobs (vec (sort (map :id remaining)))}))))
