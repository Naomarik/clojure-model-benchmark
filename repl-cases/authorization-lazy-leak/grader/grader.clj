(ns grader
  (:require [bench.authorization-lazy-leak :as sut]
            [clojure.test :refer [deftest is run-tests]]))

(def rows
  [{:design/id 1 :design/tenant :b :design/title "B1"}
   {:design/id 2 :design/tenant :a :design/title "A1"}
   {:design/id 3 :design/tenant :b :design/title "B2"}
   {:design/id 4 :design/tenant :a :design/title "A2"}
   {:design/id 5 :design/tenant :a :design/title "A3"}])

(deftest captures-authorization-before-realization
  (let [result (binding [sut/*tenant* :a] (sut/feed-page rows 2))]
    (is (vector? result))
    (is (= [{:design/id 2 :design/title "A1"}
            {:design/id 4 :design/title "A2"}]
           result)))
  (is (= [{:design/id 1 :design/title "B1"}
          {:design/id 3 :design/title "B2"}]
         (binding [sut/*tenant* :b] (sut/feed-page rows 2))))
  (is (= [] (binding [sut/*tenant* :none] (sut/feed-page rows 3)))))

(let [{:keys [fail error]} (run-tests 'grader)]
  (System/exit (if (zero? (+ fail error)) 0 1)))
