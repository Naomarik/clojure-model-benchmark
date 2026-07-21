(ns grader
  (:require [bench.webhook-event-fold :as sut]
            [clojure.test :refer [deftest is run-tests]]))

(deftest idempotent-and-monotonic
  (let [created {:id "e1" :sequence 10 :type :subscription/created}
        paid {:id "e2" :sequence 11 :type :invoice/paid}
        canceled {:id "e3" :sequence 12 :type :subscription/canceled}
        stale {:id "e0" :sequence 9 :type :subscription/created}
        once (sut/fold-events sut/initial-state [created paid canceled stale])
        twice (sut/fold-events once [paid canceled])]
    (is (= :canceled (:status once)))
    (is (= 12 (:last-seq once)))
    (is (= #{"e0" "e1" "e2" "e3"} (:seen once)))
    (is (= [[:send-receipt "e2"]] (:effects once)))
    (is (= once twice))))

(deftest unknown-event-advances-sequence
  (let [state (sut/apply-event sut/initial-state
                               {:id "x" :sequence 3 :type :unknown})]
    (is (= :new (:status state)))
    (is (= 3 (:last-seq state)))
    (is (= #{"x"} (:seen state)))))

(let [{:keys [fail error]} (run-tests 'grader)]
  (System/exit (if (zero? (+ fail error)) 0 1)))
