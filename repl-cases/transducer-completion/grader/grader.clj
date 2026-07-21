(ns grader
  (:require [bench.transducer-completion :as sut]
            [clojure.test :refer [deftest is run-tests]]))

(deftest emits-complete-and-final-partitions
  (is (= [[1 2 :cut] [3 4]]
         (into [] (sut/partition-until #{:cut}) [1 2 :cut 3 4])))
  (is (= [] (into [] (sut/partition-until #{:cut}) [])))
  (is (= [[:cut] [:cut] [1]]
         (into [] (sut/partition-until #{:cut}) [:cut :cut 1])))
  (is (= [[1 :cut]]
         (into [] (comp (sut/partition-until #{:cut}) (take 1))
               [1 :cut 2 :cut 3]))))

(deftest completion-runs-once
  (let [completions (atom 0)
        rf (fn
             ([] [])
             ([result] (swap! completions inc) result)
             ([result input] (conj result input)))]
    (is (= [[1 2]] (transduce (sut/partition-until #{:cut}) rf [1 2])))
    (is (= 1 @completions))))

(let [{:keys [fail error]} (run-tests 'grader)]
  (System/exit (if (zero? (+ fail error)) 0 1)))
