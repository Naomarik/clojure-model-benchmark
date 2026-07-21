(ns grader
  (:require [bench.closed-order-stream :as sut]
            [clojure.test :refer [deftest is run-tests]]))

(defn temp-orders [text]
  (doto (java.io.File/createTempFile "orders" ".csv")
    (spit text)))

(deftest reads-while-open
  (let [file (temp-orders "a,100\nb,250\n\n")
        result (sut/read-orders (.getPath file))]
    (is (vector? result))
    (is (= [{:order/id "a" :order/amount 100}
            {:order/id "b" :order/amount 250}]
           result))
    (.delete file)))

(deftest empty-input
  (let [file (temp-orders "")]
    (is (= [] (sut/read-orders (.getPath file))))
    (.delete file)))

(let [{:keys [fail error]} (run-tests 'grader)]
  (System/exit (if (zero? (+ fail error)) 0 1)))
