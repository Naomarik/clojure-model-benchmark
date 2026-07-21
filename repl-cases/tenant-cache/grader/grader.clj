(ns grader
  (:require [bench.tenant-cache :as sut]
            [clojure.test :refer [deftest is run-tests]]))

(deftest cache-is-scoped
  (sut/clear!)
  (let [calls (atom [])
        loader (fn [tenant id]
                 (swap! calls conj [tenant id])
                 (get {[:a "p1"] {:title "A"}
                       [:b "p1"] {:title "B"}} [tenant id]))]
    (is (= {:title "A"} (sut/lookup loader :a 1 "p1")))
    (is (= {:title "B"} (sut/lookup loader :b 1 "p1")))
    (is (= {:title "A"} (sut/lookup loader :a 1 "p1")))
    (is (= [[:a "p1"] [:b "p1"]] @calls))
    (is (= {:title "A"} (sut/lookup loader :a 2 "p1")))
    (is (= 3 (count @calls)))))

(deftest nil-is-cached
  (sut/clear!)
  (let [calls (atom 0) loader (fn [_ _] (swap! calls inc) nil)]
    (is (nil? (sut/lookup loader :a 1 "missing")))
    (is (nil? (sut/lookup loader :a 1 "missing")))
    (is (= 1 @calls))))

(let [{:keys [fail error]} (run-tests 'grader)]
  (System/exit (if (zero? (+ fail error)) 0 1)))
