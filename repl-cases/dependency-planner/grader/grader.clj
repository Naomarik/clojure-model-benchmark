(ns grader
  (:require [bench.dependency-planner :as sut]
            [clojure.test :refer [deftest is run-tests]]))

(deftest deterministic-capability-plan
  (let [jobs [{:id :web :provides #{:web} :requires #{:schema :assets}}
              {:id :assets :provides #{:assets} :requires #{}}
              {:id :migrate :provides #{:schema} :requires #{:db}}
              {:id :database :provides #{:db} :requires #{}}]]
    (is (= [:assets :database :migrate :web] (sut/plan jobs)))
    (is (= jobs jobs))))

(deftest diagnostics
  (is (= {:error :missing-capability :capability :secret :job :web}
         (sut/plan [{:id :web :provides #{:web} :requires #{:secret}}])))
  (is (= {:error :cycle :jobs [:a :b]}
         (sut/plan [{:id :a :provides #{:a-ready} :requires #{:b-ready}}
                    {:id :b :provides #{:b-ready} :requires #{:a-ready}}])))
  (is (= [:a :b]
         (sut/plan [{:id :b :provides #{:x} :requires #{}}
                    {:id :a :provides #{:x} :requires #{}}]))))

(let [{:keys [fail error]} (run-tests 'grader)]
  (System/exit (if (zero? (+ fail error)) 0 1)))
